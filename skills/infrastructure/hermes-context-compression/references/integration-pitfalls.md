# 接入陷阱与事实真相（2026-07-13 实测）

本文件承载 hermes-context-compression 技能「真实架构缺口 /
地基级真因 / 接入纪律」里提到的**具体复现命令、路径真相、
钩子真实格式**。SKILL.md 讲原则，这里给可照抄的探针。

## 0. 真实路径真相（先读这个，否则全错）
- **真实消息库**：`~/.hermes/state.db`（标准 sqlite，11942 条消息，
  113 个 session，`messages` 表字段含 `id/session_id/role/content/
  tool_calls/timestamp/token_count/compressed`）。
- **坑**：`~/.hermes/hermes-agent/state.db` 是 **0 字节空文件**。
  `context-processor.py` 的 `STATE_DB` 常量若指向它，读到的全是哑的。
- **标签库**：`~/.hermes/scripts/message_tags.db`（私有 side table，
  `message_tags` 表：`message_id/span_kind/confidence/compress_ratio/
  reason/processed_at`）。
- **id 体系错位**：真实库最大 id=12013，tags 库最大 id=11093
  → 两者**不是同一套 id**。tags 库的 410 条是 07-12 某次手动跑
  时关联旧库留下的快照，和当前真实消息接不上。
- **结论**：要让分类真正生效，必须 (a) `STATE_DB` 改指顶层
  `~/.hermes/state.db`；(b) 清空 `message_tags.db` 旧数据后用修好的库重跑。

## 1. 验证「钩子存不存在 / 接没接」（防误判"空中楼阁"）
```bash
# 1. config 实际启用的引擎（硬编码值，非 auto 推导）
grep -n 'engine:' ~/.hermes/config.yaml        # 应见 context: engine: compressor

# 2. context_engine 插件目录是否真有引擎实现
find ~/.hermes/hermes-agent/plugins/context_engine -maxdepth 2
# 若只有 __init__.py = 无挂载点，预设方案没做成可挂引擎

# 3. install.sh 是否真有建表/触发调用（证伪"自动"）
grep -niE 'message_tags|context-processor|--process-context' \
     ~/.hermes/hermes-agent/scripts/install.sh
# 空输出 = install 没接，标签库是手动跑的

# 4. 标签库是否随本轮对话更新（区分"手动跑过" vs "实时自动"）
ls -la --time-style=+%m-%d_%H:%M ~/.hermes/scripts/message_tags.db
python3 -c "import sqlite3;c=sqlite3.connect('~/.hermes/scripts/message_tags.db');print(c.execute('SELECT MIN(processed_at),MAX(processed_at),COUNT(*) FROM message_tags').fetchone())"
# 若 MAX(processed_at) 是昨天、今天 0 条 = 钩子没实时跑

# 5. 核心 compressor 是否消费标签（应为空 = 未接）
grep -niE 'role_filter|message_tags|EXECUTED|ARGUMENT' \
     ~/.hermes/hermes-agent/agent/context_compressor.py
```

## 2. post_tool_call 钩子的真实格式（用户给的大写 YAML 是错的）
```yaml
# ~/.hermes/cli-config.yaml  —— 注意本机 cli-config.yaml 可能不存在，只有 .example
# 真实段名全小写，事件是 post_tool_call（不是 Post_tool_call / Hooks / Command 大写）
hooks:
  post_tool_call:
    - matcher: "terminal"
      command: "python3 ~/.hermes/scripts/context-processor.py 1"
```
- 触发时 payload（`shell_hooks.py:_serialize_payload` 537-556 行）以 **JSON 写进 command 的 stdin**，
  含 `session_id`（= `kwargs.get("session_id") or kwargs.get("parent_session_id")`）。
  命令里可用 `{session_id}` 占位符插值。
  ⚠️ 修正：实际是 stdin JSON，不是字符串插值。脚本必须自己 sys.stdin.read() 解析 JSON 取 session_id（见 context-processor.py 的 --from-stdin 分支）。
