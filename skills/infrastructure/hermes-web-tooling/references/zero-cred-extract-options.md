# Zero-credential extract options — the `web_extract` gap

Condensed knowledge bank from the 2026-07-14 session where `web_extract` was proven
still broken under the ddgs backend.

## Verified fact (the core pitfall)
- `web_search`'s default backend enum (from `tools/web_tools.py`): `parallel`, `firecrawl`,
  `tavily`, `exa`, `searxng`, `brave-free`, `ddgs`, `xai`.
- **ddgs is search-only.** When `web_extract` runs under `web.backend=ddgs` (or
  `web.extract_backend=ddgs`, or `extract_backend` empty → falls back to `backend`),
  it returns: `DuckDuckGo (ddgs) is a search-only backend and cannot extract URL content`.
- Confirmed live 2026-07-14: `web_extract` on `https://github.com/D4Vinci/Scrapling` README
  errored with exactly that string. So post-ddgs-fix, `web_extract` is still non-functional
  with zero credentials.

## Why yesterday's fix only half-worked
- Root cause of the original "Web tools are not configured" error: `web.backend: firecrawl`
  with no Firecrawl key. Fix = install `ddgs` in Hermes venv + `hermes config set web.backend ddgs`.
- That restores `web_search`. It does NOT restore `web_extract`, because ddgs has no extract path.
- Current env state after fix: `web.backend=ddgs`, `web.search_backend=ddgs`,
  `web.extract_backend=''` (empty → falls back to ddgs → extract errors).

## Candidate extract backends (none zero-credential except #1)
1. **SearXNG** — free, self-hostable meta-search. Set `web.extract_backend: searxng` +
   `SEARXNG_URL=http://host:port`. Best general zero-key extract, but needs a running service.
2. **Firecrawl / Tavily / Exa** — high quality, require API key / paid plan.
3. **Local libraries (not via `web_extract` config)** — call directly in Python:
   - `newspaper3k` — article/body-text extraction, articles only, zero service.
   - `D4Vinci/Scrapling` (BSD-3, 69k⭐, v0.4.11) — adaptive scraping framework with a
     **built-in MCP server** that extracts targeted content before handing to the AI
     (reduces token usage). Ships a Docker image with browsers. Strong candidate to wire
     into Hermes's MCP layer as the extract path — both zero-key and AI-native.
4. **Browser tool** — `browser_navigate` + `browser_snapshot` pulls rendered text today
   (how the Scrapling repo README was actually fetched this session). Workaround, not a
   `web_extract` fix; cannot be selected via backend config.

## Decision baseline for this environment
With zero credentials and no running service: `web_extract` is broken. Either stand up
SearXNG or accept the browser-tool workaround. `web_search` is fine via ddgs.
