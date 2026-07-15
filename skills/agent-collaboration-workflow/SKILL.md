---

name: agent-collaboration-workflow
description: Hermes 三 Agent 协作架构 — 主脑调度 OpenCode (代码) + OpenClaw (脚本)，含系统服务启动检查、调用模板和故障排查。
version: 1.2.0
author: Hermes
license: MIT
platforms:
- linux
- macos
metadata:
  hermes:
    tags:
      trigger:
      - agent协作
      - 工作流
      - 多agent
      - 协作模式
      - 调度
      - agent协作
      - 调度子agent
      - agent配合
      disable:
      - cli_only
      - read_only
    related_skills:
    - hermes-agent
    - plan
    absorbed_into_umbrella:
    - openclaw
    - opencode
    - hcp-collaboration-protocol
    - agent-collaboration-architecture
---

# Hermes 三 Agent 协作架构

**架构**: Hermes (主脑) + OpenCode (代码协作) + OpenClaw (脚本执行)  
**版本**: v1.2 (2026-06-30) — 修正 MCP/ACP 架构理解，添加 systemd 持久化配置

---

## 🚨 关键架构澄清 (2026-06-30)

**重要**: 本文档已根据实测结果修正，纠正常见误解：

### 1. Hermes MCP server 不是独立服务

- **运行模式**: **stdio** (通过 stdin/stdout 与 client 通信)
- **启动方式**: 由 OpenCode 在启动时 **Spawn 进程**
- **Systemd**: **不需要** systemd 服务 (之前配置会导致重启循环)
- **配置位置**: `~/.opencode/settings.json`

```json
{
  "mcp": {
    "servers": {
      "hermes": {
        "command": "hermes",
        "args": ["mcp", "serve"],
        "enabled": true
      }
    }
  }
}
```

**测试验证**:
```bash
# 手动测试 stdio 响应
echo '{"jsonrpc":"2.0","id":1,"method":"tools/list"}' | hermes mcp serve 2>&1
# → 返回 JSON-RPC 响应证明工作正常
```

**❌ 错误配置** (会导致重启循环):
```ini
# 不要创建这个 systemd 服务！
[Unit]
Description=Hermes MCP Server
[Service]
ExecStart=hermes mcp serve
Restart=always  # ← 这会不断重启，因为 stdio 没有输入就退出
```

### 2. OpenClaw 连接方向

| 模式 | 命令 | 方向 | 协议 |
|------|------|------|------|
| **Hermes → OpenClaw** | `openclaw agent --local -m "任务"` | Hermes 作为 client | HTTP (Gateway) |
| **OpenClaw → Hermes** | `openclaw acp client --server "hermes"` | OpenClaw 作为 client | ACP (stdio) |
| **External → OpenClaw** | `openclaw gateway` | 外部通过 HTTP API | WebSocket/REST |

**架构修正**:
```
错误理解:
  Hermes --MCP--> OpenClaw
  OpenClaw --MCP--> Hermes

正确理解:
  OpenClaw --ACP--> Hermes ACP Server (独立运行)
  OpenCode --MCP--> Hermes MCP Server (stdio, OpenCode Spawn)
  
  Hermes (主脑) --HTTP Gateway--> OpenClaw (单项调用)
```

### 3. ACP 连接需要 PTY wrapper

**问题**: `openclaw acp client --server "hermes"` 会进入交互模式 (`>` 提示符)，管道输入会被 TUI 忽略。

**解决方案**: 使用 tmux 包装

```bash
# ✅ 正确方式
tmux new-session -d -s oc-acp 'openclaw acp client --server "hermes" --cwd ~'
sleep 5  # 等待初始化
tmux send-keys -t oc-acp '执行：uname -a' Enter
sleep 15
tmux capture-pane -t oc-acp -p -S -200
tmux kill-session -t oc-acp

# ❌ 错误方式 (不会工作)
echo "uname -a" | openclaw acp client --server "hermes" --cwd ~
```

---

## 🧠 主脑模式边界

主脑模式的完整流程不应维护在 `SOUL.md`。`SOUL.md` 只保留触发规则：当用户明确说“使用主脑模式 / 启用主脑模式 / Oracle Mode / 主脑调度”时，必须加载 `hermes-oracle-mode` skill。

本 skill 负责 Hermes/OpenClaw/OpenCode 的具体连接架构、服务状态、ACP/MCP 方向、tmux 包装和故障排查；`hermes-oracle-mode` 负责主脑调度流程、阻塞优先修复、子 agent 结果独立验证和最终交付格式。不要把两者合并回 SOUL.md，避免身份层膨胀和双轨漂移。

---

## 🏗️ 架构总览

