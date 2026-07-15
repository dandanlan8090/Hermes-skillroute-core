# Scrapling MCP — install & wire into Hermes (verified 2026-07-14)

Scrapling (D4Vinci/Scrapling, BSD-3, ~69k⭐) is a Python scraping framework
with a **built-in MCP server**. Its `get`/`fetch`/`stealthy_fetch` tools extract
targeted content (CSS selector) *before* handing to the AI — reducing tokens vs
extractors that dump the whole page. Zero API key. Fills Hermes's `web_extract`
gap. The general Hermes registration mechanism is in the parent SKILL.md.

## Install (into Hermes venv — NOT system python)
Find it: `hermes --version` → "Install directory: <DIR>"; venv = `<DIR>/venv/bin`.
```bash
V=<DIR>/venv/bin/python
$V -m pip install "scrapling[full,fetchers,playwright,mcp,ai]" playwright
$V -m pip install curl_cffi        # Fetcher/HTTP needs curl_cffi (separate `fetchers` extra; [full] may not pull it)
PLAYWRIGHT_DOWNLOAD_HOST=https://cdn.npmmirror.com/binaries/playwright \
  $V -m playwright install chromium
```
> PITFALL: `scrapling install` runs `playwright install-deps chromium` (needs
> root, fails as normal user) — IGNORE it; the chromium binary alone is enough
> (verified: DynamicFetcher launched headless Chromium OK).

## Verify (real network)
```python
from scrapling.fetchers import Fetcher, DynamicFetcher
print(len(Fetcher.get('https://quotes.toscrape.com/').css('.quote .text::text').getall()))
print(len(DynamicFetcher.fetch('https://quotes.toscrape.com/', headless=True).css('.quote .text::text').getall()))
t=' '.join(s.strip() for s in Fetcher.get('https://github.com/D4Vinci/Scrapling').css('article.markdown-body ::text').getall() if s.strip())
print(len(t),'chars')   # ~18k — closes the web_extract gap in one call
```

## Register (see parent SKILL.md for the mechanism + string pitfall)
```bash
hermes config set mcp_servers.scrapling.command <DIR>/venv/bin/scrapling
hermes config set mcp_servers.scrapling.args '["mcp"]'   # fix string→list after
hermes config set mcp_servers.scrapling.env '{}'         # fix string→dict after
```
Then NEW session → `hermes mcp test scrapling` → ✓ Connected, ✓ 10 tools.

> PITFALL: `scrapling mcp` is a CLI subcommand on the executable — NOT
> `python -m scrapling mcp` (errors `No module named scrapling.__main__`).
> The wheel has NO `scrapling.mcp_server` module; the server IS the `scrapling mcp` command.

## The 10 MCP tools
get / bulk_get (HTTP, fingerprint impersonation, HTTP/3) ·
fetch / bulk_fetch (Chromium dynamic) ·
stealthy_fetch / bulk_stealthy_fetch (Cloudflare/anti-bot) ·
open_session / close_session / list_sessions (persistent browser sessions) ·
screenshot (image block the model can see).

## Author's usage (Karim Shoair)
- Lightest fetcher first: static → `get`; JS-rendered → `fetch`; anti-bot →
  `stealthy_fetch`. Don't open a browser when HTTP suffices.
- Tell the AI *which* tool to use explicitly (saves tokens, avoids wrong guesses).
- `adaptive=True` (auto-relocates elements after a redesign) is OFF by default.
