# HCP (Hermes Collaboration Protocol) 规范 v1.0

**实施日期**: 2026-06-28  
**状态**: ✅ Production Ready  
**协议**: JSON-RPC 2.0 over Unix Socket

---

## 1. 设计原则

1. **轻量**: 心跳消息 < 1KB，延迟 < 100ms
2. **双向**: 主脑可主动 probing，子 Agent 可主动上报
3. **可观测**: 每个消息带 `session_id` + `timestamp` + `sequence_num`
4. **安全**: Token 认证 (文件系统权限 0600)

---

## 2. 消息格式

### 2.1 通用结构 (JSON-RPC 2.0)

```json
{
  "jsonrpc": "2.0",
  "id": <integer>,
  "method": "<method_name>",
  "params": {
    "session_id": "<string>",
    ...
  }
}
```

### 2.2 心跳上报 (Heartbeat)

**方向**: 子 Agent → 父脑

```json
// Request
{
  "jsonrpc": "2.0",
  "id": 1,
  "method": "heartbeat",
  "params": {
    "session_id": "sa-0-abc123",
    "status": "running",
    "step": "reading_large_file",
    "progress": 45.0,
    "eta_seconds": 180,
    "metadata": {
      "api_call_count": 12,
      "max_iterations": 100,
      "pid": 27484
    }
  }
}

// Response
{
  "jsonrpc": "2.0",
  "id": 1,
  "result": {
    "ack": true,
    "timestamp": 1782610472.6458578,
    "command": "continue"
  }
}
```

**字段说明**:
- `status`: `running` | `idle` | `waiting`
- `step`: 当前执行步骤 (如 `reading_file`, `executing_command`)
- `progress`: 0-100 百分比
- `eta_seconds`: 预计剩余时间 (秒)

### 2.3 完成确认 (ACK)

**方向**: 子 Agent → 父脑

```json
// Request
{
  "jsonrpc": "2.0",
  "id": 2,
  "method": "ack",
  "params": {
    "session_id": "sa-0-abc123",
    "status": "completed",
    "result_checksum": "a1b2c3d4e5f6",
    "duration_seconds": 123.45
  }
}

// Response
{
  "jsonrpc": "2.0",
  "id": 2,
  "result": {
    "ack": true,
    "timestamp": 1782610472.6467874
  }
}
```

**字段说明**:
- `status`: `completed` | `error` | `timeout`
- `result_checksum`: 前 16 位 SHA256 (用于完整性校验)
- `duration_seconds`: 执行耗时 (秒)

### 2.4 主动探测 (Probe)

**方向**: 父脑 → 子 Agent

```json
// Request
{
  "jsonrpc": "2.0",
  "id": 3,
  "method": "probe",
  "params": {
    "session_id": "sa-0-abc123"
  }
}

// Response
{
  "jsonrpc": "2.0",
  "id": 3,
  "result": {
    "ack": true,
    "latency_ms": 0.28,
    "status": "running",
    "step": "processing"
  }
}
```

**超时处理**:
- 10 秒无响应 → 标记 stale
- 连续 3 次 stale → 通知 Watchdog

---

## 3. 通信流程

### 3.1 子 Agent 启动

```
1. delegate_tool.py 启动子 Agent
2. 读取 config.yaml: hcp.enabled=true
3. start_hcp_heartbeat(session_id, child_agent, interval=30)
4. HCP Client 连接 Unix Socket (~/.hermes/hcp.sock)
5. 发送第一次心跳 (sequence_num=0)
```

### 3.2 心跳上报循环

```
每 30 秒:
  1. 获取子 Agent activity summary
  2. 检测 stale (双指标：api_count + step)
  3. 发送 heartbeat 到 HCP Server
  4. 记录响应 (成功/失败)

连续 3 次 stale:
  1. 记录警告日志
  2. 停止心跳线程
  3. 等待任务自然结束或 Watchdog 介入
```

### 3.3 任务完成

```
1. 子 Agent 完成任务
2. delegate_tool.py finally 块:
   - 停止心跳线程 (_hcp_stop_event.set())
   - 发送 ack (status=completed/error/timeout)
3. HCP Server 标记会话完成
4. 持久化到 SQLite (待实现)
```

---

## 4. Stale Detection v2 (双指标)

### 4.1 问题背景

v1 仅检测 `step == "idle"`，导致 `sleep` / `wait` 场景被误判。

### 4.2 v2 算法

```python
prev_api_count = 0
prev_step = "idle"
stale_count = 0
max_stale = 3

while running:
    summary = get_activity_summary()
    current_api_count = summary.get("api_call_count", 0)
    current_step = summary.get("current_tool", "idle")
    
    if current_api_count == prev_api_count and current_step == prev_step:
        stale_count += 1
        if stale_count >= max_stale:
            stop_heartbeat()
            break
    else:
        stale_count = 0  # 有进展，重置
    
    prev_api_count = current_api_count
    prev_step = current_step
    
    send_heartbeat(...)
```

### 4.3 测试用例

| 场景 | api_count | step | 预期结果 |
|------|-----------|------|---------|
| `sleep 15` | 0 → 0 | idle → idle | ❌ stale (3 次后停止) |
| `ls -la` | 0 → 1 | idle → executing_command | ✅ 继续 |
| `while true` | 5 → 5 | loop → loop | ❌ stale (真·卡住) |
| 正常任务 | 10 → 11 → 12 | step1 → step2 → step3 | ✅ 继续 |

