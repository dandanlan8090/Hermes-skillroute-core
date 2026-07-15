---
name: tool-selection-discipline
license: MIT
platforms:
- linux
version: 1
author: hermes
disable: false
trigger:
- 选择/调用工具前
- 工具调用失败需要换工具重试
- 多工具环境下不确定用哪个
- 抓取网页/URL 正文
- 为什么没用上已有工具
description: 多工具环境下按"任务动词→候选工具枚举→按专长/开销排序"选型，而非凭印象选最熟悉的；失败恢复先扫同动词候选里更轻量/更专长的，browser
  只作需要交互/视觉的兜底，不当万能首选。
metadata:
  hermes:
    tags:
      disable:
      - 不适用场景
      - 无关任务
      trigger:
      - 工具选择
      - 工具调度
      - 选型纪律
      - 避免误用工具
      - 工具适用性
      - agent 工具
      - 工具边界
---
--
-

# 工具选型纪律（Tool Selection Discipline）

## 铁律

遇到某类能力需求，**先枚举所有能完成它的工具，按「专长度↑ / 开销↓」排序选最靠前的**，而不是用最熟悉的那个。

这是 SOUL 铁律 #0（技能主动全量检索，不凭印象）在「工具选择」维度的延伸。工具少时凭印象够用，工具一多必然失效——每次失败恢复都会掉进同一个坑。

## 失败恢复规则（关键）

某工具调用失败时，**第一步是扫同动词下的其他候选工具里有没有更轻量/更专长的**，再决定升级到重工具。绝不要把「换工具」默认成「升级到最重的通用工具」。

## 反面案例（真实失误，2026-07-14）

需求：抓取 OpenRouter 免费模型页正文。

错误路径：
1. `web_extract` 失败（环境里 `web.extract_backend` 被误配成 ddgs，只搜不抓正文）
2. 第一反应是开 `browser`（navigate→snapshot 翻 AX 树）——最重、最慢的兜底
3. 直到用户提示才想起 `mcp__scrapling__get` 一直在工具清单里，实测一把成功

根因：没有「任务动词→候选工具枚举」习惯，凭印象挑最熟的，失败就换另一个印象里的，从不主动枚举全部候选。

正确路径应是：
```
抓网页正文：
  scrapling(get/fetch)   → 专精度高、开销低，首选
  web_extract            → 仅当 extract_backend 配对接管（如 firecrawl/exa）时才可靠
  browser                → 仅当需交互/渲染/视觉校验时，最后兜底
```

## 当前工具选型速查（以此为准，随工具增减更新）

### 抓网页 / URL 正文
- **首选** `mcp__scrapling__get`（纯 GET + markdown/text，最快）
- 高防护站（Cloudflare 等）→ `mcp__scrapling__stealthy_fetch`
- 批量 → `mcp__scrapling__bulk_get` / `bulk_fetch`
- `web_extract` 仅当 `web.extract_backend` 配成 firecrawl/tavily/exa/parallel 时才可靠；默认 ddgs 后端只搜不抓，会直接报错
- `browser_*` **仅兜底**：需要点击/填表/动态加载/视觉校验时才用

### 搜索
- `web_search`（轻量）
- `web_extract` 的搜索后端（ddgs）仅用于搜，不抓

### 读/写文件
- `read_file` / `write_file` / `patch` 永远优先于 `cat`/`echo`/sed/heredoc
- 改 `~/.hermes/config.yaml` 等受护栏文件：`patch`/`write_file` 会被拒，改用终端 python 直接改（用户显式授权时），或 `hermes config set`

### 代码/命令执行
- 3+ 步带处理逻辑的脚本 → `execute_code`（Python）
- 纯 shell 构建/安装/git/进程 → `terminal`
- 独立长任务/定时 → `cronjob` 或 `terminal(background=true, notify_on_complete=true)`

## 执行时自检（每次选工具前默念）

1. 这个需求动词是什么？（抓正文？搜？读文件？跑命令？）
2. 我能完成它的工具有哪些？（扫一遍工具清单，不只挑印象里的）
3. 按专长/开销排，最靠前的是哪个？
4. 上一步失败了——同动词下还有更轻量的候选吗？先试它，别直接升级到 browser。

## 验证

选错工具的代价是「慢/绕路/浪费 token」，不直接造成错误结果。验证方式：复盘一次「为什么没用上已有工具」时，确认是否走了「枚举候选→排序→选最轻」而非「凭印象→失败→升级最重」。
