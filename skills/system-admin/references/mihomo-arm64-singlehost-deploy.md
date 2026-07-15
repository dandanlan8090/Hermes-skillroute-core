# Mihomo ARM64 单主机透明代理部署包（CM4 / aarch64 / Debian·Ubuntu）

已知可用组合：Clash.Meta (mihomo) v1.19.28 arm64 deb + systemd TUN 网关。
适用：CM4 / Orange Pi / RPi 等 ARM SBC，单主机自用（也可当旁路由，配置一致）。

> 凭据均为占位符。真实 Trojan/SS password、sni、server 从运行环境取，勿入库。

## 0. 架构核对（先跑）
```
uname -m            # aarch64 => ARM64，必须下 arm64 资产
# 绝不能把 amd64 机器上的 /usr/bin/mihomo 拷过去
```

## 1. 取 ARM64 二进制
```
# 最新 tag：
curl -s https://api.github.com/repos/MetaCubeX/mihomo/releases/latest | grep tag_name
# 资产名：mihomo-linux-arm64-<ver>.deb
wget https://github.com/MetaCubeX/mihomo/releases/download/v1.19.28/mihomo-linux-arm64-v1.19.28.deb
```

## 2. config.yaml（单主机 TUN 透明代理）
```yaml
# ==================================================
# Mihomo (Clash.Meta) — 单主机透明代理 (ARM64)
# ==================================================
mixed-port: 7898
redir-port: 7899
allow-lan: true
bind-address: "*"
mode: rule
log-level: info
ipv6: false
external-controller: <ip>
secret: "REPLACE_WITH_SECRET"

tun:
  enable: true
  stack: system
  device: MihomoTun
  auto-route: true
  auto-detect-interface: true
  dns-hijack:
    - any:53

dns:
  enable: true
  listen: <ip>
  enhanced-mode: fake-ip
  fake-ip-range: <ip>/16
  fake-ip-filter:
    - "*.lan"
  nameserver:
    - <ip>
    - <ip>
  fallback:
    - tls://<ip>
    - tls://<ip>
    - https://dns.google/dns-query
  fallback-filter:
    geoip: true
    geoip-code: CN
    ipcidr:
      - <ip>/4

sniffer:
  enable: true
  sniff:
    TLS:
      ports: [443, 8443]
    HTTP:
      ports: [80, 8080-8880]
  force-dns-mapping: true
  parse-pure-ip: true

geodata-mode: true
geodata:
  geosite: /etc/mihomo/geosite.dat
  geoip: /etc/mihomo/geoip.dat
  mmdb: /etc/mihomo/country.mmdb

proxies:
  - name: "trojan-tls"
    type: trojan
    server: REPLACE_SERVER
    port: 8443
    password: "REPLACE_PASSWORD"
    network: tcp
    udp: true
    sni: REPLACE_SERVER
    skip-cert-verify: true
  - name: "ss"
    type: ss
    server: REPLACE_SERVER
    port: 443
    cipher: chacha20-ietf-poly1305
    password: "REPLACE_PASSWORD"
    udp: true

proxy-groups:
  - name: "Proxy"
    type: select
    proxies:
      - "trojan-tls"
      - "ss"
      - DIRECT
  - name: "自动选择"
    type: url-test
    proxies:
      - "trojan-tls"
      - "ss"
    url: "https://www.gstatic.com/generate_204"
    interval: 300
    tolerance: 50

rules:
  - IP-CIDR,REPLACE_PROXY_HOST/32,DIRECT,no-resolve
  - IP-CIDR,<ip>/16,DIRECT,no-resolve
  - IP-CIDR,<ip>/8,DIRECT,no-resolve
  - IP-CIDR,<ip>/12,DIRECT,no-resolve
  - IP-CIDR,<ip>/8,DIRECT,no-resolve
  - IP-CIDR,<ip>/10,DIRECT,no-resolve
  - IP-CIDR,<ip>/4,DIRECT,no-resolve
  - IP-CIDR,<ip>/4,DIRECT,no-resolve
  - GEOSITE,private,DIRECT
  - GEOSITE,cn,DIRECT
  - GEOIP,cn,DIRECT
  - MATCH,Proxy
```

