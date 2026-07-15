---
name: system-admin
description: 'System administration tasks: service installation, initialization, verification,
  and health checks for Linux servers (Ubuntu/Debian/Armbian). Covers databases (MariaDB/PostgreSQL/Redis),
  container runtimes (Docker), and development toolchains (Node.js, Git).'
version: 1.0.0
author: Hermes Agent
license: MIT
platforms:
- linux
- ubuntu
- debian
- armbian
metadata:
  hermes:
    tags:
      trigger:
      - 系统管理
      - 服务器
      - 服务安装
      - 部署
      - 配置环境
      - 运维
      - 启动不了
      - 服务启动
      - 数据库
      - postgresql
      - nginx
      - docker
      - 初始化
      disable:
      - cli_only
      - read_only
      - 部署服务
    related_skills:
    - hermes-bootstrap
    - plan
---
# System Administration

Class-level guidance for installing, initializing, and verifying system services on Ubuntu/Debian/Armbian servers. Use when user requests dependency installation, service setup, or post-install hardening.

## When to Use

- User asks to install and initialize services (databases, Docker, Git, etc.)
- Fresh server setup or migration to new machine
- Post-install verification of service health
- System dependency audit and gap analysis

## Core Principles

1. **Install → Initialize → Verify**: Never skip initialization or verification steps. Installation alone is incomplete.
2. **Actual testing over version checks**: Run `redis-cli ping`, `docker run hello-world`, database CRUD ops — not just `--version`.
3. **systemctl enable for persistence**: All services must be set to auto-start on boot.
4. **Hermes as orchestrator**: Hermes plans and decomposes tasks, delegates execution to OpenCode via `--attach`, then summarizes results.

## Standard Procedure

### Phase 1: Survey Current State

```bash
# Check what's installed
dpkg -l | grep -E '<package-name>'
apt list --installed 2>/dev/null | grep '<package>'
systemctl is-active <service>
```

### Phase 2: Install Missing Components

**Node.js LTS (via NodeSource)**
```bash
curl -fsSL https://deb.nodesource.com/setup_lts.x | sudo -E bash -
sudo apt-get install -y nodejs
node --version && npm --version
npm install -g npm-check-updates  # Test global install
```

**Docker + Compose**
```bash
sudo apt-get install -y docker.io docker-compose-v2
sudo usermod -aG docker lan
sudo systemctl enable --now docker
```

**Redis**
```bash
sudo apt-get install -y redis-server
sudo systemctl enable --now redis-server
redis-cli ping  # Should return PONG
```

**MariaDB Server**
```bash
sudo apt-get install -y mariadb-server
sudo systemctl enable --now mariadb
# Initialize: create test DB + user
sudo mysql -e "CREATE DATABASE IF NOT EXISTS testdb; CREATE USER IF NOT EXISTS 'testuser'@'localhost' IDENTIFIED BY 'testpass123'; GRANT ALL PRIVILEGES ON testdb.* TO 'testuser'@'localhost'; FLUSH PRIVILEGES;"
```

**PostgreSQL**
```bash
sudo apt-get install -y postgresql
sudo systemctl enable --now postgresql
# Initialize: create role + database for lan user
sudo -u postgres psql -c "CREATE ROLE lan WITH LOGIN CREATEDB;"
sudo -u postgres psql -c "CREATE DATABASE lan OWNER lan;"
```

**Git Configuration**
```bash
git config --global user.name "<name>"
git config --global user.email "<email>"
git config --global init.defaultBranch main
git config --global --list
```

### Phase 3: Verification (Mandatory)

Run actual functional tests, not just version checks:

| Service | Verification Command | Expected Output |
|---------|---------------------|-----------------|
| Node.js | `node -e "console.log(process.version)"` | v2x.x.x |
| npm | `npm --version` | 10.x or 11.x |
| Docker | `sudo docker run --rm hello-world` | "Hello from Docker!" |
| Redis | `redis-cli ping` | `PONG` |
| Redis | `redis-cli SET key 'OK' && redis-cli GET key` | `OK` then `OK` |
| MariaDB | `mysql -u testuser -ppass testdb -e "SELECT 1"` | Result set |
| PostgreSQL | `psql -U lan -d lan -c "SELECT 1"` | Result set |
| Git | `git config --global user.name` | Configured name |

**CRITICAL**: If any verification fails, debug immediately. Do not declare "complete" until all tests pass.

### Phase 4: Documentation

Generate a verification report:

```markdown
# Service Initialization Verification Report

## Summary
| Service | Version | Status | Port | Verification Test |
|---------|---------|--------|------|-------------------|
| Redis | x.x.x | ✅ active | 6379 | PING→PONG |
| MariaDB | x.x.x | ✅ active | 3306 | CREATE/INSERT/SELECT |

## Service Status
```bash
systemctl is-active mariadb postgresql redis-server docker
```

## Listening Ports
```bash
ss -tuln | grep -E '3306|5432|6379'
```

## Conclusion
All services initialized and verified. Ready for production use.
```

