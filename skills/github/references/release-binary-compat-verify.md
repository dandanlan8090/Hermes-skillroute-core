# Reference: 外部仓库分析 + 发布二进制系统适配性核验

适用：用户要求"分析某 GitHub 仓库的作用 / 系统适配性 / 是否能在当前机器跑"。
原则（老黎硬性要求）：涉及具体仓库、工具选型、适配性判断，必须先去源头拉真实数据再下结论，禁止凭记忆或泛泛而谈。

## 0. 工具路由（web_extract 未配置 Firecrawl 时）
- **browser 工具**：只能抓「正常 HTML 页面」——GitHub 仓库页、Release 列表页、Wiki 页。这些能拿到完整快照（star/fork/commit/资产矩阵）。
- **browser 对裸文本端点会渲染为空**（element_count=0、空白）：`raw.githubusercontent.com` 的 `.md/.json`、jsdelivr CDN、GitHub API 的 JSON 响应。
- **结论**：裸文本/API 端点一律用 `terminal` + `curl`（本机 mihomo TUN 网关可出境，实测可用）；需要交互/看渲染的 HTML 页才用 browser。
- `web_extract`（Firecrawl）在本环境未配置，调用会报 "Web tools are not configured"，不要走这条路。

## 1. 仓库分析取证（真实数据，不靠记忆）
- 仓库健康度：用 browser 开 `https://github.com/<owner>/<repo>`，读 star/fork/commits/最近提交日期/Issues/PR/Tags。
- README 全文：用 `curl -sL https://raw.githubusercontent.com/<owner>/<repo>/<branch>/README.md` 落地到 /tmp 再 read_file（浏览器开 raw 是空）。
- Release 资产矩阵：`https://github.com/<owner>/<repo>/releases`，看每个 release 的 Assets（平台/架构/glibc vs musl 变体）。
- 语言/许可：README 内通常自陈（如 "Single binary. .NET runtime embedded" → .NET 自包含）；GitHub API 标语言可能因仓库过大返回 403，别卡在这。

## 2. 发布二进制系统适配性核验（硬证据法）
不要只念 README 说"适配"，下二进制实测：
```bash
cd /tmp
V=v1.0.135; B=officecli-linux-x64
# 1) 下二进制 + SHA256SUMS
curl -fsSL --max-time 120 "https://github.com/<owner>/<repo>/releases/download/$V/$B" -o /tmp/$B
curl -fsSL --max-time 60  "https://github.com/<owner>/<repo>/releases/download/$V/SHA256SUMS" -o /tmp/SHA256SUMS
# 2) 完整性校验（防止被篡改 / 下载不完整）
grep " $B" /tmp/SHA256SUMS | (cd /tmp && sha256sum -c -)
# 3) 二进制类型 / ABI / 链接方式
file /tmp/$B
#   例: ELF 64-bit LSB pie executable, x86-64, dynamically linked,
#       interpreter /lib64/ld-linux-x86-64.so.2, for GNU/Linux 3.2.0
#   → .NET 自包含单二进制特征；"for GNU/Linux 3.2.0" 是极老的 ABI 下限
# 4) 动态依赖（确认本机能否直接跑）
ldd /tmp/$B
# 5) 本机环境对照
uname -m; uname -r; (ldd --version 2>&1 | head -1); . /etc/os-release; echo "$PRETTY_NAME"
```
- **架构矩阵**：x86_64→`linux-x64`；arm64/aarch64→`linux-arm64`；Alpine/musl→`linux-alpine-*`；mac/win 同理。注意是否缺 32 位/riscv/ppc。
- **libc 区分**：标准发行版用 glibc 版；Alpine/Docker-slim(musl) 必须用 alpine 变体，否则 glibc 缺失跑不起来。
- **显示依赖**：确认是否 headless 友好（README 提 "works in CI/Docker/no display" 即可无 X11/Wayland 跑）。

## 3. 实测样例（iOfficeAI/OfficeCLI，2026-07-13）
- 作用：为 AI Agent 设计的 Office 套件（Word/Excel/PPT 读改写），单二进制、.NET 运行时内嵌、Apache-2.0。
- 健康度：15.6k★ / 1.1k fork / 5,784 commits / 最近提交 2 天前 / v1.0.135 发布 3 天前 → 极活跃。
- 资产：linux-{x64,arm64,alpine-x64,alpine-arm64} + mac/win，均带 SHA256SUMS。
- 本机实测：arch=x86_64 / Ubuntu 26.04 / glibc 2.43 → 对应 `officecli-linux-x64`，`file`+`sha256sum -c` 通过，可直接跑。CM4(arm64/Debian13)→`linux-arm64`。
- 注意点：默认后台自动更新（可 `officecli config autoUpdate false` 关）、首装需联网拉二进制、screenshot 模式才用 headless browser。

## 4. 收尾
- 临时文件落 /tmp，核验完 `rm -f` 清掉（本例被安全扫描拦过 mass-delete，需用户 approve——正常）。
- 结论必须给出"本机 arch/libc ↔ 应选二进制"的明确映射，而非"应该能跑"。