```
┌──────────────────────────────────────────────────────────┐
│              Hermes (主脑 / 调度中心)                  │
│  职责：计划制定、任务分解、结果汇总、决策路由             │
│  工具：delegate_task, todo, skill_manage, memory         │
└────────────┬─────────────────────┬───────────────────────┘
             │                     │
     策略路由               策略路由
             │                     │
     ┌───────▼────────┐   ┌───────▼────────┐
     │   OpenCode     │   │   OpenClaw     │
     │  (代码协作)    │   │  (脚本执行)    │
     │  TCP 长连接    │   │  ACP/CLI 单次  │
     │  <ip>│   │  <ip>│
     └────────────────┘   └────────────────┘
```

---

## 🚀 启动检查流程

### 1. 开机自启服务

| 服务 | Systemd 单元 | 端口 | 状态检查 | 备注 |
|------|-------------|------|----------|------|
| **Hermes ACP Server** | `hermes-acp.service` | - | `systemctl --user is-active hermes-acp` | ✅ 独立运行 (OpenClaw 连接) |
| **OpenClaw Gateway** | `openclaw-gateway.service` | 18789 | `systemctl is-active openclaw-gateway` | ✅ HTTP API |
| **Hermes MCP Server** | **无** (stdio 模式) | - | **N/A** | ❌ 不需要 systemd，由 OpenCode Spawn |

### 2. 持久化配置 (Systemd)

**Hermes ACP Server** (`~/.config/systemd/user/hermes-acp.service`):
```ini
[Unit]
Description=Hermes ACP Server (for OpenClaw connection)
After=network.target

[Service]
Type=simple
User=lan
WorkingDirectory=~
ExecStart=~/.local/bin/hermes acp --accept-hooks
Restart=always
RestartSec=5
Environment="HERMES_HOME=~/.hermes"

[Install]
WantedBy=default.target
```

**启用服务**:
```bash
systemctl --user daemon-reload
systemctl --user enable hermes-acp
systemctl --user start hermes-acp
systemctl --user status hermes-acp
```

**OpenClaw Gateway** (`/etc/systemd/system/openclaw-gateway.service`):
```ini
[Unit]
Description=OpenClaw Gateway (HTTP API + ACP Bridge)
After=network.target

[Service]
Type=simple
User=lan
WorkingDirectory=~/.openclaw
ExecStart=~/.openclaw/bin/openclaw gateway
Restart=always
Environment="OPENCLAW_HOME=~/.openclaw"

[Install]
WantedBy=multi-user.target
```

### 3. OpenCode MCP 配置

**配置文件**: `~/.opencode/settings.json`
```json
{
  "mcp": {
    "servers": {
      "hermes": {
        "command": "hermes",
        "args": ["mcp", "serve"],
        "enabled": true
      }
    }
  }
}
```

**验证**: OpenCode 启动时会自动 Spawn `hermes mcp serve` 进程并通过 stdio 连接。

### 4. 快速验证脚本

```bash
#!/bin/bash
# ~/scripts/check-agent-services.sh

set -e

echo "=== Agent Services Health Check ==="

# Check Hermes ACP
if systemctl --user is-active --quiet hermes-acp; then
    echo "✅ Hermes ACP: active"
    ps aux | grep "hermes acp" | grep -v grep | head -1
else
    echo "❌ Hermes ACP: not active"
    echo "   Fix: systemctl --user start hermes-acp"
fi

# Check OpenClaw Gateway
if systemctl is-active --quiet openclaw-gateway; then
    echo "✅ OpenClaw Gateway: active (port 18789)"
    ss -tuln | grep -q ":18789" && echo "   └─ Port 18789 LISTEN" || echo "   └─ ⚠️ Port not listening"
else
    echo "❌ OpenClaw Gateway: not active"
    echo "   Fix: sudo systemctl start openclaw-gateway"
fi

# Check OpenCode MCP config
if [ -f ~/.opencode/settings.json ]; then
    if grep -q '"hermes"' ~/.opencode/settings.json && grep -q '"mcp"' ~/.opencode/settings.json; then
        echo "✅ OpenCode MCP: configured"
    else
        echo "⚠️  OpenCode MCP: config missing Hermes"
    fi
else
    echo "❌ OpenCode: config not found"
fi

# Quick connectivity test
echo ""
echo "=== Connectivity Test ==="

# Hermes ACP test
timeout 10 bash -c 'echo "test" | openclaw acp client --server "hermes" --cwd ~ 2>&1' | grep -q "ACP client connected" && \
    echo "✅ Hermes ACP: reachable" || \
    echo "⚠️  Hermes ACP: connection test failed"

# OpenCode MCP stdio test
echo '{"jsonrpc":"2.0","id":1,"method":"tools/list"}' | timeout 2 hermes mcp serve 2>&1 | grep -q "jsonrpc" && \
    echo "✅ Hermes MCP: stdio responsive" || \
    echo "⚠️  Hermes MCP: stdio test failed (may be normal)"

echo ""
echo "=== Done ==="
```

### 3. Hermes 调用前自检

```python
# 在 delegate_task 前执行
def check_agents():
    """检查 Agent 服务可用性"""
    checks = {
        'opencode': lambda: ss_check(8901),
        'openclaw': lambda: http_check('http://<ip>/health')
    }
    return {name: fn() for name, fn in checks.items()}
```

