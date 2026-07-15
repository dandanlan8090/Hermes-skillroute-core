---
name: hermes-skill-index-optimization-insights
description: 技能索引(available_skills)压缩的实测经验：focus 模式真实收益仅 -5.4% 不值， SOUL.md 重切 -58%
  更有效；路由表即索引不违反检索铁律#0(是增强)但需碰核心受框架修改铁律①约束； vdb 覆盖缺口(27 个失效 lark-* 软链)是路由表即索引的硬阻塞。
metadata:
  hermes:
    tags:
      trigger:
      - 技能索引优化
      - available_skills
      - focus模式实测
      - prompt压缩
      - 上下文精简
      - 技能列表膨胀
      - 技能索引
      - 索引优化
      - skill-index
      disable:
      - 闲聊
      - 简单问答
    skill_type: infrastructure
    priority: 5
license: MIT
author: Hermes Agent
version: 1.0.0
platforms:
- linux
- macos
---
--
-

# 技能索引优化经验（实测）

> 基于实测数据，记录 `available_skills` 区块的压缩尝试与真实结论。
> 记录时间：2026-07-14

## 背景

`available_skills` 区块是 system prompt 的固定组成部分，由
`agent/prompt_builder.py:build_skills_system_prompt()` 生成，每次请求全量
注入所有技能的 `<name>: <description>` 列表（经 `<available_skills>` 标签包裹）。

在一次针对 "hi" 请求的上下文分析中，实测该区块大小约 **14.7 KB**，占单次注入
量的 ~30%。为降低固定开销，实测了官方提供的 `focus` 模式，结论是**收益可忽略**。

## 实测过程

### 测试环境（2026-07-14）
- **技能总数**：目录列出 96 个（含失效软链），真实存在 ~69 个
- **技能分布**：主要集中在 `core/`、`workflow/`、`methodology/`、
  `infrastructure/`、`integration/` 等顶层类——这些**不在**降级名单中
- **测试工具**：`references/measure_skill_index.py`（直接调 `build_skills_system_prompt()`
  换 `compact_categories` 参数对比，剥离平台/CWD 环境依赖）

### 关键机制
`focus` 模式通过 `agent.coding_context._NON_CODING_SKILL_CATEGORIES` 降级
非 coding 类技能为**仅显示名称**（不显示 description）。降级由
`prompt_builder.py:1631` 的 `demoted` 集合判定，命中类渲染成
`  <类> [names only]: a, b, c` 单行。

**降级类共 18 个**（来自 `_NON_CODING_SKILL_CATEGORIES`）：
apple, communication, cooking, creative, email, finance, gaming, gifs,
health, media, music, note-taking, productivity, shopping, smart-home,
social-media, travel, yuanbao

⚠ **环境陷阱**：`coding_compact_skill_categories()` 在非 coding 工作区
（如从 `$HOME` 跑、非 git repo）返回空集 → 降级不激活 → 测出 0 节省（假阴性）。
必须直接取 `_NON_CODING_SKILL_CATEGORIES` 作为 `compact_categories` 参数传入，
才能稳定复现 focus 效果。

### 实测结果（本机真实运行）

| 模式 | 区块 bytes | 行数 | 带 desc 技能数 |
|------|-----------|------|--------------|
| `auto`（默认） | 14,681 | 170 | 95 |
| `focus`（降级非编码类） | 13,889 | 163 | 88 |
| **差异** | **-792 (-5.4%)** | -7 | -7 |

**实际被降级的 5 类 7 个技能**：
- email：himalaya
- media：gif-search, media-creation-and-audio, youtube-content
- smart-home：openhue
- social-media：xurl
- yuanbao：yuanbao

## 结论

**`focus` 模式在本次测试环境下收益可忽略（-5.4%），不值得启用。**

原因：本仓库 80 个技能绝大多数分布在 `core/`、`workflow/`、`methodology/` 等
顶层类，这些**不在** `_NON_CODING_SKILL_CATEGORIES` 的 18 个降级类里。实际命中
降级的仅 7 个技能（5 类）。且 `focus` 仅在 coding 工作区自动激活，日常 CLI 从
`$HOME` 运行根本不触发，需手动 `config set agent.coding_context focus` 才生效
——为 5% 收益改缓存策略不划算。

## 真正的优化杠杆

### 1. SOUL.md 精简（已验证 ✓）
- 已从重切前的 9,525 bytes 压缩到 4,013 bytes（**-58%**）
- 方法：铁律细则拆为独立 skill（每条 `#N` 指向 `skill_view(name)`），
  删除与路由表重复的「技能索引速览」整段，SOUL.md 仅留铁律 + 路由表
- 当前最有效的上下文压缩手段

### 2. 路由表即索引（架构级，需评估 + 授权）
- 当前 `available_skills` 全量内联所有技能的 name + description，
  是模型「语义联想触发」的入口
- 潜在方向：改为「路由表即索引」——仅 SOUL.md 路由表做精确匹配入口，
  技能描述完全由 vdb 检索提供