- `matcher: "terminal"` 匹配终端工具调用（工具真名是 `terminal`，
  在 `tools/code_execution_tool.py:69` 注册）。
- ⚠️ 本机 `cli-config.yaml` **不存在**（只有 `cli-config.yaml.example`）；
  `config.yaml` 里只有 `hooks_auto_accept: false`，**没有 `hooks:` 段**。
  落错文件 = 钩子不触发。

## 3. 钩子本体（确实存在，但停在离线层）
`~/.hermes/scripts/vdb-autoload.py:81` 的 `process_context()`：
- 调 `context-processor.py` 给最近 N 条消息打 EXECUTED/DATA/ARGUMENT 标签。
- 只挂在 **CLI 子命令** 上（`--process-context` 或 `--auto` 时跑一次），
  **不是**实时对话路径上的自动钩子。
- 调用：`python3 ~/.hermes/scripts/vdb-autoload.py --process-context`
  或 `--auto`（含过期检测 + 预热 + 分类）。

## 4. context-processor.py 当前能力边界
- `process_recent(n=50)`：只**打标签**（写 message_tags.db），
  **不产生压缩后上下文**。传 `1` = 只扫最近 1 条未打标的。
- 缺三块才闭环：`get_current_session_id()` / 阈值自检
  (`--min-messages`/`--min-tokens`) / `generate_summary(session_id)`
  （按标签聚合写 `~/.hermes/memories/compressed/${session_id}.md`）。
- 这些应是**纯新增函数**，不改现有 `classify`/`process_recent`，
  符合"不侵入核心"约束。

## 5. 用户给定的推进顺序（已验证合理）
1. 先用临时 hook 命令（`echo test > /tmp/hook_triggered`）验证
   `post_tool_call` 能触发、能拿到 `session_id`。
2. 给 `context-processor.py` 加 `get_current_session_id()` +
   阈值自检 + `generate_summary()`（纯新增）。
3. 脚本能力完备后，才把 `hooks.post_tool_call.command` 指向它
   （落点必须是真实存在的 `cli-config.yaml`，不是 `config.yaml`）。
4. SOUL.md 加铁律引用压缩摘要。

**核心纪律**：凡下"没接 / 空中楼阁 / 没生效"类结论前，
必须 sqlite/文件级复现（见 §1），否则是假阴性——
本轮曾误判两次，最终发现钩子本体存在、只是 `STATE_DB` 路径常量指错空库。

---

## 6. 2026-07-13 修复补丁：STATE_DB 路径 + 脚本补全 + hook 接入

### 6.1 地基 bug 定位
- 真实消息库：**`~/.hermes/state.db`**（标准 sqlite，11942 条消息，113 session）
- 空库陷阱：`hermes-agent/state.db` 是 **0 字节空文件**
- 脚本原指向：`STATE_DB = os.path.join(HERMES_HOME, "hermes-agent", "state.db")` → **错**
- 修后：`STATE_DB = os.path.join(HERMES_HOME, "state.db")` → 正
- 后果：脚本连空库跑分类，标签 id（最大 11093）与真实库 id（最大 12013）**错位**
- 修复操：改常量 + `rm message_tags.db` + 重跑 `context-processor.py 200` → 标签重建且 id 对齐

### 6.2 脚本新增函数（纯新增，不改现有 classify/process_recent）
| 函数 | 作用 |
|------|------|
| `ensure_schema()` | 幂等建 `message_tags` 表（原脚本靠预存表，清库就崩） |
| `get_current_session_id()` | 从 state.db 取最近消息的 session_id（双保险，hook 不传也能跑） |
| `count_session_tokens()` | 按 session 估算总 token（CHAR/3 近似） |
| `generate_summary(session_id)` | 写 `~/.hermes/memories/compressed/${session_id}.md`（EXEC/ARG 完整 + DATA 按比截断） |

### 6.3 新参数入口
```bash
# 阈值自检：不达标直接跳过（--min-messages, --min-tokens）
python3 context-processor.py 200 --min-messages 50 --min-tokens 10000 --summary

# post_tool_call hook 触发：从 stdin 读 JSON payload 取 session_id
echo '{"tool_name":"terminal","session_id":"xxx"}' | \
  python3 context-processor.py 200 --min-messages 50 --min-tokens 10000 --summary --from-stdin
```