---

## 📡 OpenCode 调用方式

### 场景：代码协作、项目重构、PR 生成

**模式**: TCP 长连接 (Systemd 托管)  
**端点**: `<ip>`  
**协议**: HTTP-like (OpenCode 自定义)

### 调用模板

```python
delegate_task(
    goal="重构 ~/project 的认证模块",
    context="""
    使用 OpenCode 协作模式:
    
    opencode --attach http://<ip> run "<任务描述>"
    
    或生成 diff:
    opencode --attach http://<ip> run "Review and propose changes for..."
    
    工作目录：~/project
    输出格式：unified diff
    """,
    toolsets=["terminal", "coding"],
    role="leaf"
)
```

### 完整示例

```bash
# 1. 直接调用
opencode --attach http://<ip> run \
  "Refactor auth module: move JWT logic to utils/auth.py"

# 2. 生成 PR
opencode --attach http://<ip> run \
  "Create branch 'feature/auth-refactor', commit changes, push to origin"

# 3. 代码审查
opencode --attach http://<ip> run \
  "Review PR #42, check for security issues, suggest improvements"
```

### 优势

- ✅ **上下文保持**: 长连接支持多轮对话
- ✅ **项目感知**: 理解整个代码库结构
- ✅ **Git 集成**: 直接创建分支、提交、PR
- ✅ **Review 能力**: 代码审查、安全扫描

### 限制

- ⚠️ 启动延迟 ~5s (首次连接)
- ⚠️ 沙盒限制：只能写入 `~` 目录
- ⚠️ 需要 Docker 命令时须 `sudo` 前缀

---

## 📡 OpenClaw 调用方式

### 场景：脚本执行、批量任务、系统调查

**三种模式**:

| 模式 | 命令 | 适用场景 | 延迟 | 方向 |
|------|------|----------|------|------|
| **`agent --local`** | `openclaw agent --local -m "任务"` | 快速单次任务 | ~3-5s | Hermes → OpenClaw |
| **ACP Bridge** | `openclaw acp client --server "hermes"` | 复杂多轮协作 | ~10s+ | OpenClaw → Hermes |
| **MCP Server** | `openclaw mcp serve` | 外部 MCP 客户端控制 OpenClaw | - | External → OpenClaw |

**⚠️ 重要架构澄清** (2026-06-30):

1. **OpenClaw 没有 `mcp serve` 命令** — 这是常见误解。OpenClaw 的 MCP 相关命令是 `openclaw mcp` (管理 MCP 配置)，不是 `openclaw mcp serve`。

2. **正确连接方向**:
   - **Hermes 调用 OpenClaw**: `openclaw agent --local --message "任务"` (Hermes 作为 client)
   - **OpenClaw 调用 Hermes**: `openclaw acp client --server "hermes"` (OpenClaw 作为 client)
   - **两者都通过 ACP 协议**，不是 MCP

3. **Hermes ACP server 必须先启动**:
   ```bash
   # 第一步：启动 Hermes ACP server
   hermes acp --accept-hooks
   
   # 第二步：验证运行中
   ps aux | grep "hermes acp" | grep -v grep
   
   # 第三步：OpenClaw 连接
   openclaw acp client --server "hermes" --cwd ~
   ```

4. **MCP vs ACP 的区别**:
   - **MCP** (Model Context Protocol): 用于外部工具/服务暴露给 AI (如 codebase-memory-mcp)
   - **ACP** (Agent Client Protocol): 用于 Agent 之间的双向通信 (Hermes ↔ OpenClaw)
   - **本架构使用 ACP**，不是 MCP

---

### 模式 A: `agent --local` (推荐首选)

```python
delegate_task(
    goal="分析 /var/log/syslog 最近 1000 行错误",
    context="""
    使用 OpenClaw 本地模式:
    
    openclaw agent --local \\
      --session-id "hermes-$(date +%s)" \\
      --message "Analyze last 1000 lines of /var/log/syslog, extract ERROR entries, summarize by category" \\
      --json
    
    解析 JSON 输出中的 payloads[0].text
    超时：60 秒
    """,
    toolsets=["terminal"],
    role="leaf"
)
```

**优势**:
- ✅ 简单直接，无需额外配置
- ✅ 自动继承 Gateway token
- ✅ 适合 90% 的单次任务场景

---

### 模式 B: ACP Bridge (高级协作)

**⚠️ 重要**: ACP client 进入交互模式，需要 PTY wrapper (tmux)！

