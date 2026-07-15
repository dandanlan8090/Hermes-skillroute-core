# graphify-mcp setup (verified 2026-07-14)

## What it solves
graphify-mcp serves a pre-built `graphify-out/graph.json` over MCP, exposing 10 tools including PR triage, blast-radius analysis, and community detection that codebase-memory does NOT cover. Unlike codebase-memory (auto-incremental indexing), graphify-mcp is a **static graph server** — the graph must already exist before wiring MCP.

## Install (one-time)
```bash
uv tool install "graphifyy[mcp,chinese]"
which graphify-mcp    # ~/.local/share/uv/tools/graphifyy/bin/graphify-mcp
graphify-mcp --help
```

## Build a graph FIRST (mandatory before MCP wiring)

| Scenario | Command |
|----------|---------|
| Code-only, no LLM keys needed | `graphify <path> --code-only` |
| Full pipeline (docs/video/images) | `graphify <path>` (needs LLM key) |
| Incremental update | `graphify update <path>` |
| Relabel communities | `graphify cluster-only <path>` |

Verified example:
```bash
cd ~/.hermes/skills
graphify . --code-only
# → graphify-out/graph.json (~600KB, 531 nodes / 918 edges / 53 communities)
```

## Register MCP (standard pattern)
```bash
hermes config set mcp_servers.graphify.command \
  ~/.local/share/uv/tools/graphifyy/bin/graphify-mcp
hermes config set mcp_servers.graphify.args \
  '["--graph","~/.hermes/skills/graphify-out/graph.json"]'
hermes config set mcp_servers.graphify.env '{}'
```
Then **fix the string-storage pitfall** (the main SKILL.md Step 1 fix block — config set stores args/env as strings).

## Optional: point graphify's LLM at host's main model
For a self-hosted OpenAI-compatible endpoint that does not enforce auth, set env vars in mcp_servers.graphify.env:
```yaml
OPENAI_BASE_URL: "http://<proxy-host>:6327/v1"
OPENAI_API_KEY: "dummy"
GRAPHIFY_OPENAI_MODEL: "<main-model>"
```
> PITFALL — dummy key only works against local/non-auth proxies. Real OpenAI/Anthropic will 401.

## Verify
```bash
hermes mcp list        # graphify ✓ enabled
hermes mcp test graphify   # ✓ Connected + 10 tools
```
10 tools: query_graph / get_node / get_neighbors / get_community / god_nodes / graph_stats / shortest_path / list_prs / get_pr_impact / triage_prs

## Usage boundaries (crucial — don't misuse)
| Task | Right tool |
|------|-----------|
| "Who calls function X?" | codebase-memory (`trace_path`) |
| "Cypher query this codebase" | codebase-memory (`query_graph`) |
| "Code complexity/entropy analysis" | codebase-memory (`get_architecture`) |
| "Track architectural decisions" | codebase-memory (`manage_adr`) |
| **"What's this PR's blast radius?"** | **graphify-mcp (`get_pr_impact`)** |
| **"Which PRs to review right now?"** | **graphify-mcp (`triage_prs`)** |
| "Show me the graph visualization" | graphify-mcp (`graph_stats`/`god_nodes`) |
| "Build a graph including PDFs/videos" | graphify CLI (`graphify <path>`) |

Anti-shorthand: codebase-memory = code intel engine. graphify-mcp = PR review + static graph viz. Don't ask graphify about function callers; don't ask codebase-memory about PRs.

## Environment
- Package: `graphifyy` 0.9.15 (PyPI; CLI name is `graphify`)
- MCP binary: `graphify-mcp` (shipped in same package, accessed through `[mcp]` extra)
- License: MIT
- Docs: https://github.com/Graphify-Labs/graphify
