---
name: web-tools-usage-spec
description: Hermes 网页工具（web_search / web_extract / scrapling MCP / markitdown）的当前配置、能力边界、按场景选型规范与已知缺口。任何涉及"联网搜索/抓网页/网页转MD/知识库入库"的任务前先读此规范。
version: 1.0.0
author: Hermes + 老黎
license: MIT
platforms:
- linux
metadata:
  hermes:
    tags:
      trigger:
      - 网页工具
      - web_search 用法
      - web_extract 缺口
      - 抓取网页规范
      - scrapling 怎么用
      - 联网搜索配置
      - scrapling 配 hermes
      - markitdown 转换
      disable:
      - 不适用场景
      - 无关任务
    disable:
    - cli_only
    - read_only
---
-

# 网页工具使用规范（Web Tools Usage Spec）

Hermes 当前（2026-07-14 实测）共有三层网页相关能力，分工明确。
**任何联网任务前先判断走哪层，避免踩"web_extract 坏掉"的坑。**

## 当前真实配置（config.yaml）
```yaml
web:
  backend: ddgs
  search_backend: ddgs
  extract_backend: ''      # 空 → 回退 backend=ddgs
  use_gateway: false
```
venv (~/.hermes/hermes-agent/venv) 已装：ddgs 9.14.4 / scrapling 0.4.11 / playwright 1.61.0 / curl_cffi 0.15.0 / markitdown 0.1.6

## 三层能力边界

### ① 原生 Hermes web 工具（Hermes 内置）
| 工具 | 状态 | 说明 |
|---|---|---|
| `web_search` | ✅ 可用 | ddgs 零凭据，返回真实搜索结果（**混 Bing 推广链接，噪声偏高**） |
| `web_extract` | ❌ 坏 | ddgs 是 search-only backend，报错：`DuckDuckGo (ddgs) is a search-only backend and cannot extract URL content` |

### ② scrapling MCP（已接入，✓ enabled，10 工具）
- 配置在 `config.yaml` 的 `mcp_servers.scrapling`（不在 mcp.json，mcp.json 是 codebase-memory-mcp 自己的）
- `hermes mcp list` 显示 ✓ enabled；`hermes mcp test scrapling` 实测 10 工具可达
- **注意：MCP 工具要新会话才加载**（改 config 后需 /reset）。老会话会报 "No MCP tools available"。
- 10 工具分工：
  - 基础 HTTP：`get` / `bulk_get`（浏览器指纹伪装，支持 HTTP/3）
  - 动态渲染：`fetch` / `bulk_fetch`（Chromium 渲染 JS 页）
  - 隐身反爬：`stealthy_fetch` / `bulk_stealthy_fetch`（过 Cloudflare Turnstile）
  - 会话管理：`open_session` / `close_session` / `list_sessions`
  - 截图：`screenshot`（返回图片块，模型可直接看）
- 独有价值：**先按 CSS selector 抽目标内容再喂 AI** → 省 token、过反爬（其他 MCP 是把整页塞给 AI）
- 实测对比（抓 D4Vinci/Scrapling 仓库页）：scrapling 抽正文 18,813 字符（干净），比 curl+base64 原始 30,618 字符**噪声削减 38.6%**，且 star 数/CSS 定向抽取免额外 API 请求。
- **css_selector 防截断**（2026-07-14 实测）：不加 css_selector 时 fetch 返回整个 body 序列化的 JSON，大型页面（GitHub Trending ~132KB）超过 sandbox 上限被截断，核心数据丢失。加 `css_selector="article.Box-row"` 后只返回 ~8KB 精确内容，15 条数据完整提取。**抓列表/卡片类页面第一反应传 css_selector 限定容器子树。** 详见 hermes-web-tooling skill 的「Scrapling css_selector 最佳实践」章节。

### ③ markitdown（本地文件→MD，知识库用）
- 与"网页抓取"是两条线：markitdown 管**本地文件**（PDF/Word/Excel/图片 OCR/音频/YouTube→MD），不抓网。
- 实测：HTML/Word/PDF→MD 均通过（PDF 来自真实文件 `~/OmniRoute-视频PPT.pdf`）。
- 局限（官方声明）：面向 LLM 文本分析管线，**不为人类高保真消费**——设计感双栏 PDF 转出来表格会错位，但语义不丢，喂知识库够用。

## 按场景选型（铁律：先判场景再调用）

| 你要做的 | 走哪层 | 备注 |
|---|---|---|
| 搜信息/找仓库 | `web_search`（ddgs） | 零配置已通；结果带推广噪声，关键结论需二次核实 |
| 抓某网页正文 | **scrapling MCP**（get/fetch） | 别用 web_extract（坏） |
| 抓 JS 动态渲染页 | scrapling `fetch` | 吃 Chromium |
| 抓 Cloudflare 等反爬页 | scrapling `stealthy_fetch` | 过 Turnstile |
| 批量抓多个 URL | scrapling `bulk_*` | 并发标签页 |
| 抓完存知识库 | scrapling 抓 → markitdown 转 MD | 两条线接力 |
| 本地 PDF/Word/Excel 转 MD | markitdown | 不经过网络 |

## 已知缺口与补强路线（未决，记录备查）
- **原生 web_extract 仍坏**：extract_backend 空，ddgs 不能 extract。
- 已被 scrapling MCP 覆盖（推荐，零额外服务）。
- 备选：起 SearXNG 自托管，配 `web.extract_backend: searxng` 让原生 web_extract 复活（需常驻一个服务，代价高）。
- 决策：维持现状（搜索 ddgs + 抓正文 scrapling MCP），除非老黎要求复活原生 extract。

## 踩坑提醒（接入 scrapling 时踩过，详见 hermes-mcp-server-setup 技能）
1. `hermes config set` 把 args/env 存成字符串 `'["mcp"]'`，导致 mcp test 报 dictionary 错误 → 需 python 直接改 config.yaml 为真实列表/字典。
2. `scrapling mcp` 是 CLI 子命令，不是 `python -m scrapling mcp`。
3. `scrapling install` 的 `playwright install-deps` 需 root，普通用户会失败但浏览器二进制已就位、不影响。
4. MCP 入口在 v0.4.11 wheel 里是 CLI 子命令，不是独立 mcp 模块文件。

## 验证命令（随时自查）
```bash
hermes mcp list                      # 看 scrapling 是否 ✓ enabled
hermes mcp test scrapling           # 应 ✓ Connected + 10 tools
grep -nA4 '^web:' ~/.hermes/config.yaml   # 看后端配置
~/.hermes/hermes-agent/venv/bin/python -c "import ddgs,scrapling,markitdown; print('ok')"
```