```python
delegate_task(
    goal="多阶段系统优化",
    context="""
    使用 OpenClaw ACP 模式 (必须 tmux 包装):
    
    # 1. 创建会话
    tmux new-session -d -s oc-acp 'openclaw acp client --server "hermes" --cwd ~'
    
    # 2. 等待初始化 (关键)
    sleep 8
    
    # 3. 发送复杂任务
    tmux send-keys -t oc-acp 'Execute: Multi-phase system optimization: 1) analyze disk usage 2) find large files 3) clean apt cache 4) report savings' Enter
    
    # 4. 等待执行
    sleep 60
    
    # 5. 获取结果
    tmux capture-pane -t oc-acp -p -S -200
    
    # 6. 清理
    tmux send-keys -t oc-acp 'exit' Enter
    tmux kill-session -t oc-acp
    """,
    toolsets=["terminal"],
    role="leaf"
)
```

**完整 tmux 测试脚本**:
```bash
#!/bin/bash
# 测试 OpenClaw ACP 连接

set -e

echo "1. 创建 tmux 会话..."
tmux new-session -d -s 'oc-test' 'openclaw acp client --server hermes --cwd ~'

echo "2. 等待初始化 (8 秒)..."
sleep 8

echo "3. 发送测试命令..."
tmux send-keys -t 'oc-test' '执行：uname -a && echo ===OPENCLAW_OK===' Enter

echo "4. 等待执行 (15 秒)..."
sleep 15

echo "5. 捕获输出..."
output=$(tmux capture-pane -t 'oc-test' -p | tail -30)
echo "$output"

if echo "$output" | grep -q "OPENCLAW_OK"; then
    echo ""
    echo "[✅] OpenClaw ACP 任务执行成功"
else
    echo ""
    echo "[⚠️] 未看到预期输出，可能在执行中"
fi

echo "6. 清理会话..."
tmux send-keys -t 'oc-test' 'exit' Enter
sleep 2
tmux kill-session -t 'oc-test' 2>/dev/null || true
```

**优势**:
- ✅ 完整 Agent 能力 (Hermes 工具集)
- ✅ 会话持久化 (SessionDB)
- ✅ 支持多轮对话和上下文保持

**限制**:
- ⚠️ 需要 tmux 包装解决交互输入
- ⚠️ 延迟较高 (握手 + 推理 ~15-30s)
- ⚠️ 适合复杂任务，不适合简单脚本

**常见错误**:
```bash
# ❌ 错误 - 管道输入被 TUI 忽略
echo "uname -a" | openclaw acp client --server "hermes"

# ✅正确 - 使用 tmux
tmux new-session -d -s test 'openclaw acp client --server "hermes"'
sleep 8
tmux send-keys -t test 'uname -a' Enter
```

---

## 🎯 任务路由决策树

```
用户需求？
│
├─ 代码相关？
│   ├─ 重构/Review/PR → OpenCode (TCP)
│   └─ 简单脚本生成 → OpenClaw (agent --local)
│
├─ 系统/脚本任务？
│   ├─ 单次命令/调查 → OpenClaw (agent --local) 【首选】
│   ├─ 多阶段协作 → OpenClaw (ACP + tmux)
│   └─ 需要文件操作 → OpenClaw 或 Hermes 直接执行
│
├─ 需要上下文保持？
│   ├─ 是 → OpenCode (长连接) 或 OpenClaw (ACP)
│   └─ 否 → OpenClaw (agent --local)
│
└─ Hermes 自身能力足够？
    └─ 是 → 直接执行 (不调用外部 Agent)
```

---

## 📝 故障排查

### OpenCode 无法连接

```bash
# 1. 检查服务
systemctl status opencode-collab

# 2. 检查端口
ss -tuln | grep 8901

# 3. 重启服务
sudo systemctl restart opencode-collab

# 4. 查看日志
journalctl -u opencode-collab -n 20 --no-pager
```

### OpenClaw Gateway 异常

```bash
# 1. 检查服务
systemctl status openclaw-gateway

# 2. 健康检查
curl -s http://<ip>/health

# 3. 配置检查
cat ~/.openclaw/openclaw.json | jq .gateway

# 4. 重启服务
sudo systemctl restart openclaw-gateway

# 5. 查看日志
journalctl -u openclaw-gateway -n 30 --no-pager
```

### ACP 连接失败

```bash
# 1. 检查 Hermes ACP
systemctl --user status hermes-acp

# 2. 手动测试连接 (需要 tmux)
tmux new-session -d -s test-acp 'openclaw acp client --server "hermes" --cwd ~'
sleep 8
tmux capture-pane -t test-acp -p | grep -E "connected|Session|ERROR"
tmux kill-session -t test-acp

# 3. 查看 Hermes ACP 日志
journalctl --user -u hermes-acp -n 30 --no-pager

# 4. 常见错误
#    - PermissionError: asyncio selector issue (通常不影响功能)
#    - "ACP client connected" 但没有后续 → 检查 tmux 是否正确发送命令
#    - 管道输入被忽略 → 必须使用 tmux 或其他 PTY wrapper
```

### MCP 连接失败 (OpenCode)

