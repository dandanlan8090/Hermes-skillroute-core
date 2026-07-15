---
name: new-skill-template
description: "新增技能开发规范 (Skill Development Guidelines) — 触发：创建新技能/修改现有技能/写 SKILL.md。禁用：纯文档修改/配置调整。"
version: 2.1.0
author: Hermes Agent
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags:
      trigger:
        - "新技能"
        - "创建技能"
        - "skill"
        - "技能开发"
        - "new skill"
        - "authoring"
        - "写 SKILL"
        - "新建技能目录"
        - "修改 frontmatter"
        - "写技能"
      disable:
        - "纯文档"
        - "配置修改"
        - "不需要创建技能"
    skill_type: "methodology"
    priority: "highest"
prerequisites:
  commands: []
---

# 新增技能开发规范 (Skill Development Guidelines)

版本: 2.1.0
生效日期: 2026-07-10
适用范围: 所有新增或修改的 Hermes Agent 技能
参考: dzhng/skills write-skills 方法论（leading word / progressive disclosure / failure modes）

---

## Frontmatter 必填字段

每个技能的 `SKILL.md` frontmatter 必须包含以下字段：

```yaml
---
name: skill-name                          # 必填：技能名（小写，连字符分隔）
description: "中文描述 —— 触发场景。禁用：排除场景。"  # 必填：中英双语，简洁明确
version: 2.0.0                             # 必填：语义化版本号
author: 作者名                              # 必填
license: MIT                               # 必填
platforms: [linux, macos, windows]         # 必填：支持的平台
metadata:
  hermes:
    tags:
      trigger: ["正面条件 1", "正面条件 2", ...]    # 必填：触发关键词（至少 5 个）
      disable: ["负面条件 1", "负面条件 2", ...]    # 必填：禁用场景（至少 3 个）
    skill_type: "methodology|workflow|tool|integration"  # 必填
    priority: "highest|high|normal|low"    # 必填
    next_skill: "下一个技能名"              # 可选：流程链下一个环节
    requires: ["前置技能 1", "前置技能 2"]   # 可选：依赖的前置技能
  homepage: https://github.com/...         # 可选
prerequisites:
  commands: [required-cli-command]         # 可选
  env_vars: [REQUIRED_API_KEY]             # 可选
---
```

---

## §Description 写作规范（v2.1 新增）

`description` 是 frontmatter 唯一在向量召回和 LLM 触发决策时**始终加载**的字段。
它的三个职责按顺序：

1. **前 30 字符：leading word**
   必须是一个强概念词（动词短语 / 行业术语 / 抽象名词），让模型在少 token 投入下
   锚定整套行为。候选池见 §leading word 词汇库。

2. **中间 60 字符：核心动作**
   一句话说清这个 skill 做什么、产出什么、什么场景触发。

3. **末尾剩余：分支条件 + 禁用场景**
   列举 ≥ 3 个触发分支（"Use when X / Use when Y"），和 ≥ 1 个明确的 disable 场景
   （"禁用：纯文档修改"等）。disable 重复 frontmatter tags.disable 是冗余的，**保留
   在 description 里只写最重要的 1-2 个**，完整的走 tags.disable。

### 反模式

| 错误写法 | 为什么错 | 改法 |
|---------|---------|------|
| `description: "AI 求职助手"` | 没动作、没触发、没 leading word | `description: "Job-Match：AI 求职全流程编排。Use when 评估 JD/改 CV/写求职信。禁用：单点文档查询"` |
| `description: "提供了完整的写技能方法论，包括触发器写法、progressive disclosure..."` | 抽象描述，词太多 | 前置 leading word，砍到 1 句 |
| `description: "..."` 超过 1024 字符 | 每次都吃 context | 砍到 200 字符内，详尽内容放 body |

### 召回端配合

`vdb/indexer.py` 现在按 `name：{leading_word}。{desc}。触发：{branches}。` 模板生成
向量文档；`vdb/embed.py` 对 leading word 命中给 2x sparse 权重。
**所以 description 不写 leading word = 召回打折 50%（leading word 2x boost 拿不到）。**

---

## §SKILL.md 写作规范（v2.1 新增）

### 三段式 + 失败模式

```
# Skill 标题

## 1. 第一性原理 (First Principles)  ← 3-5 条
  每条一行：定义 + 为什么重要 + smell（如何识别违反）

## 2. 工作流 (Workflow)  ← 编号步骤
  每步一个 load-bearing 动作
  每步一个 completion criterion（可验证，不是"应该"）

## 3. 规则 (Rules)  ← 约束
  - 防止常见错误
  - 链接 conditional reference（点中才加载）
  - 标注 disable 场景

## 4. 失败模式 (Failure Modes)  ← 9 个标准模式
  Premature Completion | Embargo | Lucky Pass | Duplication
  Sediment | War Story | Implementation Index | Sprawl | No-op
  每个模式一行：tell（怎么识别）+ fix（怎么修）
```

