# 真实验证报告（2026-07-12，state.db 实测）

本文件记录 context-compression skill 诞生时的两个长 session 真实数据。
数据来自 `~/.hermes/state.db`（Hermes 会话数据库），非模拟/估算。

## 样本 Session 元数据

| 属性 | SOUL更新#3 | opencode协作 |
|------|-----------|-------------|
| Session ID | `20260709_123247_c1a0b3` | `20260624_064304_be3bd4` |
| 消息数 | 500 | 376 |
| 工具调用数 | 228 | 222 |
| 类型 | 工作执行密集 | 排障+方案讨论 |
| 总 token（估算） | ~63,381 | ~68,598 |

## SpanKind 分类分布

分类规则（可复现，`state.db` messages 表的 role + tool_calls 字段即够）：
- EXECUTED：role=user（指令/反馈）或 assistant 带 tool_calls（行动意图）或含代码/命令
- ARGUMENT：assistant 纯文本 >200 字含"说明/原因/即"等解释标记
- DATA：role=tool（工具原始输出）
- COMMENT：assistant 短确认 <20 字（实测为 0，用户风格直接）

### SOUL更新#3（500 消息）
| 类别 | 消息数 | token 估算 | token 占比 | 压缩保留比 |
|------|--------|-----------|-----------|-----------|
| EXECUTED | 259 | 11,880 | 18.7% | 1.0 |
| ARGUMENT | 13 | 3,621 | 5.7% | 0.2 |
| DATA | 228 | 47,880 | 75.5% | 0.08 |
| COMMENT | 0 | 0 | 0% | 0.0 |
| **合计** | **500** | **63,381** | **100%** | 0.259（省 **74.1%**） |

### opencode协作（376 消息）
| 类别 | 消息数 | token 估算 | token 占比 | 压缩保留比 |
|------|--------|-----------|-----------|-----------|
| EXECUTED | 144 | 6,252 | 9.1% | 1.0 |
| ARGUMENT | 10 | 3,733 | 5.4% | 0.2 |
| DATA | 222 | 58,613 | 85.4% | 0.08 |
| COMMENT | 0 | 0 | 0% | 0.0 |
| **合计** | **376** | **68,598** | **100%** | **0.170（省 83.0%）** |

**分类压缩收益（Data 到 8%、Executed 100% 保留）：**
- SOUL更新#3：63,381 → 16,434 token（省 **74.1%**）
- opencode协作：68,598 → 11,687 token（省 **83.0%**）

## 检索命中率对比

关键词=disable（该 session 高频主题词），FTS5 BM25 排序 vs SpanKind 分类优先召回。

| 指标 | FTS 全文（现状） | 分类优先（SpanKind） |
|------|-----------------|-------------------|
| 8 条中执行上下文 | 4 条（50%） | 8 条（100%） |
| 8 条中工具噪音 | 4 条（50%） | 0 条（0%） |

FTS 前 4 条全是 `{"output": "..."}` 工具返回 JSON（DATA），分类优先后全部是
EXECUTED/ARGUMENT——决策性内容（"修复 matcher.py disable 过滤冗余代码"、"所有有 frontmatter
的技能都有了 disable 字段"）。

## 验证方法（Python，可复现）

```python
# 依赖: state.db (Hermes 本地会话数据库, 不需 venv)
import sqlite3, re

DB = os.path.expanduser("~/.hermes/state.db")
con = sqlite3.connect(DB)
rows = con.execute(
    "SELECT role, content, tool_calls FROM messages WHERE session_id=? ORDER BY timestamp",
    (sid,)).fetchall()

# 规则分类(同上)
COMMENT_MARKERS = ["好的", "明白", "收到", "继续", "稍等", "嗯"]
ARGUMENT_MARKERS = ["说明", "原因", "即", "也就是", "换句话说"]

def classify(role, content, tool_calls):
    if role == "tool": return "DATA"
    if role == "user": return "EXECUTED"
    if tool_calls and tool_calls not in ("[]", "", None): return "EXECUTED"
    if not content.strip(): return "DATA"
    if len(content) < 20 and any(content.startswith(m) for m in COMMENT_MARKERS): return "COMMENT"
    if any(m in content for m in ARGUMENT_MARKERS) and len(content) > 200: return "ARGUMENT"
    if re.search(r"```|def |function |import |SELECT |sudo |curl ", content): return "EXECUTED"
    return "ARGUMENT"

# 统计
kinds = Counter(classify(r, c, tc) for r, c, tc in rows)
for k, n in kinds.most_common():
    print(f"  {k}: {n} ({n/len(rows)*100:.1f}%)")
```

## 当前持久化状态

`~/.hermes/scripts/context-processor.py` 已用该规则分类最近 208 条消息（截至 2026-07-12）：
- EXECUTED：101（48.6%，保留比 1.0）
- DATA：96（46.2%，保留比 0.08）
- ARGUMENT：11（5.3%，保留比 0.2）
分布偏向 EXECUTED（近期消息含大量用户指令+assistant 决策），混合样本下平均省 46.7% token。
极端长 session 可达 75-83%。

## 能力边界

- Data 识别靠 `role=tool` 字段，该字段在 hermes-agent 的 state.db 中由消息循环写入，
  非 agent 侧构造，可靠。
- COMMENT 类实测为 0——该用户交互风格直接（"反馈阈值低、直接给方案"），其他用户可能有差异。
- 复杂边缘场景（如 tool 输出中混入决策性内容）未处理。需改进时优先加 LLM 二次校验。