```bash
# 1. 检查 OpenCode 配置
cat ~/.opencode/settings.json | jq '.mcp'

# 2. 测试 stdio 响应
echo '{"jsonrpc":"2.0","id":1,"method":"tools/list"}' | hermes mcp serve 2>&1 | head -5

# 3. 确认 OpenCode 启动日志
#    OpenCode 启动时会自动 Spawn "hermes mcp serve" 进程
#    在 OpenCode 的日志中查找 "MCP server hermes started"

# 4. 常见错误
#    - 配置缺失: 确保 ~/.opencode/settings.json 有 hermes MCP entry
#    - stdio 无响应: 检查 `hermes mcp serve --verbose` 是否有输出
#    - 重启循环: MCP server 没有 client 时会退出，这是正常行为
```

---

## 🔑 关键配置摘要

### Systemd 服务

| 文件 | 路径 |
|------|------|
| OpenCode | `/etc/systemd/system/opencode-collab.service` |
| OpenClaw | `/etc/systemd/system/openclaw-gateway.service` |

### 配置文件

| 组件 | 路径 |
|------|------|
| OpenCode | `~/.opencode/` (自动) |
| OpenClaw | `~/.openclaw/openclaw.json` |
| Hermes ACP | `~/.hermes/.env` (模型配置) |
| Hermes 心跳配置 | `~/.hermes/config.yaml` (`delegation.heartbeat_timeout_seconds`) |

### 端口一览

| 端口 | 服务 | 协议 |
|------|------|------|
| 8901 | OpenCode Collab | HTTP-like |
| 18789 | OpenClaw Gateway | WebSocket |
| 18789 | OpenClaw ACP (stdio 桥接) | ACP |

---

## ⚠️ 已知严重问题：心跳缺失导致 Batch 卡死

### 问题描述

**症状**: `delegate_task` 分发多子任务后，父 Agent 心跳停止，即使子 Agent 已完成也无法收到结果。

**根因** (2026-06-27 定位):

1. **async_delegation 的 batch completion 机制缺陷**:
   - `dispatch_async_delegation_batch()` 依赖 `runner()` 正常返回后才调用 `_finalize_batch()`
   - `runner()` 内部的子 Agent 遭遇流式超时 (`Stream stale for 180s`) 时，陷入无限重试循环
   - 子 Agent 会话未正常结束 (`ended_at=null`) → `runner()` 永不返回 → `_finalize_batch()` 永不执行
   - 父 Agent 被动等待 `completion_queue` 事件，无主动心跳检测

2. **双重故障**:
   - 子 Agent 卡住 (stuck) vs 长任务 (legitimate long-running) 无法区分
   - 父 Agent 连续 3 次工具调用失败 → 触发 AGENTS.md §4.3 保护性挂起

**真实案例** (`deleg_090439bc`, 2026-06-27):
```
deleg_090439bc (2 子任务并行)
  ├─ sa-1 (20260627_071742_6fc704) → ✅ 正常完成 (22 API 调用，692s)
  └─ sa-2 (20260627_071736_a55a08) → ❌ 流式超时
                                      → 反复重试 ReadTimeout
                                      → 会话未结束 (ended_at=null)
                                      → runner() 永不返回
                                      → _finalize_batch() 未执行
                                      → completion_queue 无事件
                                      → 父 Agent 等待 27 分钟后中断
```

### 临时解决方案

**清理卡住的会话**:
```bash
# 1. 查找未正常结束的会话
sqlite3 ~/.hermes/state.db "SELECT id, started_at, ended_at, end_reason FROM sessions WHERE ended_at IS NULL ORDER BY started_at DESC LIMIT 10;"

# 2. 强制结束卡住的会话 (替换 session_id)
sqlite3 ~/.hermes/state.db "UPDATE sessions SET ended_at=strftime('%s','now'), end_reason='manual_kill' WHERE id='20260627_071736_a55a08';"

# 3. 验证清理
sqlite3 ~/.hermes/state.db "SELECT id, ended_at, end_reason FROM sessions ORDER BY started_at DESC LIMIT 5;"
```

**重试 delegation**:
```bash
# 清理后重新分发任务
hermes delegate --goal "原任务目标" --context "原上下文"
```

### 永久修复方案 (2026-06-28 已实施)

**✅ Phase 1-3 已完成：HCP (Hermes Collaboration Protocol) 双向通信协议**

#### 架构设计

HCP 是基于 JSON-RPC 2.0 的双向通信协议，通过 Unix Socket 实现父子 Agent 间的心跳/ACK/Probing。

**组件**:
- **HCP Server** (`~/.hermes/hcp_server.py`): 监听 Unix Socket (`~/.hermes/hcp.sock`)
- **HCP Client** (`~/.hermes/hcp_client.py`): 子 Agent 导入即用
- **Integration** (`hermes-agent/utils/hcp_integration.py`): 自动集成到 `delegate_tool.py`
- **ACP Bridge** (`~/.hermes/hcp_acp_bridge.py`): 转发 OpenClaw ACP (TCP :18790) → HCP (Unix Socket)

