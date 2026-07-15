# Identify the True Origin of an Installed Binary / Package

Proven method used to answer "which GitHub repo is this `mihomo` on the host from?"
when a raw GitHub API/URL lookup was ambiguous (the URL returned an unrelated project).

## When to use
- User asks "which repo / who maintains this installed tool?"
- You need to prove a binary's identity (vs. a same-named but different project on GitHub).
- `which <bin>` resolves but you can't tell if it's upstream A or fork B.

## Procedure (run on the host, NOT a web lookup)
```bash
# 1) Locate the binary + glob common install paths
which mihomo; ls -l /usr/bin/mihomo /usr/local/bin/mihomo 2>/dev/null

# 2) Self-reported identity (name/version/build tags reveal upstream)
mihomo -v          # e.g. "Mihomo Meta v1.19.27 linux amd64 with go1.26.4 ... Use tags: with_gvisor"

# 3) Package metadata — THE authoritative source
dpkg -s mihomo     # Package / Maintainer(Vendor) / Description / Homepage / Bug URL
dpkg -L mihomo | head -40

# 4) Where it was installed from
apt-cache policy mihomo

# 5) Embedded Go module paths reveal the real vendor org (best for renamed repos)
strings /usr/bin/mihomo | grep -iE 'github.com/<org>' | sort -u | head

# 6) How it actually runs (gateway? config path? TUN?)
ps aux | grep -i mihomo | grep -v grep
systemctl list-units --all | grep -i mihomo
```

## Key lesson
**Trust host-side package metadata + embedded binary strings over a fresh GitHub URL lookup.**
A repo URL in package metadata (e.g. `Bug: github.com/MetaCubeX/mihomo`) can later point
to a DIFFERENT project if the upstream renamed/redirected and the old name was reused.
Verify identity from the binary itself; only use the web URL as a secondary hint.

## Clash/Mihomo ecosystem — name disambiguation (observed 2026-07-12)
Easily confused; verify each by type, not by name:
- **mihomo** (Clash.Meta core engine): proxy *core*, Go binary named `mihomo`, runs as TUN gateway.
  Vendor MetaCubeX, homepage wiki.metacubex.one. This is what the host runs.
- **MetaCubeX/ClashX.Meta**: macOS *GUI client* (ClashX fork). NOT the core. ~6.1k stars.
- **clash-verge-rev/clash-verge-rev**: cross-platform *desktop GUI client* (Tauri). ~130k stars.
  Revival fork of archived zzzgydi/clash-verge. Consumes nodes; does not produce them.
- **shadowsocks-libev**: server-side *node producer*, C, maintenance-only
  (dev moved to shadowsocks-rust). Not a client.
- GOTCHA: at observation time, the exact URL `github.com/MetaCubeX/mihomo` returned (via API)
  a Python "Honkai: Star Rail" data library — unrelated to the proxy core. Treat as a
  renamed/redirected repo; never assume the URL still means the same project.

## Workflow correction captured from this session
User required live verification before answering ("去github详细查看完再回答").
When a question is about a specific repo/project identity, fetch real data (API or host-side)
and cite it — do not answer from memory of what a repo "used to be".
