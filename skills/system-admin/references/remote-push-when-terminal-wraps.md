# Push files/keys to a host when the terminal wraps long pastes

## Trigger
The user's terminal auto-wraps long pasted lines and inserts a REAL newline,
breaking commands like `echo 'AAAA...long key...' >> ~/.ssh/authorized_keys`
(shell reports `syntax error` / `Permission denied` because the line was split).
This is a recurring user-environment trait, not a one-off.

## Fix: serve from a reachable host, pull with a SHORT curl
On the SOURCE host (one the target can reach over LAN):
    mkdir -p /tmp/keyserve && cp <file-to-serve> /tmp/keyserve/k
    cd /tmp/keyserve && python3 -m http.server 8088 --bind <ip> &

On the TARGET host (single short line, no wrap risk):
    mkdir -p ~/.ssh && chmod 700 ~/.ssh
    curl -fsS <SRC_IP>:8088/k >> ~/.ssh/authorized_keys
    chmod 600 ~/.ssh/authorized_keys

Cleanup on source: `pkill -f "http.server 8088"`; verify `ss -tulnp | grep 8088`
is empty. Keep the served content trivial (a pubkey / small config) — never
expose secrets on a LAN HTTP server longer than needed.

## Cross-arch binary note
Do NOT copy a binary built for one arch to another host. Example from the CM4
deploy: the deb host ran amd64 mihomo; CM4 is aarch64/ARM64 and the amd64
binary will not execute there. Always `uname -m` on the target first, then
fetch the matching release asset (e.g. `mihomo-linux-arm64-*.deb` for aarch64,
`mihomo-linux-amd64-*.deb` for x86_64).