**配置** (`config.yaml`):
```yaml
hcp:
  enabled: true
  socket_path: ~/.hermes/hcp.sock
  heartbeat_interval_seconds: 30
  probe_interval_seconds: 60
  probe_timeout_seconds: 10
  token_path: ~/.hermes/hcp.token
```

#### 心跳上报机制 (已实现)

子 Agent 启动时自动启动心跳线程：

```python
# delegate_tool.py (第 1641-1668 行)
child_task_id = _subagent_id or f"subagent-{task_index}-{_uuid.uuid4().hex[:8]}"

# 读取 HCP 配置并启动心跳
from hermes_cli.config import load_config as _load_hcp_cfg
_hcp_cfg = _load_hcp_cfg().get('hcp', {})
_hcp_enabled = _hcp_cfg.get('enabled', False)
_hcp_interval = _hcp_cfg.get('heartbeat_interval_seconds', 30)

if _hcp_enabled:
    from utils.hcp_integration import start_hcp_heartbeat
    _hcp_stop_event = start_hcp_heartbeat(
        session_id=child_task_id,
        child_agent=child,
        interval=_hcp_interval
    )
    logger.info(f"HCP heartbeat started for {child_task_id} (interval={_hcp_interval}s)")
```

#### 双指标 Stale Detection (2026-06-28 v2)

**问题**: 初始版本仅检测 `step == "idle"`，导致 `sleep` 场景被误判为 stale。

**修复**: 改用双指标判定 — `api_call_count` 不增长 **且** `step` 不变：

```python
# utils/hcp_integration.py (第 60-88 行)
prev_api_count = 0
prev_step = "idle"
stale_count = 0
max_stale = 3  # 连续 3 次 stale → 停止上报

while not stop_event.is_set():
    summary = child_agent.get_activity_summary()
    current_api_count = summary.get("api_call_count", 0)
    current_step = summary.get("current_tool", "idle") or "idle"
    
    if current_api_count == prev_api_count and current_step == prev_step:
        stale_count += 1
        if stale_count >= max_stale:
            logger.warning(f"Session {session_id} stale for {stale_count} cycles...")
            break
    else:
        stale_count = 0  # 有进展，重置
    
    prev_api_count = current_api_count
    prev_step = current_step
    
    client.heartbeat(session_id, "running", current_step, progress)
```

**效果**: `sleep` / `wait` 等被动等待场景不再误报，只有真·卡住才触发 stale。

#### 完成 ACK 协议 (已实现)

子 Agent 完成后自动发送 ACK：

```python
# delegate_tool.py (第 1805-1823 行)
finally:
    _timeout_executor.shutdown(wait=False)
    
    # 停止心跳并发送 ACK
    if _hcp_stop_event is not None:
        _hcp_stop_event.set()
        from utils.hcp_integration import send_hcp_ack
        status = "completed" if completed and not is_timeout else ("timeout" if is_timeout else "error")
        send_hcp_ack(
            session_id=child_task_id,
            status=status,
            duration_seconds=duration
        )
```

#### 主动 Probing (已实现)

HCP Server 每 60 秒主动 probing 子 Agent：

```json
// Probe 请求
{"jsonrpc":"2.0","id":1,"method":"probe","params":{"session_id":"sa-0-xxx"}}

// Probe 响应
{"jsonrpc":"2.0","id":1,"result":{"status":"running","step":"reading_file","latency_ms":0.28}}
```

**超时处理**: 10 秒无响应 → 标记 stale → 通知 Watchdog 进程。

#### OpenClaw ACP 桥接 (已实现)

**Bridge 脚本** (`hcp_acp_bridge.py`):
- 监听 TCP :18790 (不同于 OpenClaw 默认的 18789)
- 转发 ACP 消息到 HCP Unix Socket
- 支持的 ACP 方法：
  - `openclaw.ping` → 返回 `{"status":"pong"}`
  - `openclaw.task.start` → HCP `heartbeat(session_id, "running", "task_start")`
  - `openclaw.task.progress` → HCP `heartbeat(session_id, "running", step, progress)`
  - `openclaw.task.complete` → HCP `ack(session_id, status, duration)`

**实测结果** (2026-06-28):
```bash
# Ping 测试
echo '{"jsonrpc":"2.0","id":1,"method":"openclaw.ping","params":{}}' | nc <ip> 18790
# → {"jsonrpc":"2.0","id":1,"result":{"status":"pong"}}

# Task Start 测试
echo '{"jsonrpc":"2.0","id":2,"method":"openclaw.task.start","params":{"session_id":"test_acp_001"}}' | nc <ip> 18790
# → {"jsonrpc":"2.0","id":2,"result":{"ack":true,"session_id":"test_acp_001"}}
# HCP Server 日志：New session: test_acp_001
```

#### 超时保护配置 (已更新)

`config.yaml` 新增/修改：

