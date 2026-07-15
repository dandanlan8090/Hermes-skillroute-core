---
name: hermes-verification-workflow
description: Hermes 质量验证工作流 — 子 agent 结果验证 → (失败→返工) → 通过→交付。包含硬件/服务/MCP/ACP 四项验证模板。
trigger: 当子 agent (OpenClaw/OpenCode/delegate_task) 返回检测结果、服务状态、配置报告时
---

## 触发条件

当子 agent 完成检测/测试任务并返回报告后，**必须**先执行验证流程，不得直接交付。

## 验证步骤

### 1. 硬件报告验证

```python
from hermes_tools import terminal
import json

report = json.load(open('/path/to/report.json'))

# CPU 验证
cpu_actual = terminal("lscpu | grep 'Model name' | cut -d: -f2 | xargs")['output'].strip()
cpu_ok = report['cpu']['model'] in cpu_actual

# 内存验证
mem_actual = int(terminal("free -g | grep Mem | awk '{print $2}'")['output'].strip())
mem_ok = abs(mem_actual - report['memory']['total_gb']) < 0.5

# 磁盘验证
disk_actual = int(terminal("df -h / | tail -1 | awk '{print $5}' | tr -d '%'")['output'].strip())
disk_ok = abs(disk_actual - report['disk']['root']['use_percent']) < 2

# Python 版本验证
py_actual = terminal("python3 --version | cut -d' ' -f2")['output'].strip()
py_ok = py_actual == report['runtimes']['python']['version']

hardware_valid = all([cpu_ok, mem_ok, disk_ok, py_ok])
```

**判定标准**: 所有项必须通过，允许误差（内存±0.5GB，磁盘±2%）

### 2. 服务状态验证

```python
# Hermes ACP
acp_status = terminal("systemctl --user is-active hermes-acp")['output'].strip()
acp_ok = acp_status == "active"

# OpenClaw Gateway
gw_listening = int(terminal("ss -tlnp | grep 18789 | wc -l")['output'].strip()) > 0

services_valid = acp_ok and gw_listening
```

### 3. MCP 连接验证

```python
import json

# 检查配置文件
with open('~/.opencode/settings.json') as f:
    mcp_config = json.load(f)
mcp_ok = 'hermes' in mcp_config.get('mcp', {}).get('servers', {})

# 测试 stdio 响应（必须使用完整 initialize 消息）
init_msg = json.dumps({
    "jsonrpc": "2.0",
    "id": 1,
    "method": "initialize",
    "params": {
        "protocolVersion": "2024-11-05",
        "capabilities": {},
        "clientInfo": {"name": "hermes-validator", "version": "1.0"}
    }
})
mcp_test = terminal(f"echo '{init_msg}' | timeout 3 hermes mcp serve 2>&1")
mcp_responds = 'result' in mcp_test['output'] and 'serverInfo' in mcp_test['output']

mcp_valid = mcp_ok and mcp_responds
```

**关键点**: 必须使用完整的 JSON-RPC initialize 消息，简化消息会返回 error 导致误判。

### 4. ACP 连接验证

```python
acp_service = terminal("systemctl --user is-active hermes-acp")
acp_valid = acp_service['output'].strip() == "active"

# 可选：快速连接测试
acp_quick = terminal("timeout 3 bash -c 'echo \"exit\" | openclaw acp client --server hermes 2>&1' | grep -c 'connected'")
quick_connect = int(acp_quick['output'].strip()) > 0  # 超时也算正常（需要 PTY）
```

## 决策逻辑

```python
all_valid = all([hardware_valid, services_valid, mcp_valid, acp_valid])

if all_valid:
    print("✅ 所有验证通过 → 整理交付")
    # 生成最终报告，标注"已验证"
else:
    print("❌ 存在错误 → 返工重测")
    # 列出失败项，派发返工任务给子 agent
    failed = [k for k, v in results.items() if not v]
    # delegate_task(goal=f"修复以下问题后重测：{failed}", ...)
```

## 交付要求

验证通过的报告必须包含：

1. **验证声明**: 明确标注"已验证"状态
2. **验证记录**: 列出 4 项验证的实际比对结果
3. **问题修复记录**: 如果初测失败，记录根本原因和修复方法
4. **验证者签名**: Hermes (质量验证) + 协助 Agent 名称

## 常见陷阱

1. **MCP stdio 测试误报**: 简化 JSON 消息会返回 error，必须用完整 initialize
2. **MCP systemd 重启循环**: 是预期行为（stdio 模式），应禁用服务
3. **ACP 管道输入无效**: 需要 PTY wrapper（tmux）才能执行任务
4. **内存单位误差**: `free -g` 是整数，允许±0.5GB 误差

## 参考案例

- 2026-06-30: OpenClaw 硬件检测 + MCP 配置验证
- 发现问题：MCP 测试误报 → 修复：完整 JSON-RPC → 重测通过 → 交付