### 6.4 config.yaml 钩子（### 护栏阻挡，需手动追加 ###）
```yaml
# 加在 ~/.hermes/config.yaml 末尾
hooks:
  post_tool_call:
    - matcher: "terminal"
      command: "python3 ~/.hermes/scripts/context-processor.py 200 --min-messages 50 --min-tokens 10000 --summary --from-stdin"
```
agent **不能**直写 config.yaml（`hermes` 安全护栏报 `Refusing to write to Hermes config file`），必须手动 `vim ~/.hermes/config.yaml` 追加。不绕护栏、不走 `hermes config set`（嵌套 list 不好拼）。

### 6.5 验证命令
```bash
# 验证状态
python3 ~/.hermes/scripts/context-processor.py --stats

# 模拟 hook 触发
echo '{"tool_name":"terminal","session_id":"20260713_090712_a22f6a"}' | \
  python3 ~/.hermes/scripts/context-processor.py 200 --min-messages 50 --min-tokens 10000 --summary --from-stdin

# 检查摘要
ls -la ~/.hermes/memories/compressed/
cat ~/.hermes/memories/compressed/$(python3 -c "import sqlite3;print(sqlite3.connect('~/.hermes/state.db').execute('SELECT session_id FROM messages ORDER BY id DESC LIMIT 1').fetchone()[0])").md | head -10
```

## 7. ⚠ 关键陷阱：`hermes hooks test` 通过 ≠ 实时自动触发
（2026-07-13 本轮真实踩到的坑）

`hermes hooks test post_tool_call --for-tool terminal --payload-file x.json` 是**独立 CLI 进程**，
直接读 `config.yaml` 的 `hooks:` 段跑一遍，exit=0 只能证明：
1. YAML 格式正确、能被 `shell_hooks` 解析；
2. command 能被 `_spawn` 真实执行；
3. stdin JSON payload 路由正确（脚本拿到 session_id）。

它**不能证明**正在运行的 agent 主循环会自动触发该 hook。原因：
- 钩子注册发生在 **Hermes 进程启动时**（`register_from_config` 加载 config）。
- **改 config.yaml 之前就已启动的 session，其运行中的进程根本没加载新 `hooks:` 段** —— 钩子注册表是空的。
- 所以你会看到：`hermes hooks test` 跑通了、摘要文件也被它刷新（合成触发），
  但你在老 session 里正常用 terminal 工具，摘要 mtime 不更新 → 误以为"钩子没接"。

判定 + 解法：
- 验证真实触发路径：开一个**新的对话 / 新 session**，再用 terminal 工具，观察
  `~/.hermes/memories/compressed/<newsid>.md` 的 mtime 是否随每次 terminal 调用自动刷新。
- 或者用真实 payload 文件走 `hermes hooks test`（已验证等价 production stdin）：
  ```bash
  echo "{\"session_id\":\"$(python3 -c "import sqlite3;print(sqlite3.connect('~/.hermes/state.db').execute('SELECT session_id FROM messages ORDER BY id DESC LIMIT 1').fetchone()[0])")\"}" > /tmp/hook_payload.json
  hermes hooks test post_tool_call --for-tool terminal --payload-file /tmp/hook_payload.json
  ```
- 注意：每次 `hermes hooks test` 触发会跑真实分类+摘要（生产等价），可放心用它做真实数据验证；
  但**观察"自动刷新"必须靠新 session 的真实工具调用**，test 命令本身不算自动触发。

> 对应 SKILL.md「真实架构缺口」的修正：本项目已**从"空中楼阁"转为真实接入**——
> 地基 bug（STATE_DB 空库路径 + id 错位）已修、脚本能力已补全、config 已加 hooks 段。
> 剩余唯一待观察项：真实长对话中每次 terminal 调用自动刷新摘要的效果（铁律 #7 尚未写 SOUL.md）。
