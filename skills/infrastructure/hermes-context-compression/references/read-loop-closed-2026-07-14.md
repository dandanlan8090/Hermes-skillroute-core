# 铁律#7 读取端闭环 + 摘要膨胀坑（2026-07-14 实测收口）

## 背景
hermes-context-compression 长期悬空 P3：context-processor.py 生成的
`memories/compressed/<sid>.md` "写了不读"。2026-07-14 用户正式决定收口 P3
（此前 7/13 约定维持现状，本次反转）。

## 收口落地（已改两处文件）
1. **SOUL.md 新增铁律#7（长对话上下文管理）**：位于铁律#0 之后，内容为
   会话消息 > 50 条时，任何新工具/推理前必须先做上下文回收：
   - 检查 `~/.hermes/memories/compressed/${session_id}.md` 是否存在
     （session_id 取 state.db 当前活跃 session 的最后一条 message 的 session_id）
   - **新鲜度检查**：解析摘要第 2 行 `<!-- generated_at=ISO8601 last_message_id=N -->`
     - generated_at 与当前差 > 5 分钟 → 过期，忽略摘要，回退读原始消息
     - last_message_id < state.db 该 session 最新 id → 过期（摘要后又有新消息），回退
   - 文件存在且新鲜 → 加载作"已发生事实的精简摘要"基底
   - 不存在/过期 → 回退读 state.db 原始消息最新若干条
   → 细则 `skill_view(name='hermes-context-compression')`

2. **context-processor.py generate_summary() 加元数据**：在标题行后写入
   `<!-- generated_at=<iso8601> last_message_id=<N> -->`，供铁律#7 解析。
   实现：循环里追 `last_mid = max(last_mid, mid)`，ts 用
   `datetime.now().isoformat(timespec="seconds")`。
   ⚠ 调用方式：`--session` 不是 argparse 定义的参数，必须用
   `echo '{"session_id":"<sid>"}' | python3 context-processor.py --summary --from-stdin`
   （直接 `python3 context-processor.py <sid> --summary` 会把 sid 当成位置参数 n 报错）。

## ⚠ 真实新坑：摘要反成 token 膨胀源（收口后必须处理）
收口后发现当前 session 的 `compressed/<sid>.md` **83KB**，且 DATA 摘要段
**嵌套了来自其他 session 的完整 `[CONTEXT COMPACTION]` 压缩块**（经
session_search 结果带入）。后果：铁律#7 每轮 cat 该文件 = 在已有上下文外
**再加 83KB**，比不读还费 token，违背压缩初衷。

根因：DATA 截断比 0.08 对超大 tool 输出仍太大（8% of 几十 KB = 数 KB），
且未剔除嵌套压缩块/超长转义串。

**建议后续在 generate_summary() 内修**：
- DATA 压缩比从 0.08 降到 ~0.02，并对单条 keep 加硬上限（如 400 字符）
- 生成时跳过内容含 `[CONTEXT COMPACTION]` / `PRIOR CONTEXT` 的 tool 消息
  （这类是别的 session 的压缩遗产，非本 session 事实）
- 或铁律#7 加"摘要 > 20KB 则只加载 EXECUTED/ARGUMENT 段（前 1/3），跳过 DATA 段"

> 注：本 reference 创建时 SKILL.md 正文的"P3 未闭环/写了不读"描述已过时，
> 待 curator 用 skill_manage patch 将那句改为"P3 已收口（见本文件）"。

## 验证配方（收口后自查）
```bash
# 1. 重新生成当前 session 摘要（带元数据）
SID=$(python3 -c "import sqlite3;print(sqlite3.connect('~/.hermes/state.db').execute('SELECT session_id FROM messages ORDER BY id DESC LIMIT 1').fetchone()[0])")
echo "{\"session_id\": \"$SID\"}" | python3 ~/.hermes/scripts/context-processor.py --min-messages 1 --min-tokens 1 --summary --from-stdin
# 2. 看第 2 行元数据
sed -n '2p' ~/.hermes/memories/compressed/$SID.md
# 3. 新鲜度解析（铁律#7 的等价逻辑）
python3 -c "
import re
p='~/.hermes/memories/compressed/$SID.md'
l=open(p).read().split('\n')[1]
m=re.search(r'generated_at=([^ ]+) last_message_id=(\d+)', l)
print('parsed:', m.group(1), m.group(2)) if m else print('NO META')
"
```
