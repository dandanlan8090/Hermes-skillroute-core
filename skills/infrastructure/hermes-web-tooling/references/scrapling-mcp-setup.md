# Scrapling MCP — install & verify recipe (verified 2026-07-14)

## What it solves
Scrapling (D4Vinci/Scrapling, BSD-3, 69k⭐) is a Python scraping framework
with a **built-in MCP server**. Its `get`/`fetch`/`stealthy_fetch` tools extract
targeted content (via CSS selector) *before* handing it to the AI — reducing
tokens vs extractors that dump the whole page. Zero API key, ships a Docker
image with browsers. Strong candidate to fill Hermes's `web_extract` gap AND
plug into the MCP layer.

## Install (into Hermes venv — NOT system python)
Find Hermes's venv: `hermes --version` → "Install directory: <DIR>";
venv = `<DIR>/venv/bin/python`.
```bash
V=<DIR>/venv/bin/python
$V -m pip install "scrapling[full,fetchers,playwright,mcp,ai]"
$V -m pip install curl_cffi        # belt-and-suspenders (see PITFALL)
```

> PITFALL — `pip install "scrapling[full]"` alone leaves
> `ModuleNotFoundError: No module named 'curl_cffi'`. Fetcher/HTTP mode needs
> `curl_cffi`, which lives under the **separate `fetchers` extra**, not `[full]`.
> Always include `fetchers` in the extras list, or install curl_cffi explicitly.

## Browser (DynamicFetcher / StealthyFetcher need Chromium)
```bash
# default GitHub host is slow/blocked behind GFW — use the npmmirror mirror
PLAYWRIGHT_DOWNLOAD_HOST=https://cdn.npmmirror.com/binaries/playwright \
  <DIR>/venv/bin/python -m playwright install chromium
```
- Fetches `chromium-headless-shell` + `ffmpeg` into `~/.cache/ms-playwright/`.
- Author's recommended `scrapling install` runs `playwright install-deps
  chromium` which needs **root** and fails in a user venv — IGNORE it. The
  browser binary alone is sufficient (verified: DynamicFetcher launched headless
  Chromium OK without the system deps step).

## Verify (real network, through any egress)
```python
from scrapling.fetchers import Fetcher, DynamicFetcher
print(Fetcher.get('https://quotes.toscrape.com/').css('.quote .text::text').getall()[:1])
print(DynamicFetcher.fetch('https://quotes.toscrape.com/', headless=True).css('.quote .text::text').getall()[:1])
# closes the web_extract gap — GitHub README body in one call:
t = ' '.join(s.strip() for s in Fetcher.get('https://github.com/D4Vinci/Scrapling').css('article.markdown-body ::text').getall() if s.strip())
print(len(t), 'chars extracted')   # -> ~18k chars
```

## MCP server (the payoff)
Entry point is the **CLI subcommand**, NOT `python -m scrapling mcp`
(that errors: "No module named scrapling.__main__"). Use the executable:
```bash
<DIR>/venv/bin/scrapling mcp --help                                # stdio transport
<DIR>/venv/bin/scrapling mcp --http --host <ip> --port 8000   # streamable-HTTP
```
Tools: `get`, `bulk_get`, `fetch`, `bulk_fetch`, `stealthy_fetch`,
`bulk_stealthy_fetch`, `screenshot`, `open_session`, `close_session`,
`list_sessions`.
Custom browser: `--executable-path /path/to/chromium` or `SCRAPLING_EXECUTABLE_PATH`.
To plug into Hermes's MCP layer: add an entry under `mcp_servers` in
`~/.hermes/config.yaml` with `command`, `args` (YAML list), `env` (YAML dict).
Use `hermes config set mcp_servers.<name>.command <path>` for the command,
then fix args/env with python (config set stores them as strings — see
hermes-mcp-server-setup skill for the full pattern). Verify with
`hermes mcp test <name>`.

## Fetcher choice (author's guidance)
- **Fetcher** (HTTP, fastest 🐇×5) → static pages HTTP can fetch. No browser.
- **DynamicFetcher** (Chromium) → JS-rendered pages / small automation.
- **StealthyFetcher** (Chromium, max stealth ⭐×5) → Cloudflare
  Turnstile/Interstitial / anti-bot.
Author's rule of thumb: tell the AI *which* tool to use explicitly to save
tokens/time. `adaptive=True` (auto-relocates elements after a site redesign)
is OFF by default — enable it when you want resilience to markup changes.