- **铁律澄清（2026-07-14 老黎纠偏，重要）**：此方向**不违反检索铁律#0**
  （强制技能检索入口），反而把检索从「模型看目录自己决定」升级为
  「命中才动态展开」的显式检索，是 #0 的合规增强。
  ⚠ **切勿混淆两道铁律**：#0 = 检索入口（行为层面，管的是「干活前必须先检索」，
  不规定注入形态）；真正的闸门是**框架修改铁律①**（不深入 Hermes 核心 /
  优先外部钩子 / 避免更新失效）。「路由表即索引」若要落地，必须触碰
  `prompt_builder.py` 核心注入逻辑 —— 这是框架修改铁律①的边界，需另行明确授权才动，
  而**不是**「违反检索铁律」。评估此类改动时先分清是哪一道铁律在起作用。
- 风险：削弱模型语义联想触发，可能退化为「只能靠路由表精确匹配」
  （vdb 覆盖不足时尤甚，见「硬阻塞」一节）

### 3. 缓存隔离已内建
- `prompt_builder.py:1488` 的 `cache_key` 已含 `compact_categories`，
  focus 切换只生成不同缓存条目，不违反 prompt 缓存铁律
  （AGENTS.md：session 内 byte-stable；focus 是会话级 opt-in，满足）

## 硬阻塞：vdb 覆盖缺口（实测 + 已修复，2026-07-14）

**目录列出 96 个 skill，vdb 仅索引 71 个；catalog-only = 27（全 lark-*），vdb-only = 2（幽灵）。**

### ⚠ 真实根因（后续追查校正，曾误判为"失效软链"）

**曾误判**：27 个 `lark-*` 是失效软链、目标 `~/.hermes/.agents/` 已删除。
**实测推翻**：软链一直正确（`~/.hermes/skills/lark-im` → `../../.agents/skills/lark-im`
从 `~/.hermes/skills/` 解析即 `~/.agents/skills/lark-im`，**真实存在且含 SKILL.md**，
`readlink -f` 可验证）。`~/.agents/skills/lark-*` **全 27 个都在磁盘上**。

**真实根因**：`~/.hermes/vdb/indexer.py` 用 `SKILLS_DIR.rglob("SKILL.md")` 扫描技能。
**Python 3.14 的 `Path.rglob` 默认不跟进目录软链** → 27 个软链目录被整体跳过 →
vdb 仅 71 个。同目录 `os.walk(followlinks=True)` 能正确拿到全部 28 个 lark-*。

`prompt_builder` 仍能列出 27 个 lark-*，是因为它读的是另一路径（external/bundled 快照
元数据），与 indexer 的 rglob 扫描互不同源 —— 这也是"目录与 vdb 不一致"的真因。

### ✅ 修复与复测（已完成）

- 改 `indexer.py` 两处扫描（`build_index` + `check_index_stale`）为 `os.walk(followlinks=True)`
  + 构造 `Path(root)/"SKILL.md"`。
- 重建：`vdb/.venv/bin/python -c "import indexer; indexer.build_index(force=True)"`
- 结果：vdb 索引 **71 → 98 个**；目录 96 vs vdb 98 → **缺口 = 0（100% 覆盖）**；
  `lark-*`:目录 28 = vdb 28；飞书 query（发消息/表格/日历/文档）top3 全命中对应 lark-*。
- 完整可复跑配方（Detect/fix/verify + vdb 双 venv 工具链事实）：
  `references/vdb_symlink_rglob_fix.md`

### 推论（对"路由表即索引"方向）

**硬阻塞已清除** —— vdb 现 100% 覆盖所有目录技能（含 28 个飞书 skill）。该方向的前置
条件（检索覆盖无缺口）已满足。是否推进仍受**框架修改铁律①**（不深入 hermes-agent 核心
`prompt_builder`）约束，需另行授权。

### 诊断配方（复测覆盖用，见 references/vdb_symlink_rglob_fix.md 的 Detect 段）

1. 调 `build_skills_system_prompt(available_tools=None, available_toolsets=None)` 取完整
   available_skills 区块 → 正则解析全部 skill 名（含 `[names only]` 行）
2. 读 `vdb/vdb_state.json` 的 `skill_hashes` 键 → 已索引名集合
3. 差集 = catalog-only（目录有、vdb 无）；若非空，先 `readlink -f` 验证软链目标是否真存在，
   **不要直接认定失效软链** —— 先查是不是扫描逻辑（rglob 不跟进软链）的锅。

## 后续决策参考

| 场景 | 建议 |
|------|------|
| 当前技能分布下 | **不启用 `focus`**，收益 < 6%，不值得改缓存策略 |
| 未来大量引入非 coding 类技能 | 重新评估 `focus` 价值（重跑 references/measure_skill_index.py） |
| 寻求进一步压缩上下文 | 优先迭代 SOUL.md，而非动 `available_skills` |
| 启动期全量 vs 运行时按需展开 | 框架核心设计取舍，需明确需求后再动核心 |
| vdb 覆盖缺口 | **已修复**（rglob→os.walk followlinks）；复测见 references/vdb_symlink_rglob_fix.md |

## 附录：复现脚本

- `references/measure_skill_index.py` —— 对比 auto/focus 区块字节数（规避非 coding 工作区假阴性）。
- `references/diagnose_skills_coverage.py` —— 目录 vs vdb 覆盖差集 + 失效软链检测。
