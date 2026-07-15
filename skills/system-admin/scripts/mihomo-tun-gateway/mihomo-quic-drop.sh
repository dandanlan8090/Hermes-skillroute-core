#!/bin/sh
# 注入 QUIC(UDP/443) 拦截：强制局域网客户端经 TUN 时回落 TCP 以启用 SNI 嗅探
# 仅在 mihomo TUN 已建立后由 mihomo.service ExecStartPost 调用
# 网卡名 enp4s0 需替换为实际内网网卡（ip -br link 查）
set -e

for i in $(seq 1 10); do
  ip link show MihomoTun >/dev/null 2>&1 && break
  sleep 0.5
done

if nft list ruleset 2>/dev/null | grep -q 'iifname "enp4s0" oifname "MihomoTun" udp dport 443 drop'; then
  exit 0
fi

HANDLE=$(nft -a list chain ip filter FORWARD 2>/dev/null | grep 'iifname "enp4s0" oifname "MihomoTun" counter' | head -1 | grep -oE 'handle [0-9]+' | awk '{print $2}')
if [ -n "$HANDLE" ]; then
  nft insert rule ip filter FORWARD position "$HANDLE" iifname "enp4s0" oifname "MihomoTun" udp dport 443 drop
fi