```yaml
delegation:
  # P0 超时保护 (2026-06-28 缩短)
  child_soft_timeout_seconds: 300    # 5 分钟 → 警告 (原 600s)
  child_hard_timeout_seconds: 600    # 10 分钟 → 强制中断 (原 900s)
  batch_hard_timeout_seconds: 1800   # 30 分钟 (原 3600s)
  
  # HCP 心跳配置
  hcp_enabled: true
  hcp_heartbeat_interval: 30
  use_hcp_for_subagents: true

hcp:
  enabled: true
  socket_path: ~/.hermes/hcp.sock
  heartbeat_interval_seconds: 30
  probe_interval_seconds: 60
  probe_timeout_seconds: 10
```

#### Watchdog 集成 (已在 P1 阶段落地)

独立 Watchdog 进程 (`~/.hermes/watchdog.py`, PID 6053):
- 每 10 秒扫描 `~/.hermes/heartbeat/*.json`
- 300 秒无心跳 → SIGTERM → 10 秒 → SIGKILL
- 审计日志：`~/.hermes/watchdog_audit.jsonl`

**与 HCP 协同**:
- HCP 负责 **应用层心跳** (每 30s 上报 `step`/`progress`)
- Watchdog 负责 **进程级监控** (检测 stale 后 kill)
- HCP 的 `probe_timeout=10s` 与 Watchdog 的 `stale_threshold=300s` 互补

---

### Phase 4: 未来增强 (待实施)

**进度条 UI** (优先级 P3):
```yaml
# 父 Agent TUI 展示
[████▒▒▒▒▒] 45% - Reading large file... (剩 3 分钟)
```

**DAG 依赖管理** (长期):
```yaml
# Task Contract
depends_on: [task_1, task_2]
condition: "task_1.exit_code == 0"
```

**Circuit Breaker** (长期):
- 连续 3 次失败 → 熔断 → 指数退避重试

**Phase 2: 分级超时配置** (优先级 P1)

修改 `config.yaml`:
```yaml
delegation:
  soft_timeout_seconds: 600   # 10 分钟 → 发警告通知用户
  hard_timeout_seconds: 1800  # 30 分钟 → 询问用户是否继续
  max_timeout_seconds: 3600   # 60 分钟 → 强制 kill (可配置)
  heartbeat_interval_seconds: 30  # 心跳间隔
  heartbeat_timeout_seconds: 300  # 5 分钟无心跳判定为 stuck
```

**Phase 3: 进度上报机制** (优先级 P2)

子 Agent 定期上报:
```python
report_progress({
    "step": "reading_large_file",
    "progress_percent": 45,
    "eta_seconds": 180,
    "current_file": "/path/to/large.log"
})
```

父 Agent 展示进度条:
```
[███░░░░░] 45% - Reading large file... (剩 3 分钟)
```

### 监控建议

**添加健康检查脚本** (`~/scripts/check-delegation-health.sh`):
```bash
#!/bin/bash
# 检查超过 30 分钟未结束的 delegation

THRESHOLD=1800  # 30 分钟

stuck=$(sqlite3 ~/.hermes/state.db "
  SELECT id, started_at, (strftime('%s','now') - started_at) as duration
  FROM sessions 
  WHERE ended_at IS NULL AND duration > $THRESHOLD
  ORDER BY duration DESC;
")

if [ -n "$stuck" ]; then
    echo "⚠️ 发现卡住的子 Agent:"
    echo "$stuck"
    echo ""
    echo "建议操作:"
    echo "1. 手动结束：sqlite3 ~/.hermes/state.db \"UPDATE sessions SET ended_at=strftime('%s','now') WHERE id='...';\""
    echo "2. 查看日志：tail -100 ~/.hermes/logs/agent.log | grep <session_id>"
fi
```

---

## ✅ 最佳实践总结

1. **启动顺序**:
   ```bash
   sudo systemctl start opencode-collab openclaw-gateway
   ~/scripts/check-agent-services.sh  # 验证
   ~/scripts/check-delegation-health.sh  # 检查 delegation 健康状态
   ```

2. **默认路由**:
   - 代码任务 → OpenCode
   - 脚本/系统任务 → OpenClaw (`agent --local`)
   - 复杂协作 → OpenClaw (ACP + tmux)

3. **会话管理**:
   - OpenCode: 长连接，自动保持
   - OpenClaw ACP: tmux 包装，用完即清理
   - **Delegation: 每 5 分钟检查心跳，超过 30 分钟无心跳需手动干预**

4. **错误处理**:
   - 先检查服务状态
   - 再看端口监听
   - 最后查日志
   - **delegation 卡住 → 检查 SQLite sessions 表 → 强制结束无心跳会话**

5. **长任务处理**:
   - 预期超过 10 分钟的任务 → 提前告知用户
   - 预期超过 30 分钟的任务 → 使用进度上报机制
   -  batch 中任一子任务卡住 → 其他子任务结果仍会丢失 (batch 无法部分交付)

---

## 🔮 架构演进计划

