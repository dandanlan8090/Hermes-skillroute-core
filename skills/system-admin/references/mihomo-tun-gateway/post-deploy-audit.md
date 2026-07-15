# Mihomo 旁路由网关 - 部署后审计检查清单

在完成部署并按验证清单通过后，运行此审计捕获易忽略的回环/冗余问题。

## 1. 代理节点回环检测

```bash
# 获取节点 IP
NODE_IP=$(grep '^  server:' /etc/mihomo/config.yaml | awk '{print $2}')

# 检查路由是否被 auto-route 捕获
ip route get "$NODE_IP"
# 危险信号：via <ip> dev MihomoTun table 2022

# 检查连接堆积（回环的直接证据）
ss -tnp dst "$NODE_IP" | tail -n +2 | awk '{print $1}' | sort | uniq -c
# 危险信号：大量 CLOSE-WAIT（>5）

# 日志中的回环证据
sudo journalctl -u mihomo --no-pager -n 100 | grep "$NODE_IP" | grep 'match Match'
# 出现 198.18.0.x -> NODE_IP 的行说明回环发生
```

**修复**：在 rules: 后插入 `IP-CIDR,<NODE_IP>/32,DIRECT,no-resolve`

## 2. DNS 优化检查

```bash
# 确认 nameserver 不含境外 DNS
sudo grep -A5 'nameserver:' /etc/mihomo/config.yaml
# 期望：仅 <ip> / <ip>（纯国内）
# 不应有：tls://<ip> / tls://<ip>

# 确认 fallback 有境外 DNS
sudo grep -A5 'fallback:' /etc/mihomo/config.yaml
# 期望：tls://<ip> / tls://<ip> / https://dns.google/dns-query
```

## 3. 规则去重检查

```bash
# FORWARD 链 MihomoTun ACCEPT 数量
sudo iptables -S FORWARD | grep -cE '^-A FORWARD -i (enp4s0 -o MihomoTun|MihomoTun -o enp4s0) -j ACCEPT'
# 期望：2（enp4s0→MihomoTun × 1, MihomoTun→enp4s0 × 1）

# MASQUERADE 数量
sudo iptables -t nat -S POSTROUTING | grep -c '^-A POSTROUTING -o enp4s0 -j MASQUERADE'
# 期望：1
```

## 4. sysctl 持久化检查

```bash
grep -Rl 'net.ipv4.ip_forward' /etc/sysctl.d/ /etc/sysctl.conf 2>/dev/null
# 期望：至少返回一个文件
sysctl net.ipv4.ip_forward
# 期望：net.ipv4.ip_forward = 1
```

## 5. 完整功能快照

```bash
{
  echo "=== 服务 ==="
  systemctl is-active mihomo
  echo "=== SOCKS5 出口 ==="
  curl -sS --max-time 15 --proxy socks5h://<ip> -o /dev/null -w 'google=%{http_code} %{time_total}s\n' https://www.google.com
  echo "=== 国内直连 ==="
  curl -sS --max-time 8 -o /dev/null -w 'baidu=%{http_code} %{time_total}s\n' https://www.baidu.com
  echo "=== DNS fake-ip ==="
  dig @<ip> +short www.google.com 2>/dev/null
  echo "=== API 认证 ==="
  curl -sS -o /dev/null -w 'no-auth=%{http_code} ' http://<ip>/version
  SECRET=$(python3 -c 'import re; s=open("/etc/mihomo/config.yaml").read(); m=re.search(r"^secret:\s*[\"'"'"']?([^\"'"'"'\n#]+)", s, re.M); print(m.group(1).strip() if m else "")')
  curl -sS -H "Authorization: Bearer $SECRET" -o /dev/null -w 'auth=%{http_code}\n' http://<ip>/version
  echo "=== QUIC 拦截 ==="
  nft list chain ip filter FORWARD 2>/dev/null | grep -q 'udp dport 443 drop' && echo "active" || echo "missing"
}
```