### 长度上限

- 单个 SKILL.md ≤ 100 行（不含 frontmatter 和 examples）
- 超过 → progressive disclosure：长 schema/例子/变体推 `references/`
- `references/<name>.md` 单文件 ≤ 200 行
- 脚本推 `scripts/<name>.py`，调用方在 SKILL.md 用 `bash scripts/<name>.py` 引用
- 素材推 `assets/`，不解释

### 例子写法（教问题不教答案）

✅ 写 smell（怎么识别问题）+ signal（怎么确认是这个问题） + 让 agent 自己推
❌ 写"我们当时改了什么参数" → war story，几个月就腐烂

### 通用术语不重复

leading word / failure mode / sparse 权重 / fire-line 这类通用概念在 SOUL.md 或
AGENTS.md 定义一次。skill 引用 `见 SOUL.md §X` 即可，不重写定义。

### 不做的事

- 不要把"我们项目用了什么"写进 skill（sediment）
- 不要引用具体行号 / 函数名（implementation index，让 agent 自己 grep）
- 不要把"完整示例"塞正文（sprawl，推 references/）
- 不要写"be thorough / be careful"这种 no-op（模型默认就在做）

---

## §Leading Word 词汇库（v2.1 新增）

leading word 必须从以下池子选（按 skill_type 分桶）。自定义词需要先在 SOUL.md 注册
才会被 `vdb/embed.py` 识别为 2x boost。

### methodology 类（v2.1 初始化）

| 词汇 | 适用场景 |
|------|----------|
| `red-green` | TDD / 测试驱动 / 红绿循环 |
| `fog-of-war` | 探索未知 / 分阶段规划 / 边做边探 |
| `tracer-bullet` | 端到端最小通路 / 渐进增强 |
| `root-cause` | 调试 / 排查根因 / 不治症状 |
| `verify-first` | 完成判定 / 跑通再宣布 / 反对"应该 OK" |
| `sunk-cost` | 删废弃代码 / 拒绝保留"参考" / 推倒重来 |
| `ship-it` | 部署 / 发布 / 上线门控 |
| `ground-truth` | 文档驱动 / 引用官方源 / 反对拍脑袋 |

### workflow 类（v2.1 初始化）

| 词汇 | 适用场景 |
|------|----------|
| `dispatch` | 多 agent 派发 / 并行 / 隔离子任务 |
| `gate` | 卡口 / 验证通过才能进下一步 |
| `handoff` | 交接产物 / 上一步输出作为下一步输入 |
| `slice` | 切片 / 独立可验证 / API seam |

### tool 类（v2.1 初始化）

| 词汇 | 适用场景 |
|------|----------|
| `probe` | 探查 / 跑命令查状态 / 不修改 |
| `fire` | 触发 / 一次性操作 / 副作用明确 |
| `scaffold` | 生成模板 / 一次性结构 |

### integration 类（v2.1 初始化）

| 词汇 | 适用场景 |
|------|----------|
| `bridge` | 跨平台 / 协议转换 / 适配器 |
| `mirror` | 同步 / 镜像 / 一致性保证 |

### 选用规则

1. 先看 skill 核心动作属于哪一类（methodology / workflow / tool / integration）
2. 从该类池子里挑一个最贴的
3. 不要为了"显得高级"硬塞，no-op leading word 比重写还糟
4. 现有 skill 重写不强制，但新建 skill 必须遵守

---

## 标签设计原则

### trigger（至少 5 个）
- 用户视角词汇：用用户在自然对话中会说的词
- 中英文覆盖：同时包含中文和英文触发词
- 覆盖不同表达方式（同义词、变体）
- 具体明确：避免过于宽泛的词（如"工作"、"做"）

**标签在 vdb 语义匹配中的双重作用**：
1. **稠密向量侧**：tags 拼接在 name+desc 后送入 SiliconFlow BGE-M3（云端 1024d）
2. **稀疏打分侧**：仅 trigger_tags → 本地纯 Python lexical weights → `compute_lexical_matching_score` 与 query 关键词匹配 → 加权融合（0.6 × dense_cosine + 0.4 × sparse_lexical）

因此 trigger 标签质量直接影响召回：
- 标签越精准语义匹配越好
- 建议标签粒度在 2-6 字之间，太短（1字）向量表达弱

