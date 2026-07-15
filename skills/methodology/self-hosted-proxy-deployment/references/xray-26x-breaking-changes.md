# Xray 26.x 破坏性变更与 Reality 失败诊断（实测 26.3.27 / Debian 12）

## 1. 破坏性变更（直接卡启动）

| 旧字段 | 新写法 | 报错 |
|--------|--------|------|
| `tlsSettings.allowInsecure: true` | `tlsSettings.pinnedPeerCertSha256: "<sha256无冒号>"` | `The feature "allowInsecure" has been removed and migrated to "pinnedPeerCertSha256"` |
| VLESS client users 无 encryption | 每个 user 必须 `"encryption": "none"` | `VLESS users: please add/set "encryption":"none" for every user` |
| Trojan 协议 | 仍可用但 deprecation warning | `The feature Trojan (with no Flow, etc.) is deprecated ... migrate to VLESS` |

证书指纹获取：`openssl x509 -in server.crt -noout -fingerprint -sha256 | sed 's/.*=//;s/://g'`

## 2. Reality 握手失败诊断树

错误信号分类：

### A. 服务端日志 `processed invalid connection from <ip>:<port>: incorrect server hello or handshake incomplete`
- 含义：包**已到达**服务端，但 Reality 认证不通过。
- 排查：
  1. 服务端 `privateKey` 与客户端 `publicKey` 是否**同源**（同一次 `xray x25519`）。重生成一端漏了另一端 = 必失败。
  2. `shortId` 是否匹配（服务端 shortIds 列表须含客户端 shortId；空 `""` 合法）。
  3. `flow` 服务端 client 与客户端是否都为 `xtls-rprx-vision`。
  4. `uuid` 是否一致。

### B. 客户端日志 `received real certificate (potential MITM or redirection)`
- 含义：**不是真 MITM**。是 Reality 验证失败后，服务端按 design 把连接 fallback 到 `dest`（真站点），客户端因此看到真证书。
- 同 A 根因（认证不匹配）。注意：在服务器本地用**外部 IP** 连也会拿到真证书（NAT 回环被重定向），必须用 `<ip>` 测试才能隔离。

### C. `i/o timeout` 与 auth 失败交替
- 部分包到不了服务端（防火墙/安全组未放端口），部分到了但握手失败。先用 §3 本地同版本测试隔离。

## 3. 隔离测试（定位是服务端/客户端/网络）

在**服务器本地**用同版本 xray 跑 client 连 `<ip>:<port>`：
```bash
cat > /tmp/cl.json <<JSON
{"log":{"loglevel":"warning"},
 "inbounds":[{"listen":"<ip>","port":10091,"protocol":"socks"}],
 "outbounds":[{"protocol":"trojan","settings":{"servers":[{"address":"<ip>","port":8443,"password":"<PASS>"}]},
 "streamSettings":{"network":"tcp","security":"tls","tlsSettings":{"serverName":"<IP>","pinnedPeerCertSha256":"<SHA>"}}}]}
JSON
nohup xray run -c /tmp/cl.json >/tmp/cl.log 2>&1 &
sleep 3
curl -s --max-time 15 -x socks5://<ip> https://api.ipify.org && echo OK || echo FAIL
```
- <ip> 能通 → 服务端 OK，问题在外部客户端/网络。
- <ip> 也失败 → 服务端配置/版本问题（见 Reality 坑：Xray 26.3.27 在本环境 Reality 始终 fallback，改 Trojan 解决）。

## 4. 环境结论（2026-07-12 实测，带时效注记）

> **`verified_on`: 2026-07-12 | `环境指纹`: Xray 26.3.27 + Debian 12 (bookworm) + 外部 NAT IP 云主机 + mihomo 1.19.27 客户端**
> **结论性质**: 条件性（非普适）。仅在此环境组合下成立。
> **失效/重验触发条件**:
> 1. Xray 升级到新主版本（26.x → 27+ 等）后，Reality 实现可能修复/变更 → 重测。
> 2. 换云厂商、换系统镜像（非 Debian12）、或服务器拿到真实域名并绑定后 → 重测。
> 3. 改用原生 Reality 客户端（非 mihomo，如官方 xray / sing-box）时 → 重测。
> 上述任一条件变化，须用 §3 隔离测试重新评估 Reality 可用性，不得默认沿用本结论。

- 在上述文本「环境指纹」组合下，Xray 26.3.27 的 **VLESS+Reality 握手失败**（同版本 client 连 `<ip>` 也 `received real certificate`，排除网络/客户端因素）。
- 改用 **Trojan+自签证书** 立即成功。建议新部署默认 Trojan，除非确知目标环境 Reality 版本兼容（且已用 §3 验证通过）。
- 证书权限：xray 以 nobody 运行，`server.key` 必须 `chmod 644`，否则 `permission denied` 启动失败。