**当前局限** (2026-06-25 评估):
1. ❌ 无 worktree 隔离 → 子 Agent 文件冲突风险
2. ❌ 无心跳检测 → 无法识别卡死的子 Agent
3. ❌ 无失败重试 → 单次失败即放弃
4. ❌ 无任务状态机 → 仅 pending/completed 两态
5. ❌ 无依赖管理 → 无法表达 DAG 任务关系

**改进路线图** (详见 `agent-fleet-orchestration` skill):
- **Phase 1** (1-2 周): Worktree 隔离 — 添加 `worktree_id` 参数
- **Phase 2** (2-3 周): Freshness 调度器 — 心跳检测 + hung 判定
- **Phase 3** (1-2 周): 电路断路器 — 失败重试 + 指数退避
- **Phase 4** (长期): 决策门 — 阻塞任务等待外部事件

**目标架构** (参考 Orca 模式):
```
┌──────────────────────────────────────────────────────────┐
│         Hermes (主脑 + Coordinator)                    │
│  新增：状态机/心跳调度/电路断路器/决策门/Worktree 管理     │
└────────────┬─────────────────────┬───────────────────────┘
      - agent协作
      - 调度子agent
      - agent配合

             │                     │
     ┌───────▼────────┐   ┌───────▼────────┐
     │   OpenCode     │   │   OpenClaw     │
     │  worktree-A    │   │  worktree-B    │
     │  (隔离 cwd)    │   │  (隔离 cwd)    │
     └────────────────┘   └────────────────┘
```

---

## References

- **最终测试报告** (2026-06-30): `~/.hermes/workspace/hermes-final-test-report.md` — 完整硬件检测和多 Agent 连接测试结果
- **连接配置文档** (2026-06-30): `~/.hermes/workspace/hermes-multi-agent-connection.md` — systemd 服务配置和持久化方案
- **ACP 架构验证** (2026-06-30): `references/acp-architecture-verification-2026-06-30.md` — OpenClaw 通过 ACP 连接 Hermes 的完整实测记录，常见误解澄清，快速启动脚本
- **HCP Protocol Spec**: `references/hcp-protocol-spec-v1.0.md` — Complete JSON-RPC message formats, stale detection v2 algorithm, ACP bridge mapping
- **ACP 实测数据**: `references/acp-verification-2026-06-24.md` — 完整连接日志、性能数据、问题排查记录
- **心跳故障报告**: `references/delegation-heartbeat-failure-2026-06-27.md` — deleg_090439bc 详细分析报告
- **硬件检测报告**: `~/hardware_report.json` — OpenClaw ACP 执行的完整硬件检测结果
- **健康检查脚本**: `scripts/check-agent-services.sh` — 自动检测所有 Agent 服务状态
- **ACP tmux 测试脚本**: `scripts/test-acp-connection.sh` — OpenClaw ACP 连接自动化测试
- **HCP 全链路测试**: `scripts/test-hcp-full-chain.py` — 5-in-1 test suite (Server/Heartbeat/ACK/Bridge/Stale v2)
- **Systemd 服务**: 
  - `~/.config/systemd/user/hermes-acp.service` (Hermes ACP server)
  - `/etc/systemd/system/openclaw-gateway.service` (OpenClaw Gateway)
- **配置文件**:
  - `~/.opencode/settings.json` (OpenCode MCP)
  - `~/.openclaw/openclaw.json` (OpenClaw Gateway)
- **Related Skills**: `hermes-agent`, `openclaw`, `opencode`

---

## Changelog

- **1.2.0** (2026-06-30): 
  - 修正架构理解：Hermes MCP server 是 stdio 模式，不由 systemd 运行
  - 添加 Hermes ACP server systemd 持久化配置
  - 澄清 OpenClaw 连接方向 (Hermes → OpenClaw vs OpenClaw → Hermes)
  - 添加 ACP tmux wrapper 完整测试脚本
  - 添加 OpenCode MCP 配置示例和 stdio 测试方法
  - 故障排查更新：区分 ACP 和 MCP 的不同调试方法
- **1.1.0** (2026-06-24): Added ACP verification data from production test — session `df975c1e-f1cc-4021-847c-86eb3f5f0563` confirmed working, performance benchmarks, tmux automation pattern, user preference for "主脑模式"
- **1.0.0** (2026-06-24): Initial version

---

*Generated by Hermes*  
*Last updated: 2026-06-24*

---

## Consolidation Note (2026-07-08 curator pass)

The following previously-standalone skills are **absorbed into this umbrella** — their content is fully covered by the sections above. Their unique reference material has been re-homed:

- `openclaw` -> `references/openclaw/` (acp-bridge.md, connection-tests.md, mcp-server-integration.md)
- `opencode` -> the OpenCode calling / Server Mode sections (flags, PR review, pitfalls)
- `hcp-collaboration-protocol` -> `references/hcp-protocol-spec-v1.0.md` + the Timeout/Heartbeat patterns
- `agent-collaboration-architecture` -> the architecture overview + integration-path decision matrix

Do NOT recreate these as separate skills; extend the relevant section here instead.