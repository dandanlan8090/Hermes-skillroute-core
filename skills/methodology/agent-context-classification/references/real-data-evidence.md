# 真实数据证据：SpanKind 上下文分类在 Agent 长对话治理的价值

来源：~/.hermes/state.db（session_search 后端）两个真实长 session，2026-07-12 实测。

## 样本

| session | 消息数 | 工具调用 | 主题 |
|---|---|---|---|
| 20260709_123247_c1a0b3 | 500 | 228 | 检查SOUL.md更新 #3（工作执行密集） |
| 20260624_064304_be3bd4 | 376 | 222 | opencode 稳定协作连接方案（排障+方案） |

## 三分类 token 分布（规则分类器）

| 类别 | SOUL更新#3 | opencode协作 | 压缩比 |
|---|---|---|---|
| Data（tool 原始输出） | 75.5% | 85.4% | 0.08 |
| Executed（执行上下文） | 18.7% | 9.1% | 1.0 |
| Argument（解释文本） | 5.7% | 5.4% | 0.2 |
| Comment | 0% | 0% | 0.0 |

## 压缩收益（模拟）

分类压缩（Data→8% / Executed→100% / Argument→20%）：
- SOUL更新#3：省 74.1% token，执行上下文保留率 100%
- opencode协作：省 83.0% token，执行上下文保留率 100%

## 历史检索复用对比（关键词 = "disable"）

**FTS5 全文召回（现有 session_search 行为）：**
- SOUL更新#3：8 条中 5 条执行上下文、3 条 Data（62%）
- opencode协作：8 条中仅 **1 条**执行上下文、7 条工具输出噪音（12.5%）

**SpanKind 分类优先召回（Executed 优先）：**
- 全部 8 条均为 Executed/Argument（100% 执行上下文）

## 落地文件（~/.hermes/scripts/）

- `init-context-tables.sql` — 建 message_tags.db（私有 side-table，message_id 关联 state.db.messages.id）
- `context-processor.py` — 规则分类最近 N 条 + `retrieve_prioritized()` 演示
- `vdb-autoload.py --process-context` — --auto 模式自动触发（不依赖 chroma）

## 分类器规则（已验证足够准，无需 LLM）

```
role == "tool"                  -> Data       (置信度 1.0, role 字段直接可用)
role == "user"                  -> Executed   (指令/反馈)
assistant 带 tool_calls         -> Executed   (行动意图)
assistant 纯文本:
    短且以[好的/明白/收到/继续/稍等]开头  -> Comment (0.7)
    含[说明/原因/即/也就是/换句话说]且>200字 -> Argument (0.7)
    含代码/命令(```, def, import, SELECT, sudo, curl, .py) -> Executed (0.9)
    默认                              -> Argument (0.7)
```

## 约束（重要）

- **不修改 hermes-agent 核心**（state.db schema / hermes_state.py / cli.py）。
  search_messages 已提供 `role_filter` 参数，调用侧传 `role_filter=["user","assistant"]`
  即可排除 Data 类，无需改 JOIN。
- 当前真实价值集中在"Data 识别"一刀（Comment 恒为 0，用户直接型反馈风格）。
  不要夸大四分类全覆盖。