## Hermes + OpenCode Collaboration Pattern

For complex multi-service initialization:

1. **Hermes writes plan**: `.hermes/plans/YYYY-MM-DD_HHMMSS-sysadmin-init.md`
2. **Hermes delegates to OpenCode**:
   ```bash
   opencode --attach http://<ip> run "<task description with exact commands>"
   ```
3. **OpenCode executes**: Runs commands, captures output, handles errors
4. **Hermes aggregates**: Reads OpenCode output, formats final report

Example delegation prompt:
```
Execute system optimization task: Install and initialize Node.js, Docker, Redis.

**Task 1: Node.js LTS**
curl -fsSL https://deb.nodesource.com/setup_lts.x | sudo -E bash -
sudo apt-get install -y nodejs
node --version && npm --version
npm install -g npm-check-updates  # Test global install

**Task 2: Docker**
sudo apt-get install -y docker.io docker-compose-v2
sudo usermod -aG docker lan
sudo systemctl enable --now docker
sudo docker run --rm hello-world

**Task 3: Redis**
sudo apt-get install -y redis-server
sudo systemctl enable --now redis-server
redis-cli ping

Save output to /tmp/install-log.md with [✅] or [❌] markers.
```

## Pitfalls

- **Docker permission denied**: User must be in `docker` group. Run `sudo usermod -aG docker <user>` then logout/login.
- **MariaDB root access denied**: Modern MariaDB uses `unix_socket` auth. Use `sudo mariadb` or create separate admin user.
- **PostgreSQL peer auth**: By default, psql uses peer auth. Use `sudo -u postgres psql` or configure pg_hba.conf for password auth.
- **Only clients installed**: Check if server packages are actually installed (`mariadb-server`, `postgresql`, not just `-client`).
- **Docker network timeout**: If `docker run hello-world` fails with "failed to resolve reference", check network/DNS. May need to configure Docker mirror.
- **sudo -E with apt**: NodeSource script may warn about `-E` being unsupported on apt. Safe to ignore, or use `sudo bash` instead.
- **Systemd unit not found**: Service may not be installed or named differently (e.g., `mariadb` vs `mysql`).
- **Port already in use**: Check `ss -tuln | grep <port>` before assuming service is down.

## Verification Before Completion

Iron Law: **Do not declare success without running tests.**

- Docker must actually pull and run `hello-world`
- Redis must respond to PING and survive SET/GET
- Databases must survive CREATE → INSERT → SELECT → DROP cycle
- Git config must show correct values via `--list`
- All services must show `active (running)` in `systemctl status`

## Common Service Ports

| Service | Port | Default Bind |
|---------|------|--------------|
| MariaDB | 3306 | <ip> |
| PostgreSQL | 5432 | <ip> |
| Redis | 6379 | <ip> (IPv4+IPv6) |
| Docker | - | Unix socket |
| OpenCode | 8901 | <ip> |

## Related Commands

- `systemctl enable --now <svc>`: Enable + start
- `systemctl is-active <svc>`: Check status (returns exit code)
- `ss -tuln | grep <port>`: Verify listening
- `journalctl -u <svc> -n 30`: Recent logs

## Rules

1. Always use `apt-get install -y` for non-interactive installs.
2. Always run `systemctl enable --now` for services.
3. Always verify with functional tests, not just `--version`.
4. Always generate a verification report for the user.
5. When delegating to OpenCode, provide exact commands in the prompt.
6. When verification fails, debug immediately — do not move to next task.

## References

- NodeSource setup: https://github.com/nodesource/distributions
- Docker installation (Ubuntu): https://docs.docker.com/engine/install/ubuntu/
- MariaDB secure installation: `mysql_secure_installation`
- PostgreSQL role management: `man psql`

---

---

## Appendix A. Broken dpkg / apt Recovery

Re-homed from the `linux-dpkg-repair` skill. Covers Debian-family (Ubuntu/Debian/Armbian) systems where `apt-get` / `dpkg --configure` cannot make progress.

**Triggers**: `apt-get install -f` loops on a postinst hook (install-info / man-db / initramfs-tools); `dpkg -s <pkg>` errors `parsing file '/var/lib/dpkg/status' near line N` or `duplicate value for 'Package' field`; `dpkg -l | grep '^.[ih][FU]'` shows iF / iU / hU packages; package reports installed but files missing (common with renamed upstream packages).

**Not for**: pure mirror/sources.list issues, apt-key/network-proxy problems (those are not dpkg state corruption).

**Decision tree (30s fault map)**:
```bash
dpkg -l | awk '/^.[ih][FU]/ {print $1, $2, $3}'
echo "半配置包数: $(dpkg -l | grep -cE '^.[ih][FU]')"
```

