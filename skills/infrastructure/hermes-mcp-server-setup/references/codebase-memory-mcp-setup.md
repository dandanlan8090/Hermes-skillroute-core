# codebase-memory-mcp — Setup & Verify Recipe (verified 2026-07-14)

## What it is
codebase-memory-mcp (DeusData/Scrapling, MIT, 31k⭐) is a high-performance
code intelligence MCP server. Single static C binary, zero dependencies,
158 languages via tree-sitter, LSP-grade cross-file call/usage resolution,
persistent SQLite knowledge graph, Cypher query support.

14 MCP tools: `index_repository`, `search_graph`, `query_graph`, `trace_path`,
`get_code_snippet`, `get_graph_schema`, `get_architecture`, `search_code`,
`list_projects`, `delete_project`, `index_status`, `detect_changes`,
`manage_adr`, `ingest_traces`.

## Backstory — was installed but not natively wired
The binary was installed (2026-06-29) via `curl ... | bash` to
`~/.local/bin/codebase-memory-mcp` v0.8.1, and config existed in
`~/.hermes/mcp.json` (the server's own config file, NOT Hermes's config.yaml).
As a result `hermes mcp list` showed only scrapling — codebase-memory was
invisible to the agent. User's verdict: "不然很容易变成摆设". This recipe
fixes that by wiring into Hermes's native mcp_servers.

## Install (if binary not yet present)
```bash
curl -fsSL https://raw.githubusercontent.com/DeusData/codebase-memory-mcp/main/install.sh | bash
codebase-memory-mcp --version    # verify binary
```

## Wire into Hermes native MCP (the only correct path)
```bash
# Step 1: register via hermes config set
hermes config set mcp_servers.codebase-memory.command ~/.local/bin/codebase-memory-mcp
hermes config set mcp_servers.codebase-memory.args '[]'
hermes config set mcp_servers.codebase-memory.env '{}'

# Step 2: fix the string-storage pitfall (same as scrapling)
cd ~/.hermes && python3 -c "
import yaml
with open('config.yaml') as f: cfg = yaml.safe_load(f)
cfg['mcp_servers']['codebase-memory']['args'] = []
cfg['mcp_servers']['codebase-memory']['env'] = {}
with open('config.yaml', 'w') as f: yaml.dump(cfg, f, default_flow_style=False, allow_unicode=True, sort_keys=False)
print('done')
"

# Step 3: verify config
grep -nA4 'codebase-memory:' ~/.hermes/config.yaml
# Expect: args: []  (no quotes)  env: {}  (no quotes)

# Step 4: authoritative test
hermes mcp test codebase-memory
# Expect: ✓ Connected | ✓ Tools discovered: 14
```

## Verify existing index
```bash
codebase-memory-mcp cli list_projects
codebase-memory-mcp cli index_status '{"project":"home-lan-.hermes-skills"}'
# Project name auto-derived from repo path: "/" → "-", "." → "-"
```

## Update index after code changes
Two approaches:
1. **Via MCP tool** (in-session, after /reset): `detect_changes` →
   `index_repository` with `mode=fast` for incremental update.
2. **Via CLI** (terminal, any time): `codebase-memory-mcp cli index_repository
   '{"repo_path":"/path","project":"name","mode":"fast"}'`

Verified 2026-07-14: detect_changes found 4 changed files (skill patches from
this session), fast re-index produced 6774 nodes / 6672 edges / status=ready.

## Graph schema (hermes-skills project, 2026-07-14)
Node labels: Section(6908) / Variable(552) / File(449) / Module(447) /
Class(420) / Function(273) / Method(135) / Folder(188) / Route(2) /
Decorator(3) / Project(1).

Edge types: DEFINES(8735→6672) / CALLS(536) / USAGE(407) /
SEMANTICALLY_RELATED(120) / WRITES(112) / IMPORTS(70) / TESTS(16) /
HTTP_CALLS(2) / DECORATES(8) / RAISES(2) / SIMILAR_TO(4).

Function/Method nodes carry complexity properties: cyclomatic, cognitive,
loop_count, loop_depth, transitive_loop_depth, linear_scan_in_loop,
alloc_in_loop, recursion_in_loop, unguarded_recursion, param_count,
max_access_depth — all queryable via Cypher for hot-path analysis.

## vs Graphify (positioning)
codebase-memory = persistent code query engine (SQLite, Cypher, complexity,
ADR, trace ingestion). Graphify = code+docs+media knowledge graph (report
generation, community detection, graph.html visualization, 20+ platform
skill install). They complement, not compete. See `graphify` skill for
Graphify's install recipe and positioning.
