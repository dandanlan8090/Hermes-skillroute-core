---
name: self-hosted-proxy-deployment
description: 自建反审查代理节点（Xray/Trojan/VLESS+Reality/Shadowsocks）与本地 Clash.Meta(mihomo)
  客户端的分流配置、排错与端到端验证。涵盖协议选型、Xray 26.x 破坏性变更、Reality 握手失败诊断、密钥对管理、mihomo 节点格式。
trigger_tags:
- xray
- v2ray
- trojan
- vless
- reality
- shadowsocks
- clash
- clash-meta
- mihomo
- 代理节点
- 翻墙
- 科学上网
- 自建节点
- 出境
- proxy
- tunnel
- 抗封锁
version: 1.0.0
author: hermes
license: MIT
platforms:
- linux
- macos
metadata:
  hermes:
    tags:
      disable:
      - 不适用场景
      - 无关任务
      trigger:
      - 自托管代理
      - 代理部署
      - xray
      - v2ray
      - shadowsocks
      - proxy 部署
      - 翻墙
---
--
--
-

# 自建反审查代理节点部署

用于在海外云主机搭建代理服务端（Xray 系），并让本地 Clash.Meta/mihomo 作为客户端做规则分流/透明网关。

> 合规提示：此类工具的部署与跨境使用在不同司法辖区有不同合规要求。执行前让用户自行确认当地法规边界，不要替用户判断合规性。本 skill 只讲技术实现。

> **结论书写纪律（维护本 skill 必读）**：凡标注「当前环境/本环境/实测失败」的结论，**必须**带 (1)`verified_on` 日期 + (2) 具体「环境指纹」(版本/OS/网络形态/客户端) + (3)「失效/重验触发条件」。禁止写成"Reality 必然失败"这类普适结论——Reality 失败是条件性的，换版本/OS/域名/客户端即可能不同。任何环境结论变更时同步更新本注记，不删历史 verified_on。
>
> **凭据管理纪律（2026-07-12 确立）**：真实接入参数（服务器 IP、端口、密码/UUID、证书 sha256 指纹、SSH 端口等）**严禁写入本 skill 或任何会被 git/同步/备份提交的文本**（templates/references/scripts 一律用 `<IP>` `<密码>` `<uuid>` `<SHA>` 占位符）。真实凭据只存在于运行环境（服务端 config + 客户端 config），需要时用 SSH 现取现用（python3 读服务端配置 + openssl x509 取指纹）。原因：skill 进 git 后明文密码永久落版本历史，撤回困难。本纪律与「结论书写纪律」同等强制。
>
> **两种输出场景（同一纪律的两面，2026-07-12 用户明确）**：
> ① 写入 skill / template / git 等持久文本 → 一律脱敏占位符，绝不落真实值。
> ② 在对话中向用户交付「能直接连」的配置（用户说「要实际数据」/「给我接入参数」时）→ 用 SSH 现取真实参数直接给，不入库即可。用户要的是可立即使用的真实凭据，不要回一份通用模板糊弄。
> 判断标准：持久化文本 = 脱敏；临时对话交付 = 真实值。二者不冲突。

## 0. 架构模型（先搞清层级，否则会答错）

- **Shadowsocks (SS)**：一套完整协议栈 = 服务端(ss-server) + 客户端。能独立"出节点"。
- **Clash / Clash.Meta / mihomo**：**客户端侧规则引擎**，本身不是节点协议。它消费 SS / VMess / VLESS / Trojan / Hysteria 等节点，负责域名/IP/国家分流、策略组、TUN 透明网关。
- 所以"SS 和 Clash 哪个好"是错的问题。正确组合是：**海外机跑 Xray(Trojan/VLESS/SS) 出节点 → 本地 mihomo 管分流**。
- mihomo 能当 SS/VLESS/Trojan 的**客户端**，也能开 mixed/socks/http **入站监听**，但**不能当 SS 服务端**（本机构建 `type: ss` 入站报 `unsupport proxy type: ss`）。

## 1. 协议选型

| 方案 | 抗封锁 | 前置条件 | 备注 |
|------|--------|----------|------|
| 裸 SS (chacha20/aeas) | 弱，固定首包指纹易被 DPI 识别 | 无 | 仅应急/内网，不建议跨境 |
| SS-2022 / SS+obfs | 中 | 需套混淆插件 | 改善但仍可被协议指纹识别 |
| VLESS+Reality | 强（借真站证书，无自有证书） | 需真域名 SNI + 同版本兼容 | 见 §3，Xray 26.x 有兼容坑 |
| Trojan+TLS | 强（标准 TLS 1.3， indistinguishable from HTTPS） | 需证书（可自签） | 最稳、对版本不敏感，推荐默认 |

**默认推荐 Trojan+TLS（自签证书 + 客户端 skip-cert-verify）**。比裸 SS 抗封锁强一个量级，且避开了 Reality 的版本/环境坑。

## 2. Xray 26.x 破坏性变更（实测 26.3.27，关键！）

部署前必读，否则会反复失败：