**Sanitizer**: `scripts/linux-dpkg-repair/status-file-sanitizer.py` rewrites `/var/lib/dpkg/status` to drop duplicate Package sections and repair unparseable status lines. **Always back up `/var/lib/dpkg/status` before running it.** See `references/linux-dpkg-repair/install-info-update-info-dir-bug.md` for the specific install-info / update-info-dir postinst loop fix.

**Rules**: never touch user data — only dpkg metadata + package-manager caches. After repair, `apt-get install -f` should return `0 upgraded, 0 newly installed`.

## Appendix B. Mihomo TUN Transparent-Gateway

Re-homed from the `mihomo-tun-gateway` skill. Deploy a Mihomo (Clash-compatible) TUN-mode gateway on Debian/Ubuntu/Armbian (**x86_64 AND ARM64/aarch64**). Two topologies:
- **LAN side-router**: other LAN hosts route through this host as gateway (set their gateway/DNS to this host).
- **Single-host transparent proxy**: only this machine's own traffic goes through TUN (no other hosts route via it). Config is identical — only the external routing differs. The bundle in `references/mihomo-arm64-singlehost-deploy.md` covers the single-host case and works for side-router too.

**Use when**: you want system-wide proxy without per-app config; split so domestic IPs go DIRECT and foreign traffic goes via proxy nodes (GEOSITE/geoip CN → DIRECT, MATCH → Proxy).

**Key pieces**:
- Install + systemd unit for `mihomo` in TUN mode.
- `references/mihomo-arm64-singlehost-deploy.md` — known-good ARM64 single-host bundle (desensitized config + systemd unit + install script + SSH-pubkey + health-check).
- `references/mihomo-tun-gateway/post-deploy-audit.md` — post-deploy connectivity/leak audit checklist.
- `scripts/mihomo-tun-gateway/mihomo-quic-drop.sh` — drop QUIC (force TCP so proxy rules apply).

**Cross-arch (ARM64 / CM4 / Orange Pi / RPi)**:
- Never reuse an amd64 binary on an ARM host. Check `uname -m` on target (`aarch64` = ARM64).
- Fetch the matching release asset: `mihomo-linux-arm64-<ver>.deb` (or `.gz` raw binary). Latest tag via `curl -s https://api.github.com/repos/MetaCubeX/mihomo/releases/latest | grep tag_name`.
- The `.deb` installs `/usr/bin/mihomo`; the custom unit adds `CapabilityBoundingSet=CAP_NET_ADMIN CAP_NET_BIND_SERVICE CAP_NET_RAW` (TUN device + binding ports 53/9090). Run `mihomo -t -d /etc/mihomo` to validate config before `enable`.

**SSH pubkey distribution pitfall (long keys wrap in narrow terminals)**:
- An 82-char ed25519 key wider than the terminal wraps to a new line → `>>` and key split → `syntax error` / `chmod: missing operand` / `Permission denied`. Copy-paste of long keys is unsafe.
- Fix: serve from source host (`cd /tmp/ks && cp ~/.ssh/id_ed25519.pub k && python3 -m http.server 8088`), then on target `mkdir -p ~/.ssh && chmod 700 ~/.ssh && curl -fsS <SRC_IP>:8088/k >> ~/.ssh/authorized_keys && chmod 600 ~/.ssh/authorized_keys`. The curl line stays <60 chars — no wrapping.
- **Do NOT `sudo -i` before appending a login user's `authorized_keys`** — `$HOME` switches to `/root`, so the key lands in `/root/.ssh/` not `/home/<user>/.ssh/`. Append as the login user; `sudo` only the `mkdir`/`chmod` if perms require, keeping the redirect under the user's own home.

**SBC multi-NIC pitfall**:
- SBCs like CM4 often expose wireless + wired on the same subnet. A wireless IP flaps and is the wrong always-on gateway target. Confirm the wired IP with the user before deploying if the host shows >1 interface.

**Rules**: requires `iptables`/nftables + TUN kernel module; lock down to the intended LAN subnet; always run the post-deploy audit to confirm no DNS/leak.

## Appendix C. Identifying an Installed Binary's True Origin

When asked "which repo is this tool from?" — e.g. resolving the `mihomo` naming confusion
(`MetaCubeX/mihomo` URL returned an unrelated Python game library; Clash.Meta core vs
ClashX.Meta macOS GUI vs clash-verge-rev desktop GUI). Full procedure + ecosystem
disambiguation in `references/identify-package-origin.md`.

**Core rule**: trust host-side `dpkg -s` metadata + `strings <bin> | grep github.com/<org>`
over a fresh GitHub URL lookup. A repo URL in package metadata can later point to a
*different* project if upstream renamed/redirected and the old name was reused. Verify
identity from the binary itself; treat web URLs as secondary hints only.

**Workflow rule (user-mandated 2026-07-12)**: for any "which repo / what is this project?"
question, fetch real data (GitHub API or host-side) and cite it — never answer from memory
of what a repo "used to be". User explicitly required live verification before answering.