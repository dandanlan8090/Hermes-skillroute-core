# OpenClaw ACP Bridge: Hermes ↔ OpenClaw Agent Collaboration

**Investigation Date**: 2026-06-24  
**Status**: ✅ Functional (interactive TUI requires PTY wrapper)

---

## Overview

The ACP (Agent Client Protocol) bridge enables **true Agent-to-Agent collaboration** where:
- **OpenClaw** acts as ACP client (user-facing interface)
- **Hermes** acts as ACP server (execution backend with full toolset)
- Communication: stdio pipe (subprocess)

This is fundamentally different from:
- `openclaw agent --local` (stateless, embedded model only)
- `openclaw mcp serve` (exposes Channels API, not Agent execution)

---

## Architecture

```
User Request
    ↓
openclaw acp client --server "hermes"
    ↓ stdio (JSON-RPC)
Hermes ACP Server (acp_adapter)
    ↓
Hermes Agent Core (full toolset + memory + skills)
```

**Key advantage**: OpenClaw inherits **ALL** Hermes capabilities:
- terminal, file, browser, cron, delegation
- skills (auto-loaded from ~/.hermes/skills/)
- memory (holographic + user profile)
- session_search (cross-session recall)

---

## Setup & Connection

### Prerequisites

```bash
# 1. Verify Hermes ACP
hermes acp --check  # Output: "Hermes ACP check OK"

# 2. Verify OpenClaw
openclaw --version  # Output: OpenClaw 2026.6.10+

# 3. Verify Hermes model configured
cat ~/.hermes/.env | grep -E "NVIDIA|OPENROUTER" | head -3
```

### Connection Command

```bash
openclaw acp client --server "hermes" --cwd ~ -v
```

**Critical syntax**:
- ✅ `--server "hermes"` (OpenClaw auto-appends `acp`)
- ❌ `--server "hermes acp"` → ENOENT
- ❌ `--server-args "acp"` → `hermes acp acp` duplication

---

## Testing

### Quick Test (10s)

```bash
timeout 10 openclaw acp client --server "hermes" --cwd ~ 2>&1 | \
  grep -E "session|Session|Initialize"
```

**Expected**:
```
[INFO] acp_adapter.server: ACP client connected
[INFO] acp_adapter.session: Created ACP session <uuid>
OpenClaw ACP client
Session: <uuid>
```

### Full Test with tmux (90s)

```bash
tmux new-session -d -s 'acp-test' 'openclaw acp client --server hermes --cwd ~'
sleep 8
tmux send-keys -t 'acp-test' 'Execute: echo ACP_TEST_SUCCESS' Enter
sleep 30
tmux capture-pane -t 'acp-test' -p | grep ACP_TEST_SUCCESS
tmux send-keys -t 'acp-test' 'exit' Enter
sleep 2 && tmux kill-session -t 'acp-test'
```

---

## Automation Pattern (tmux wrapper)

```python
import subprocess, time

def run_acp_task(prompt, workdir="~", timeout=90):
    session = f"acp-{int(time.time())}"
    
    subprocess.run(["tmux", "new-session", "-d", "-s", session,
        "openclaw", "acp", "client", "--server", "hermes", "--cwd", workdir])
    
    time.sleep(8)  # Init
    subprocess.run(["tmux", "send-keys", "-t", session, prompt, "Enter"])
    time.sleep(timeout - 15)
    
    result = subprocess.run(["tmux", "capture-pane", "-t", session, "-p"],
        capture_output=True, text=True)
    
    subprocess.run(["tmux", "send-keys", "-t", session, "exit", "Enter"])
    time.sleep(2)
    subprocess.run(["tmux", "kill-session", "-t", session])
    
    return result.stdout
```

---

## Decision Tree

```
Task requirement?
├─ Quick one-shot (< 60s)
│   └─ ✅ openclaw agent --local
│
├─ Code development
│   └─ ✅ opencode --attach http://<ip>
│
├─ Need Hermes memory/skills?
│   └─ ✅ openclaw acp client --server hermes + tmux
│
└─ External MCP client
    └─ ✅ openclaw mcp serve
```

---

## Known Issues

| Issue | Workaround |
|-------|------------|
| Piped input ignored | Use tmux wrapper (TTY required) |
| `--server-args "acp"` fails | Use `--server "hermes"` only |
| Session timeout (>90s) | Split task or increase Hermes timeout |
| `Method not found` on retry | Restart Hermes ACP or use new client info |

---

*Session: 2026-06-24 | Hermes investigation*