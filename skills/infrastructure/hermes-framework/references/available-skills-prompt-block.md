# available_skills 注入区块 — 源码实证（2026-07-14）

会话实测结论，全部来自读源码（`~/.hermes/hermes-agent/venv`，hermes_agent 0.18.2 可编辑安装）。
本文档只描述机制，不修改核心代码（核心改动违反铁律#1 持久化边界）。

## 1. 这个区块是什么

系统 prompt 里的 `<available_skills>...</available_skills>` 块，把**所有** skill 的
`<name>: <description>` 全量内联进去（约 80 条时 ≈ 12–14 KB，是单次注入的第二大头，
仅次于工具 schema）。模型靠它做第 3 层召回（"MUST load" 指令）。

## 2. 构建位置（确切）

- `agent/prompt_builder.py:1445` `build_skills_system_prompt()`
  - 第 1495–1548 行：glob skills/ 目录 + 外部目录，收集 `(name, description)` 元组
  - 第 1652–1653 行：默认每个 skill 输出 `    - {name}: {desc}`
  - 第 1691–1693 行：拼成 `<available_skills>` 块
- `agent/system_prompt.py:314` 调用 `build_skills_system_prompt(compact_categories=...)`
- 缓存：`_SKILLS_PROMPT_CACHE`（LRU），cache_key 见下方 §4

## 3. 与 vdb 路由门禁（routing.py）的关系 —— 关键澄清

**两者是独立管线，routing.py 管不到这个区块。**

- `vdb/routing.py::is_query_allowed_for_skill()` 只在 `matcher.search()` 返回结果**前**过滤
  （拦截重型框架文档被业务 query 误召回）。它决定"vdb 检索返回哪几个 skill 名"。
- `<available_skills>` 块是启动/构建 system prompt 时，由 `prompt_builder` **glob 整个 skills/ 目录**
  直接内联的，不经过 routing.py，与用户 query 无关。

所以"用路由门禁做到按需展开 available_skills"是不可能的——门禁在检索侧，区块在注入侧。
要砍这个区块，只能动注入侧（prompt_builder / 配置开关），或借助下面的 focus 降级开关。

## 4. 官方内置的精简开关：focus 模式（零核心改动）

`prompt_builder` 已有"降级类"（demote to names-only）机制：

- `prompt_builder.py:1631-1634` `demoted` = 命中 `compact_categories` 的类
- `prompt_builder.py:1652-1653` 降级后只输出 `  {category} [names only]: {names}`，丢 description
- `cache_key`（1481–1489）**含** `compact_categories` → 改它只生成不同缓存条目，
  **不违反 prompt 缓存铁律**（AGENTS.md 要求 session 内 byte-stable；focus 是会话级 opt-in，满足）

调用来源：`system_prompt.py:309` `coding_compact_skill_categories(platform, cwd)`，
由 `agent/coding_context.py` 实现，受 config `agent.coding_context` 控制：

| 模式 | 行为 |
|------|------|
| `auto`（默认） | 仅 coding posture 提示+快照；skill 索引不动（全量 description） |
| `focus` | 同 auto + 把**非 coding 类**降级为 names-only + 工具集收敛到 coding 集 |
| `on` | 强制 posture（含非 workspace） |
| `off` | 完全禁用 |

开启：
```
hermes config set agent.coding_context focus
```
效果：lark-*/media/social-media/integration 等非 coding 类只留名字，描述被砍。
估算可从 ~13KB 降到 ~3–4KB（取决于非 coding 类占比）。coding 类（debugging/tdd/git/plan）
description 仍全量——focus 语义就是"保 coding、压非 coding"。

**能力边界（focus 做不到的）**：
- 不能让所有类都只列名（除非改 prompt_builder 本身 = 碰核心，铁律#1 不希望）。
- 不能"路由命中才展开"（那是动态注入，与常驻索引的设计相反）。
- 要做到"全 names-only"或"按需展开"，必须改 `prompt_builder.py` 渲染逻辑。

## 5. 实测体积（2026-07-14 SOUL.md 瘦身会话）

| 组件 | 大小 | 备注 |
|------|------|------|
| SOUL.md | 4013 B（重切前 9525 B，-58%） | 极简铁律+路由表 |
| USER.md | 4932 B | |
| MEMORY.md | 6455 B | |
| available_skills 块 | ~12–14 KB（**估算**，未实跑度量） | focus 后可砍到 ~3–4KB |
| 工具 schema | ~10–12 KB（**估算**） | 随每次请求下发，独立于 skills |
| 头部/其他 | ~1.5 KB | host/profile/provider |

> 注：available_skills 与工具 schema 的尺寸是会话中基于文件体积的**估算**，非精确渲染度量。
> 精确数字用此法取得：在 venv 里 `from agent.prompt_builder import build_skills_system_prompt;
> print(len(build_skills_system_prompt()))`，对比 focus 开/关两种状态。

**对旧文档的纠正**：本总纲 §0/§7 旧的 `system prompt ≈ 6,100t/轮` 公式**漏算**了
available_skills 块（~13KB ≈ 3.5K t）与工具 schema（~10-12KB ≈ 3K t）两个最大头，
因此严重低估了真实注入量。真实单次注入 ≈ 45–47KB（~1.5–1.7 万 t），远非 6K。
SOUL.md 瘦身只动其中一个小头（框架文件 ~5.5KB），大头仍在 skills 区块与工具 schema。

## 6. 排查/调优 checklist

- 想砍 available_skills 体积：先开 `focus` 实测（零风险、官方支持、cache-safe）
- 想确认某个 skill 是否进索引：看 `prompt_builder` 的 `demoted`/disabled 判定，
  不是看 routing.py（routing 只影响检索召回，不影响注入）
- 改 compact_categories 后无需重建 vdb（它不属于 vdb 管线）
- 修改核心 prompt_builder 前请三思：违反铁律#1 持久化边界，且会随 `hermes update` 被覆盖