### disable（至少 3 个）
- 排除明确场景
- 流程阶段标记
- 技术约束
- 防止与其他技能冲突
- disable 标签不进向量文本，只用于检索后过滤（fuzzy 匹配 ≥ 0.7 则排除）

**必须从以下固定词库选取**，禁止自定义笼统文本（如"无关任务"、"不适用场景"）：

```
DISABLE_TAG_POOL = [
    "cli_only",            # 仅 CLI/TUI 可用，gateway 平台无效
    "long_context",        # 需大量上下文，不适合轻量查询触发
    "code_development",    # 纯代码开发类，不适合运维/问答场景
    "document_parse",      # 文档解析密集型，不适合快速响应
    "network_request",     # 发起外部 API/网络调用
    "windows_only",        # Windows 平台限定
    "deep_review",         # 深度审查/分析，不适合轻量触发
    "platform_gateway",    # 仅 gateway 消息平台可用
    "creative_gen",        # 图片/音视频生成类
    "read_only",           # 只读操作，不修改系统
]
```

选择原则：
- `cli_only`：仅在终端交互时可用，Telegram/Discord 等 gateway 平台不宜触发
- `long_context`：技能自身有大量参考文档，压缩成本高
- `deep_review`：一次性消耗大量 token，不适合频繁触发
- `network_request`：需要联网权限，沙箱环境不可用
- `read_only`：放宽限制，用户只查不问时倾向此类技能

---

## 技能类型定义

| 类型 | 说明 | 例子 |
|------|------|------|
| methodology | 工作方法论，定义"如何做" | TDD、debugging、brainstorming |
| workflow | 流程控制技能，定义环节顺序 | plan、hermes-oracle-mode |
| tool | 特定工具/CLI 的使用指南 | github、blogwatcher |
| integration | 外部服务/API 集成 | notion、airtable |

---

## 优先级定义

| 优先级 | 说明 | 加载策略 |
|--------|------|----------|
| highest | 元技能，每会话必加载 | 会话开始强制加载 |
| high | 核心方法论，任务相关 | 触发词命中必加载 |
| normal | 工具/集成技能 | 触发词命中建议加载 |
| low | 辅助/可选技能 | 仅在明确提到时加载 |

---

## 新增技能检查清单

**Frontmatter 检查：**
- [ ] `name` 是小写、连字符分隔、无空格
- [ ] `description` 是中英双语、包含触发和禁用说明
- [ ] `description` 前 30 字符含 leading word（v2.1 新增）
- [ ] `version` 遵循语义化版本 (MAJOR.MINOR.PATCH)
- [ ] `trigger` 标签至少 5 个，覆盖中文和英文
- [ ] `disable` 标签至少 3 个，明确排除场景
- [ ] `skill_type` 和 `priority` 是预定义值

**标签质量检查：**
- [ ] `trigger` 词汇来自用户自然语言，非技能内部术语
- [ ] `trigger` 和 `disable` 无重叠或矛盾
- [ ] `disable` 覆盖了常见误触发场景

**SKILL.md 内容检查（v2.1 新增）：**
- [ ] 三段式结构（第一性原理 / 工作流 / 规则）
- [ ] 含 §失败模式 段（9 个标准模式）
- [ ] 单文件 ≤ 100 行（不含 frontmatter）
- [ ] 长内容已推 references/scripts/assets
- [ ] 例子写 smell 不写答案
- [ ] 通用术语引用 SOUL.md/AGENTS.md 不重写

**内容检查：**
- [ ] 技能正文与 frontmatter 描述一致
- [ ] 包含清晰的使用场景和示例
- [ ] 有明确的红线（red flags）和常见借口（rationalizations）

---

## 版本更新规范

- **MAJOR**：破坏性变更（技能流程、核心规则改变）
- **MINOR**：新增功能或标签优化（向后兼容）
- **PATCH**：修正 typo、补充说明（不影响行为）

## 变更日志

- **2.1.0** (2026-07-10)：引入 dzhng/skills 方法论
  - 新增 §Description 写作规范（leading word / 三段职责）
  - 新增 §SKILL.md 写作规范（三段式 + 失败模式 + 长度上限）
  - 新增 §Leading Word 词汇库（21 个初始词按 skill_type 分桶）
  - 检查清单新增 description 和 SKILL.md 内容项
- **2.0.0** (2026-06-11)：重写 frontmatter 规范

---

## 元触发说明

本技能通过 AGENTS.md §1.4 实现强制加载：
当 `write_file` / `patch` 的目标是 `*/SKILL.md` 文件时，无论用户消息内容是什么，
都必须先加载本技能并完成 checklist 核对。

**最后更新**: 2026-07-10