- `allowInsecure` **已从 tlsSettings 移除** → 改用 `pinnedPeerCertSha256`（证书 sha256，无冒号）或新版 insecure 字段。用旧字段直接 `Failed to start`。
- **Trojan 协议被标记 deprecated**（warning: "The feature Trojan ... is deprecated ... migrate to VLESS"），但仍可用。
- **VLESS client 的 users 必须显式 `"encryption": "none"`**，否则 `please add/set "encryption":"none" for every user`。
- **Reality 在「当前环境组合」下握手失败**（见 §3），优先用 Trojan。
  > ⚠️ 时效注记（非普适结论）：此结论仅针对 **2026-07-12 实测的 Xray 26.3.27 + Debian12 + 外部 NAT IP 云主机**这一组合。Reality 本身不必然失败——换 Xray 版本、换 OS、改用真实域名绑定的机器、或直接在原生支持 Reality 的客户端（非 mihomo）上可能正常。**失效/重验触发条件**：(a) Xray 升级到新主版本后；(b) 换不同云厂商/系统镜像部署时；(c) 拿到真实域名并绑到服务器时 → 应重新用 §5 隔离测试评估 Reality 是否可用，不要默认沿用本结论。

详见 `references/xray-26x-breaking-changes.md`。

## 3. Reality 排错（如仍要踩）

错误信号与含义：

- 客户端 `REALITY authentication failed` 或服务端日志 `processed invalid connection ... incorrect server hello or handshake incomplete` → 包已到达服务端，但认证参数不匹配（密钥对 / shortId / flow / uuid）。
- 客户端 `received real certificate (potential MITM or redirection)` → **不是真 MITM**，是服务端 Reality 验证失败后按设计把连接 fallback 到 `dest`（真站点），客户端因此看到真证书。含义仍是"客户端 Reality 认证与服务端不匹配"。
- `i/o timeout` 与 auth 失败交替 → 有时包根本到不了服务端（防火墙/网络），有时到了但握手失败。先用 §5 的本地同版本 client 测试隔离。

**密钥对管理坑（最易错）**：
- `xray x25519` 输出 `PrivateKey: <priv>` 和 `Password (PublicKey): <pub>`。pub 行含空格括号，naive `grep "PublicKey:"` / `sed` 提取会失败 → 用 `awk '/PrivateKey/{print $NF}'` 和 `awk '/PublicKey/{print $NF}'`。
- **服务端 privateKey 与客户端 publicKey 必须来自同一次 `xray x25519` 调用**。重生成一端而忘了另一端 → "authentication failed"。每次改密钥，两端同源重写。

## 4. mihomo 客户端节点格式

Trojan（推荐）：
```yaml
  - name: "trojan-tls"
    type: trojan
    server: <IP>
    port: 8443
    password: "<password>"
    network: tcp
    udp: true
    sni: <IP-or-domain>
    skip-cert-verify: true
```
VLESS+Reality（需 client-fingerprint，否则报 `REALITY is based on uTLS, please set a client-fingerprint`）：
```yaml
  - name: "vless-reality"
    type: vless
    server: <IP>
    port: 8443
    uuid: "<uuid>"
    flow: xtls-rprx-vision
    network: tcp
    tls: true
    servername: microsoft.com
    reality-opts:
      public-key: <pub>
      short-id: ""
    client-fingerprint: chrome
    udp: true
```
改节点后记得同步 Proxy 策略组里引用的节点名，否则 `proxy group: 'X' not found` 导致 config test 失败。

## 5. 验证方法论（务必以真实状态为准，不要从客户端配置推断）

- **外部仓库事实**：不要凭记忆断言 repo 归属/状态。用 GitHub API：`api.github.com/repos/OWNER/REPO` 取 stars/archived/description；404 即不存在；注意**仓库改名/复用**（例：`MetaCubeX/mihomo` 现是原神 Python 数据包，非 Clash.Meta 内核）。
- **已部署服务**：SSH 进服务器，读真实配置 + `ps` + `ss -tlnp`，不要从本端 client 配置反推服务端状态。
- **服务端自测隔离**：在服务器用**同版本 xray** 写一份 client 配置连 `<ip>:<port>`，能通说明服务端 OK，问题在客户端/网络。注意：连服务器的**外部 IP** 可能经 NAT 回环被重定向（拿到真站证书），必须用 <ip>。
- **端到端**：经 mihomo API 切节点 `PUT /proxies/Proxy` body `{"name":"trojan-tls"}`，再 `curl -x http://<ip>:<mixed-port> https://api.ipify.org` 查出境 IP。同时切回 SS 确认 fallback 仍在。
- 改本端 mihomo 配置前先 `cp` 备份；`patch` 工具拒绝写 `/etc` 系统路径，用 `sudo python3` 做精确字符串替换，最后 `mihomo -t` 校验。

## 6. 最小执行顺序（以 Trojan 为例）

1. 海外机：装 Xray（`bash <(curl -sL https://github.com/XTLS/Xray-install/raw/main/install-release.sh) install`）。
2. 生成自签证书：`openssl req -x509 -newkey rsa:2048 -keyout server.key -out server.crt -days 3650 -nodes -subj "/CN=<IP>"`；**chmod 644**（xray 以 nobody 跑，600 会 permission denied）。
3. 写服务端 config（见 `templates/trojan-server.json`），`systemctl restart xray`，`ss -tlnp | grep 8443` 确认监听。
4. 本端 mihomo 加 trojan 节点（见 `templates/mihomo-trojan-node.yaml`），设首选，SS 留 fallback。
5. 端到端验证（§5）。

## 支持文件
- `references/xray-26x-breaking-changes.md` — Xray 26.x 破坏性变更与 Reality 失败诊断详表
- `templates/trojan-server.json` — 已知可用 Trojan+TLS 服务端配置
- `templates/mihomo-trojan-node.yaml` — 客户端节点片段
- `templates/vless-reality-server.json` — VLESS+Reality 服务端配置（版本兼容时参考）
- `scripts/verify-xray.sh` — 服务端状态/监听/日志探针
