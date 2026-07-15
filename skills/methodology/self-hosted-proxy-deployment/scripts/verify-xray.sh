#!/usr/bin/env bash
# 在 Xray 服务端本机运行：检查进程/监听/日志，隔离 Reality/Trojan 问题。
set -e
echo "=== Xray 进程 ==="
pgrep -a xray || echo "NO XRAY PROCESS"
echo "=== 监听端口 ==="
ss -tlnp 2>/dev/null | grep -E ":(443|8443)" || echo "no 443/8443 listening"
echo "=== 证书权限(必须为 644, xray 以 nobody 跑) ==="
ls -l /usr/local/etc/xray/server.key 2>/dev/null || echo "(无自签 key，可能用 Reality)"
echo "=== 最近错误日志 ==="
tail -8 /var/log/xray/error.log 2>/dev/null
echo "=== 本机出网是否被 MITM(应拿到真站证书) ==="
echo | timeout 8 openssl s_client -connect microsoft.com:443 -servername microsoft.com 2>/dev/null | openssl x509 -noout -subject 2>/dev/null || echo "证书解析失败(可能无外网)"
echo "=== 本机 IP 是否为外部 NAT IP(影响 Reality 回环测试) ==="
ip -4 addr show 2>/dev/null | grep -oE "inet [0-9.]+" | awk '{print $2}'
echo "提示: 用 <ip>:<port> 做同版本 client 自测，勿用外部 IP(会被 NAT 回环重定向)"
