---
name: agent-context-classification
version: 1.0.0
author: hermes
date: 2026-07-12
category: methodology
trigger_tags:
- 上下文分类
- 长对话压缩
- 上下文治理
- conversation compression
- context classification
- SpanKind
- 历史检索优先
- message classification
- token 压缩
- execution goal extraction
- 执行目标提取
description: 将 dcg(Destructive Command Guard) 的 SpanKind 命令上下文分类范式迁移到 Agent 长对话治理：按"是否影响结果"把消息分为
  Executed/Argument/Data/Comment，用于 压缩分层、历史复用优先召回、执行目标提取。含真实数据证据与不改 hermes-agent 核心的私有
  side-table 实现。
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
      - 上下文分类
      - 对话分类
      - SpanKind
      - 上下文标签
      - 对话类型识别
      - agent 上下文
      - message_tags
---
--
--
-

# Agent 上下文分类（SpanKind 迁移）

## 核心思想

dcg 把 shell 命令切成 `Executed / InlineCode / Argument / Data / Comment / HeredocBody`，
分类的**唯一目的**不是"描述命令"，而是**决定后续动作**——Executed 影响结果必须检查，
Data 不影响结果可跳过。这跟"匹配什么规则"无关，跟"这段输入是否进入执行路径"有关。

把这个范式从"命令安全"上移到"Agent 工作流"：把对话消息按**是否影响结果**分类，
直接服务于三件事——压缩、历史复用、执行目标提取。本质是结果导向的上下文治理，
不是检索优化（向量天花板不归它管，见 Pitfalls）。

## 为什么值得做（真实数据，非推测）

来源：~/.hermes/state.db 两个真实长 session（500 / 376 条消息，228 / 222 次工具调用）。

| 类别 | SOUL更新#3 | opencode协作 |
|---|---|---|
| Data（工具原始输出） | 75.5% token | 85.4% token |
| Executed（执行上下文） | 18.7% | 9.1% |
| Argument（解释文本） | 5.7% | 5.4% |

- **长对话 75–85% 的 token 是工具原始输出（Data）**，真正驱动执行的上下文仅 10–20%。
- 分类压缩（Data→8%、Executed→100%、Argument→20%）：省 **74.1% / 83.0%** token，执行上下文零损失。
- 历史检索：FTS5 全文召回执行决策率仅 **13–50%**（工具输出淹没），分类优先后 **100%**。
- Comment 类实测为 **0**（用户反馈阈值低、直接给方案，无客套）——真实价值集中在"Data 识别"这一刀。

## 分类映射（规则即可，对齐 dcg SpanKind）

| SpanKind | Agent 上下文等价物 | 对结果的作用 | 压缩比 |
|---|---|---|---|
| Executed | 用户指令 + assistant 行动决策/工具调用意图 | 决定"做了什么" | 1.0 |
| Argument | 描述性/解释性文本（含"说明/原因/即"） | 可追溯但不驱动 | 0.2 |
| Data | tool 角色原始输出（命令结果/文件/API） | 被处理的过程材料 | 0.08 |
| Comment | 客套/过渡/纯确认 | 零作用 | 0.0 |

**规则分类器（已验证足够准，无需 LLM）：**
- `role == "tool"` → Data（置信度 1.0，role 字段直接可用）
- `role == "user"` → Executed（指令/反馈）
- `assistant` 带 `tool_calls` → Executed（行动意图）
- `assistant` 纯文本 → 按标记启发式分 Argument/Comment/Executed

## 三个结果导向用途

1. **工作执行聚焦**：执行前对当前上下文分类，把 Executed（本轮真要的 + 相关历史决策）提溜出来，
   Data/Comment 降级。与铁律#6（聚焦本轮、不推演）是同一目标的两面——一个管"别加噪音"，一个管"从已有噪音捞信号"。
2. **超长对话压缩**：按是否影响结果分层，不是无差别截断或 LLM 摘要。压缩后上下文仍能支撑"继续干活"，
   因为所有执行上下文都在。LLM 摘要常把"执行决策"和"数据"混压，导致忘掉"刚才决定要做什么"。
3. **执行目标提取**：Executed 类天然就是"用户指令 + agent 决策 + 工具调用意图"，拼起来即"本轮要干什么"。
   分类本身就是目标提取。

## 实现模式（关键：不碰 hermes-agent 核心）

`hermes_state.py`（`search_messages`）是 hermes-agent 核心，AGENTS.md 明确"核心窄腰，不修改 core 文件"。
但它已提供 `role_filter` 参数——直接传 `role_filter=["user","assistant"]` 即可排除 tool(Data 类)，
**无需改 JOIN**。落地采用：私有 side-table + 调用侧优先排序，不侵入核心。

已落地文件（~/.hermes/scripts/）：
- `init-context-tables.sql` — 建 `message_tags.db`（私有 side table，message_id 关联 state.db.messages.id）
- `context-processor.py` — 规则分类最近 N 条消息写标签 + `retrieve_prioritized()` 分类优先检索演示
- `vdb-autoload.py` 已加 `--process-context`，`--auto` 模式自动触发（分类不依赖 chroma，vdb 不可用时也跑）

调用侧优先检索约定：检索历史时先用 `role_filter=["user","assistant"]` 排除 Data，
或读 `message_tags` 优先 `span_kind IN ('EXECUTED','ARGUMENT')`。

## Pitfalls

- **不要为追 100% 召回去改 vdb 融合层**：SpanKind 式路由在 vdb 融合层原型化仅 +2 Top-1 且引入 2 条新错误
  （见 vdb-retrieval-pipeline 的 pitfall）。向量天花板是真实的，置信度加权是徒劳，**允许命中失败**。
  这个范式只该用在"上下文怎么被使用"，不是"怎么被检索"——两者正交。
- **绝不修改 hermes-agent 核心文件**（state.db schema / hermes_state.py / cli.py）。
  用 side-table + 调用侧过滤实现。改 core 违反上游约束且难回滚。
- **规则分类够用，别急着上 LLM**：role 字段直接可用，Comment 类对直接型用户恒为 0。
  只有复杂场景（assistant 长文本既要当产出又要当数据）才需二次校验，当前不必。
- **压缩比设定要保守**：Data=0.08 不是"丢到 0"，是"压成'工具X返回Y行，结论Z'"的短摘要，
  保留可复核的线索，别真删。

## 验证方法（真实数据说话，不要空谈）

1. 从 state.db 拉一个长 session 全量消息：`SELECT role, content, tool_calls FROM messages WHERE session_id=?`
2. 规则分类 → 统计三类 token 占比（中文 1.6 字/tok、英文 4 字/tok 估算）
3. 对比：FTS 全文召回 vs `retrieve_prioritized()` 分类优先召回，看执行决策命中率
4. 确认 Data 占比 >70% 即说明分类压缩收益显著

详见 `references/real-data-evidence.md`。可运行脚本见 `scripts/`。
