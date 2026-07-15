# 双压缩机制与钩子触发验证（2026-07-13 实测补充）

## 两套压缩互不通信（关键架构事实）

`~/.hermes` 里并存两套上下文压缩，触发条件、作用对象、产物消费全部独立：

| 维度 | context-processor.py（侧边钩子） | 系统 `compression:`（config.yaml） |
|------|----------------------------------|-----------------------------------|
| 触发点 | `config.yaml` 的 `hooks: post_tool_call:` 段，每次 terminal 调用后跑 | 核心 `context_compressor.py`，会话 token 达预算阈值时由核心就地触发 |
| 阈值 | hook 命令写死 `--min-tokens 10000 --min-messages 50`（**绝对 token 数**，非预算百分比） | `compression.threshold: 0.5`（预算 50%）→ 压到 `target_ratio: 0.2` |
| 产物 | 覆盖写 `~/.hermes/memories/compressed/<session_id>.md` | 核心就地压缩历史消息（进 system prompt） |
| 产物是否影响对话 | **否**——P3 读取端未闭环，无机制在对话里读该 .md | **是**——真正压缩你看到的上下文 |

> 误区纠正（2026-07-13）：用户曾以为"50% 触发 processor、低于 50% 不再触发、75% 系统兜底"。
> 实测：processor 按绝对 10000 token 触发，session 超线后**每次 terminal 都跑**，不是 50% 触发一次；
> 系统 `compression` 才是 50% 预算触发点；config 无 0.75（75% 可能是核心内部硬上限或记忆偏差）。
> 真实状态：**processor 一直在跑但只写不读，系统压缩兜底真正压缩对话**，两者压同一份 session、重复劳动。

## P3 读取端状态（截至 2026-07-13）

- 生成端 ✓：钩子真触发，`compressed/<sid>.md` 内容准确、时间新鲜（本轮实测 session 14:17 生成，内容首条即本轮开头）。
- 质量端 ✓：本轮实测 76.2% 压缩（74,019→17,713 token），91 条必保留消息指纹抽验 83/83 零遗漏。
- 读取端 ✗：**未闭环**。决定：用户确认保持现状（processor 落盘备用、系统兜底、P3 挂起）。
- 未来收口两路（均依赖 P3）：① 长会话优先读 `compressed/<sid>.md`；② 去重——关系统 compression 只用 processor+读取端。

## 验证钩子在当前会话是否真触发（三联交叉验证，可复用配方）

不要靠"config 里有 hooks 段"就断定生效。跑这三步，全绿才证明真触发：

```bash
SID=$(python3 -c "import sqlite3;print(sqlite3.connect('~/.hermes/state.db').execute('SELECT session_id FROM messages ORDER BY id DESC LIMIT 1').fetchone()[0])")

# ① 钩子是否接入 config（字段名/事件名/路径必须真实存在）
grep -nA2 'post_tool_call' ~/.hermes/config.yaml

# ② 当前 session 摘要产物: 时间新鲜 + 内容匹配该 session
ls -la --time-style=+%m-%d_%H:%M ~/.hermes/memories/compressed/$SID.md
head -c 400 ~/.hermes/memories/compressed/$SID.md

# ③ message_tags.db 覆盖当前 session 的消息范围(证实时自动打标,非快照)
python3 - << 'EOF'
import sqlite3, os
sid=os.environ['SID']
sc=sqlite3.connect('~/.hermes/state.db')
tc=sqlite3.connect('~/.hermes/scripts/message_tags.db')
rng=sc.execute("SELECT MIN(id),MAX(id) FROM messages WHERE session_id=?",(sid,)).fetchone()
covered=tc.execute("SELECT COUNT(*) FROM message_tags WHERE message_id BETWEEN ? AND ?",rng).fetchone()[0]
print(f"session {sid} msg范围 {rng}, 已打标 {covered}")
EOF
```

判定：① 有 `post_tool_call` 段 + ② .md 时间 ≈ 当前且内容首条是本会话 + ③ covered 覆盖当前 session 范围 → 钩子**真触发且实时**。三者任一缺失都要查根因（路径错/钩子未加载老 session/STATE_DB 指错库，见本 skill「地基级真因」）。

## 压缩收益 + 执行决策完整性验证（指纹抽验，防"压丢了关键决策"）

```bash
python3 - << 'EOF'
import sqlite3, os
sid=os.environ['SID']
sc=sqlite3.connect('~/.hermes/state.db')
tc=sqlite3.connect('~/.hermes/scripts/message_tags.db')
rng=sc.execute("SELECT MIN(id),MAX(id) FROM messages WHERE session_id=?",(sid,)).fetchone()
raw=sum(r[0] or 0 for r in sc.execute(
    "SELECT COALESCE(token_count,length(content)/3) FROM messages WHERE session_id=?",(sid,)))
summ=open(f'~/.hermes/memories/compressed/{sid}.md').read()
summ_tok=len(summ)//4
must=[r[0] for r in tc.execute(
    "SELECT message_id FROM message_tags WHERE message_id BETWEEN ? AND ? AND span_kind IN ('EXECUTED','ARGUMENT')",rng)]
missing=0
for mid in must:
    c=sc.execute("SELECT content FROM messages WHERE id=?",(mid,)).fetchone()[0] or ""
    fp="".join(c.split())[:25]
    if fp and fp not in "".join(summ.split()): missing+=1
print(f"原始 {raw:,} -> 摘要 {summ_tok:,} token  省 {(1-summ_tok/raw)*100:.1f}%")
print(f"必保留 {len(must)} 条, 遗漏 {missing} (0=执行决策完整)")
EOF
```

> 注：`message_tags.db` 是独立文件，连接用绝对路径 `~/.hermes/scripts/message_tags.db`，
> 勿用相对路径（并发写时偶发 `no such table` 是连接竞态，重试即可）。
> `count_session_tokens` 用 `COALESCE(token_count, length/3)`——tool 消息 token_count 常为空，DATA 类体积要用字符估算。
