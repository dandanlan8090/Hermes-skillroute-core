# Hermes MCP Server Integration

## Overview

Hermes can run as an MCP (Model Context Protocol) server to expose its messaging gateway conversations and platform integrations to external MCP clients like OpenCode, Claude Code, or Cursor.

**Key distinction**: This is **separate from** the ACP server (`hermes acp`) which is used for OpenClaw integration.

| Server | Protocol | Used By | Purpose |
|--------|----------|---------|---------|
| `hermes acp` | ACP (Agent Client Protocol) | OpenClaw | OpenClaw → Hermes tool access |
| `hermes mcp serve` | MCP (Model Context Protocol) | OpenCode, Claude Code, Cursor | External clients → Hermes messaging gateway |

## Starting Hermes MCP Server

### Manual Start

```bash
# Start Hermes as MCP server (stdio mode)
hermes mcp serve --verbose

# Expected output (debug mode):
# DEBUG:hermes.mcp_serve:EventBridge started
# DEBUG:mcp.server.lowlevel.server:Initializing server 'hermes'
# DEBUG:mcp.server.lowlevel.server:Registering handler for ListToolsRequest
# ...
```

**Important**: The MCP server uses **stdio protocol** — it does NOT listen on a TCP port. It expects JSON-RPC messages via stdin and responds via stdout. External clients spawn it as a subprocess and communicate via pipes.

### Verification

```bash
# Test that MCP server starts (will timeout after 5s)
timeout 5 hermes mcp serve --verbose 2>&1 | head -20

# Expected output:
# DEBUG:hermes.mcp_serve:EventBridge started
# DEBUG:mcp.server.lowlevel.server:Initializing server 'hermes'
# DEBUG:mcp.server.lowlevel.server:Registering handler for ListToolsRequest
# DEBUG:mcp.server.lowlevel.server:Registering handler for CallToolRequest
# ...
```

## MCP Tools Provided

The Hermes MCP server exposes the following tools to connected clients:

| Tool | Description |
|------|-------------|
| `conversations_list` | List all messaging conversations across connected platforms |
| `conversation_get` | Get full message history for a specific conversation |
| `messages_read` | Read messages from a conversation (with pagination) |
| `messages_send` | Send messages via connected platforms (Telegram, Discord, Slack, etc.) |
| `events_poll` | Poll for new events/messages from platforms |
| `channels_list` | List all connected platform channels and their status |
| `permissions_list_open` | List pending approval requests (command approvals, plugin requests) |
| `permissions_respond` | Respond to approval requests (allow/deny) |

## Client Configuration

### OpenCode

Add to your OpenCode MCP configuration (usually `~/.config/opencode/mcp.json` or `opencode.json`):

```json
{
  "mcpServers": {
    "hermes": {
      "command": "hermes",
      "args": ["mcp", "serve"]
    }
  }
}
```

### Claude Code

Add to Claude Desktop config (`claude_desktop_config.json`):

```json
{
  "mcpServers": {
    "hermes": {
      "command": "hermes",
      "args": ["mcp", "serve"]
    }
  }
}
```

### Cursor

Add to Cursor MCP config (`.cursor/mcp.json` in project root or global):

```json
{
  "mcpServers": {
    "hermes": {
      "command": "hermes",
      "args": ["mcp", "serve"]
    }
  }
}
```

## Architecture Diagram

```
┌─────────────────┐                                    ┌─────────────────┐
│  OpenCode /     │                                    │   Hermes MCP    │
│  Claude Code /  │◄─────── stdio (JSON-RPC) ─────────►│     Server      │
│  Cursor         │                                    │                 │
└─────────────────┘                                    └────────┬────────┘
                                                                │
                                                                │
                                                                ▼
                     ┌──────────────────────────────────────────────────┐
                     │          Hermes Agent Core                        │
                     │  ┌────────────────────────────────────────────┐  │
                     │  │  Messaging Gateway                         │  │
                     │  │  ├─ Telegram                               │  │
                     │  │  ├─ Discord                                │  │
                     │  │  ├─ Slack                                  │  │
                     │  │  ├─ WhatsApp                               │  │
                     │  │  └─ ... (20+ platforms)                    │  │
                     │  └────────────────────────────────────────────┘  │
                     └──────────────────────────────────────────────────┘
```

## Use Cases

1. **Unified messaging from code editor**: Send/receive messages across all platforms without leaving your editor
2. **Automated notifications**: Code CI/CD events → send notifications to Telegram/Discord
3. **Conversation analytics**: Analyze message patterns, response times, platform usage
4. **Multi-platform bot management**: Manage bot responses across platforms from a single interface

## Troubleshooting

### MCP server exits immediately

**Cause**: The server expects stdin input. When run in a terminal without piped input, it may appear to "exit immediately" because there's no client sending JSON-RPC messages.

**Solution**: This is normal behavior when testing manually. Configure your MCP client (OpenCode, etc.) to spawn the server — the client will handle the stdio communication.

### No tools showing up in client

**Cause**: Client failed to spawn the server or MCP SDK not available.

**Verification**:

```bash
# Check if MCP SDK is installed
~/.hermes/hermes-agent/venv/bin/python -c "from mcp.server.fastmcp import FastMCP; print('OK')"

# Expected: OK
```

**Fix**: Install MCP SDK if missing:

```bash
~/.hermes/hermes-agent/venv/bin/pip install mcp
```

### Permission denied errors

**Cause**: Hermes requires approval for certain actions (command execution, platform operations).

**Solution**: Use the `permissions_list_open` and `permissions_respond` tools to manage approvals, or start Hermes with `--accept-hooks` flag for auto-approval (use with caution).

## Security Considerations

1. **Token management**: Hermes MCP server inherits all authentication from the main Hermes instance — ensure your `~/.hermes/.env` and platform tokens are secured.
2. **Command approval**: By default, Hermes requires approval for shell commands. MCP clients can respond to approval requests via `permissions_respond`.
3. **Platform access**: MCP clients get full access to all connected messaging platforms. Only configure MCP servers you trust.

## Related Documentation

- Main skill: `skill_view(name='openclaw')` — See "MCP Server Mode" section
- ACP integration: `skill_view(name='openclaw', file_path='references/acp-bridge.md')`
- Official MCP spec: https://modelcontextprotocol.io/

## Session Notes (2026-06-30)

This reference was created after clarifying the confusion between:
- **OpenClaw ACP client** → connects to Hermes ACP server
- **Hermes MCP server** → serves external MCP clients (OpenCode, etc.)
- **OpenClaw MCP server** → exposes OpenClaw Channels (different from Hermes MCP)

Key discovery: `hermes mcp serve` uses stdio protocol, not TCP — it's meant to be spawned by MCP clients, not run standalone.