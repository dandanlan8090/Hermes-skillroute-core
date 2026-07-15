# Web backend — source evidence & self-host notes

## Source facts (tools/web_tools.py, Hermes v0.18.2)
- `_LEGACY_WEB_BACKENDS = {"parallel","firecrawl","tavily","exa","searxng","brave-free","ddgs","xai"}`
- `_get_backend()` priority:
  1. `web.backend` from config (if in the set or a registered provider)
  2. env-var probe, paid beats free: tavily->exa->parallel->firecrawl->firecrawl(gateway)->searxng->brave-free->ddgs
  3. fallback to `"firecrawl"` (backward compat) — this is why missing config still "selects" firecrawl and errors.
- `_is_backend_available("ddgs")` -> `_ddgs_package_importable()` (imports `ddgs`). No env var required.
- `web.search_backend` / `web.extract_backend` override per-capability (e.g. searxng for search + firecrawl for extract).
- Real handlers: `web_search_tool(query, limit=5)`, `web_extract_tool(...)` — registered as `web_search` / `web_extract`.
- `web_tools.py` lazy-dep: `search.firecrawl -> firecrawl-py==4.17.0`.

## Firecrawl self-host path correction (verified 2026-07-13)
- Correct repo: `github.com/firecrawl/firecrawl` (150k star, AGPL-3.0, active). The old `firecrawl-dev/firecrawl` path is dead (404/redirect).
- Self-host docs live at `docs.firecrawl.dev/contributing/self-host` (NOT `/self-host/*` — v2 docs moved it under `contributing`).
- Compose file is `docker-compose.yaml` at repo root (NOT `.yml`).
- Stack (7 containers): playwright-service, api (:3002), redis, rabbitmq, nuq-postgres, foundationdb, foundationdb-init. Heavy — not lightweight.
- Self-host caveats: `/agent` and `/browser` endpoints unsupported; no Fire-engine (anti-bot) features; needs `OPENAI_API_KEY` for LLM post-processing (raw fetch works without). Local LLMs via `OLLAMA_BASE_URL` (experimental) — a self-host-only advantage.
- To wire a self-hosted instance into Hermes: set `FIRECRAWL_API_URL=http://localhost:3002` (and optionally `FIRECRAWL_API_KEY`), then `hermes config set web.backend firecrawl`.

## DuckDuckGo (ddgs) quality note
ddgs results are routed through DuckDuckGo which may surface Bing-sponsored links (`bing.com/aclick?ld=...` with encoded URLs). Filter/skip those when parsing. Acceptable for "can it crawl" needs; prefer searxng/firecrawl when result cleanliness matters.