## 3. mihomo.service（放 /etc/systemd/system/mihomo.service）
```ini
[Unit]
Description=Mihomo Service (Clash.Meta) - TUN gateway
After=network.target nss-lookup.target

[Service]
Type=simple
User=root
LimitNPROC=512
LimitNOFILE=1000000
CapabilityBoundingSet=CAP_NET_ADMIN CAP_NET_BIND_SERVICE CAP_NET_RAW
AmbientCapabilities=CAP_NET_ADMIN CAP_NET_BIND_SERVICE CAP_NET_RAW
Restart=always
RestartSec=5
ExecStartPre=/usr/bin/mihomo -t -d /etc/mihomo
ExecStart=/usr/bin/mihomo -d /etc/mihomo
ExecReload=/bin/kill -HUP $MAINPID

[Install]
WantedBy=multi-user.target
```

## 4. install.sh（目标机 `sudo bash install.sh`，同目录需 config.yaml / mihomo.service / geo 数据 / deb）
```bash
#!/usr/bin/env bash
set -euo pipefail
SRC="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DEB="mihomo-linux-arm64-v1.19.28.deb"
echo "==> [1/6] 安装 mihomo"
if command -v mihomo >/dev/null 2>&1; then echo "    已存在: $(mihomo -v 2>/dev/null|head -1)"
else [ -f "$SRC/$DEB" ] || curl -fL --max-time 150 -o "$SRC/$DEB" "https://github.com/MetaCubeX/mihomo/releases/download/v1.19.28/$DEB"
  sudo dpkg -i "$SRC/$DEB" || sudo apt-get install -f -y; fi
echo "==> [2/6] 部署配置/geo"
sudo mkdir -p /etc/mihomo
sudo install -m 644 "$SRC/config.yaml" /etc/mihomo/config.yaml
sudo install -m 644 "$SRC"/{geosite.dat,geoip.dat,country.mmdb} /etc/mihomo/ 2>/dev/null || true
echo "==> [3/6] 语法校验"; sudo /usr/bin/mihomo -t -d /etc/mihomo
echo "==> [4/6] systemd"; sudo install -m 644 "$SRC/mihomo.service" /etc/systemd/system/mihomo.service; sudo systemctl daemon-reload
echo "==> [5/6] 启用+启动"; sudo systemctl enable --now mihomo; sleep 2
echo "==> [6/6] 健康检查"
sudo systemctl is-active mihomo && echo "  service active" || { sudo journalctl -u mihomo -n 30 --no-pager; exit 1; }
ss -tuln | grep -E ':7898|:9090' && echo "  ports OK" || echo "  WARN ports"
ip link show MihomoTun >/dev/null 2>&1 && echo "  TUN up" || echo "  WARN TUN"
```

## 5. geo 数据
```
# 从已有主机拷：geosite.dat / geoip.dat / country.mmdb -> /etc/mihomo/
# 或首次启动让 mihomo 自动下载（需先能出境）
```

## 6. SSH 公钥分发（长密钥防终端折行）
```
# 源机：cd /tmp/ks && cp ~/.ssh/id_ed25519.pub k && python3 -m http.server 8088
# 目标机（以登录用户身份，别 sudo -i）：
mkdir -p ~/.ssh && chmod 700 ~/.ssh && \
curl -fsS <SRC_IP>:8088/k >> ~/.ssh/authorized_keys && chmod 600 ~/.ssh/authorized_keys
```

## 7. 健康检查
```
systemctl is-active mihomo
ss -tuln | grep -E ':7898|:9090'   # mixed-port / external-controller
ss -tuln | grep ':53 '             # dns
ip link show MihomoTun             # TUN 设备
curl -x http://<ip> https://www.google.com   # 需节点可达
```

## 8. SBC 多网卡
CM4 类双网卡主机确认用**有线 IP** 管理，无线 IP 易飘。