---

## 5. OpenClaw ACP 桥接

### 5.1 架构

```
OpenClaw (ACP Client)
       │
       │ TCP :18790
       ▼
HCP ↔ ACP Bridge (python3 hcp_acp_bridge.py)
       │
       │ Unix Socket (~/.hermes/hcp.sock)
       ▼
HCP Server → Hermes Parent
```

### 5.2 ACP 方法映射

| ACP Method | HCP Method | 说明 |
|------------|------------|------|
| `openclaw.ping` | - | 直接返回 pong，不转发 |
| `openclaw.task.start` | `heartbeat(status="running", step="task_start")` | 创建 HCP session |
| `openclaw.task.progress` | `heartbeat(step=<step>, progress=<pct>)` | 更新进度 |
| `openclaw.task.complete` | `ack(status=<status>, duration=<dur>)` | 完成确认 |

### 5.3 测试命令

```bash
# Ping 测试
echo '{"jsonrpc":"2.0","id":1,"method":"openclaw.ping","params":{}}' | nc <ip> 18790
# → {"jsonrpc":"2.0","id":1,"result":{"status":"pong"}}

# Task Start 测试
echo '{"jsonrpc":"2.0","id":2,"method":"openclaw.task.start","params":{"session_id":"test_001"}}' | nc <ip> 18790
# → {"jsonrpc":"2.0","id":2,"result":{"ack":true,"session_id":"test_001"}}
# HCP Server 日志：New session: test_001

# Progress 测试
echo '{"jsonrpc":"2.0","id":3,"method":"openclaw.task.progress","params":{"step":"processing","progress":50.0}}' | nc <ip> 18790
# → {"jsonrpc":"2.0","id":3,"result":{"ack":true}}

# Complete 测试
echo '{"jsonrpc":"2.0","id":4,"method":"openclaw.task.complete","params":{"status":"completed","duration":10.5}}' | nc <ip> 18790
# → {"jsonrpc":"2.0","id":4,"result":{"ack":true}}
```

---

## 6. 配置项

### 6.1 `config.yaml`

```yaml
hcp:
  enabled: true
  socket_path: ~/.hermes/hcp.sock
  heartbeat_interval_seconds: 30
  probe_interval_seconds: 60
  probe_timeout_seconds: 10
  token_path: ~/.hermes/hcp.token

delegation:
  hcp_enabled: true  # 自动注入到 delegate_tool.py
  hcp_heartbeat_interval: 30
  use_hcp_for_subagents: true
```

### 6.2 环境变量 (可选)

```bash
export HERMES_HCP_ENABLED=true
export HERMES_HCP_SOCKET_PATH=~/.hermes/hcp.sock
```

---

## 7. 文件清单

| 文件 | 路径 | 说明 |
|------|------|------|
| HCP Server | `~/.hermes/hcp_server.py` | 监听 Unix Socket |
| HCP Client | `~/.hermes/hcp_client.py` | 子 Agent SDK |
| Integration | `~/.hermes/hermes-agent/utils/hcp_integration.py` | delegate_tool 集成 |
| ACP Bridge | `~/.hermes/hcp_acp_bridge.py` | TCP → Unix Socket 转发 |
| Protocol Spec | `~/.hermes/hcp_protocol.md` | 本文档 |
| Token | `~/.hermes/hcp.token` | 认证 Token (mode 0600) |
| Socket | `~/.hermes/hcp.sock` | Unix Socket (mode 0600) |

---

## 8. 故障排查

### 8.1 HCP Server 未启动

```bash
# 检查进程
ps aux | grep hcp_server

# 检查 Socket
ls -la ~/.hermes/hcp.sock

# 手动启动
python3 ~/.hermes/hcp_server.py &
```

### 8.2 心跳未上报

```bash
# 查看 HCP Server 日志
tail -50 ~/.hermes/hcp_server.log | grep "New session\|Heartbeat\|stale"

# 查看子 Agent 日志
grep "HCP heartbeat" ~/.hermes/logs/agent.log
```

### 8.3 ACP Bridge 连接失败

```bash
# 检查 Bridge 进程
ps aux | grep hcp_acp_bridge

# 检查端口
ss -tlnp | grep 18790

# 测试连通性
echo '{"jsonrpc":"2.0","id":1,"method":"openclaw.ping","params":{}}' | nc <ip> 18790
```

---

## 9. 性能数据 (2026-06-28 实测)

| 指标 | 值 | 测试条件 |
|------|-----|---------|
| 心跳延迟 | 0.28ms | Probe 响应时间 |
| 心跳间隔 | 30s | config.yaml |
| Stale 阈值 | 3 次 | 连续无进展 |
| Token 长度 | 16 字符 | hex(随机 8 字节) |
| Socket 权限 | 0600 | 仅当前用户可访问 |
| Bridge 吞吐量 | ~100 msg/s | netcat 压测 |

---

## 10. 与相关技能的关系

- **agent-collaboration-workflow**: HCP 是该技能Phase 1-3的永久修复方案
- **dispatching-parallel-agents**: HCP 提供了心跳/ACK底层协议
- **hermes-agent**: HCP Server/Client 作为 Hermes 核心组件

---

*Last updated: 2026-06-28*
*Status: ✅ Production*