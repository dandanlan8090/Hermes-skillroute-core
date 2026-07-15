---
name: hermes-context-compression
description: 对长对话上下文进行分类压缩（DATA/EXECUTED/ARGUMENT），保留 100% 执行决策， 压缩 75-83% 工具输出 token；历史检索时通过
  role_filter 优先返回 user/assistant 消息。 Use when token 敏感的长 session、上下文太长、压缩对话、历史检索全是工具输出、
  会话卡顿或长 session 管理。Not for 单轮短对话、需保留完整日志、调试模式看原始输出、审计合规场景。
version: 1.0.0
author: Hermes Agent
license: MIT
platforms:
- linux
- macos
- windows
metadata:
  hermes:
    tags:
      trigger:
      - token 太多
      - 上下文太长
      - 压缩对话
      - 历史检索全是工具输出
      - 会话卡顿
      - 长 session 管理
      - 上下文压缩
      - token 压缩
      - 对话历史压缩
      disable:
      - 单轮短对话
      - 保留完整日志
      - 调试模式
      - 审计合规
---
-

# Hermes Context Compression

## 第一性原理
长对话中 75-85% token 是工具原始输出（Data），只有 10-20% 是执行上下文（Executed）。
按语义类型分类后，Data 类可安全压缩，Executed 类必须 100% 保留。

范式来源：借鉴 dcg（Destructive Command Guard）的 SpanKind 命令上下文分类——
它把命令行切成 Executed/Data/Comment 等，分类的唯一目的是决定"是否影响结果"。
这里把同一范式上移到 Agent 长对话治理：分类轴是"这段上下文是否驱动执行"。

## 设计原则（迁移外部范式的通用纪律，来自本 skill 的诞生会话）
- 分析外部项目时，重其**架构/钩子关系**而非功能清单；借用的理念须用**真实数据验证**而非空谈。
- 向量/语义检索的天花板内，不靠**置信度加权/分数微调**去抢救召不回的 case
  （用户原话："置信度加权之类大可不必，允许命中失败是没问题的"）。
  正确方向是"进检索前的路由/分层"（如 SpanKind 上下文分类），不是改融合公式。
- 落到实现时优先在私有侧扩展（side table / 调用侧 `role_filter`），**不侵入核心代码**，
  符合 hermes-agent AGENTS.md 的"核心窄腰"约束。

## 落地实现（~/.hermes/scripts/）
| 文件 | 作用 |
|------|------|
| `init-context-tables.sql` | 创建 `message_tags.db` 私有 side table（不侵入 Hermes 核心） |
| `context-processor.py` | 规则分类最近 N 条消息 + 阈值自检 + 按 session 生成精简摘要。新增(2026-07-13): `ensure_schema()`, `get_current_session_id()`, `generate_summary()`, `--from-stdin` stdin JSON hook 入口, `--min-messages`/`--min-tokens` 阈值自检 |
| `vdb-autoload.py --process-context` | **仅手动 CLI 子命令**：`--auto` 或 `--process-context` 时跑一次 `process_context()`，**不是实时自动**。install.sh 没挂、agent 主循环没挂、无 cron → 对话期间不自动更新标签 |

分类映射（对齐 dcg SpanKind，可解释）：
- EXECUTED：user 指令/反馈 + assistant 工具调用意图 + 含代码/命令的产出 → 压缩比 1.0
- ARGUMENT：assistant 解释性长文本（含"说明/原因/即"等标记） → 压缩比 0.2
- DATA：tool 角色原始输出（命令结果/文件内容/API 返回） → 压缩比 0.08
- COMMENT：短确认/过渡（实测为 0，此用户交互风格直接给方案）

## 与 install.sh 的集成（⚠ 实测已证伪，见下方「真实架构缺口」）
**原 SKILL.md 声称**"`install.sh` 第 6.5 步自动建 `message_tags.db`、`--auto` 模式自动触发分类"——
这是**错的**。真实 `hermes-agent/scripts/install.sh` 里 grep 不到任何 `message_tags` / `context-processor` / `sqlite3` 建表语句（仅命中一个无关注释）。
`message_tags.db`（mtime 07-12 14:41）是**技能诞生会话里手动跑的**，不是安装自动。

## 真实架构缺口（2026-07-13 实测，分类器"做了一半"）
钩子本体**存在且能跑**：`vdb-autoload.py:81 def process_context()` → 调 `context-processor.py` 给最近 N 条消息打 EXECUTED/DATA/ARGUMENT 标签 → 写 `message_tags.db`。
但**停在「数据准备层」，从来没接进实时 context 路由**：

1. **接入点缺失**：`hermes-agent/plugins/context_engine/` 下**只有 `__init__.py` 发现器，没有任何引擎实现子目录**（无 `compressor/`、无 SpanKind 分类引擎）。预设方案从设计上就没有「可挂载引擎类」的落点。
2. **config 写死核心 compressor**：`config.yaml:412` `context: engine: compressor` 显式硬编码，指向核心内联的 `agent/context_compressor.py`（保护首尾轮+中间轮摘要）。它**全程不读 `message_tags.db`、不按分类决策、不调 `role_filter`**。
3. **自动触发缺失**：`process_context()` 只挂在 `vdb-autoload.py` 的 **CLI 子命令**上（`--process-context` 或 `--auto` 时手动跑一次）。`install.sh` 没挂、agent 实时路径（`agent_init.py` 主循环）没挂、无 cron/event hook。所以对话期间**不会自动更新标签**。
4. **消费端缺失**：核心 `context_compressor.py` 压缩时 grep 不到任何 `role_filter`/`message_tags`/`EXECUTED` 引用——它根本不知道预设方案的存在。反而是 `hermes_state.py:4763 search_messages` **确有 `role_filter` 参数**（4845-4980 行实现），但**当前没有任何引擎在压缩时自动传它**。

→ 旧结论（2026-07-13 上午）曾判"钩子空中楼阁、message_tags.db 是 07-12 快照 0 条新写入"——**已被同日实测推翻**：修好 `STATE_DB` 路径后，钩子经 `config.yaml` 的 `hooks: post_tool_call` 段**真在实时跑**，当前 session 实测新增 160 条标签（覆盖完整 message_id 范围）、`compressed/<sid>.md` 14:17 新鲜生成且内容首条即本会话开头。
**修正后的真因**：钩子"做了分类器 + 自动触发"已生效，卡在**最后一步「消费端 / 读取端」未接**——生成的 `compressed/<sid>.md` 没有任何机制在对话里被读取，所以产物对当前对话**零影响**，系统 `compression` 才是真正压缩对话的那套（见下方「双压缩架构」）。这仍是"缺失的一环"，但性质从"空中楼阁"修正为"写了不读"。

> **P3 已于 2026-07-14 收口（不再是悬空项）**：SOUL.md 新增**铁律#7（长对话上下文管理）**，将 `compressed/<sid>.md` 从"落盘备用"变为"条件触发读取"——仅在会话 > 50 条 **且** 用户明确回指历史 **且** 无进行中历史检索时，才加载该摘要作"已发生事实精简回收"，且只取 `[EXECUTED]`/`[ARGUMENT]` 段、校验作用域；`context-processor.py` 的 `generate_summary()` 写入 `<!-- generated_at=ISO8601 last_message_id=N -->` + `<!-- 本摘要仅适用于会话 <sid> (scope=current_session_only) -->` 元数据。初版"每轮全量加载"暴露 83KB 膨胀源后，当日修订为"条件触发 + 过滤加载"（详见下方「铁律#7 读取端闭环」）。

### 地基级真因（2026-07-13 钉死，比「缺口」更底层）
`context-processor.py` 的 `STATE_DB` 常量**指向错误路径**：
- 真实有数据的库是**顶层 `~/.hermes/state.db`**（11942 条消息、113 个 session，标准 sqlite 可读，`messages` 表字段完整）。
- `hermes-agent/state.db` 是 **0 字节空文件** —— 脚本 `STATE_DB = os.path.join(HERMES_HOME, "hermes-agent", "state.db")` 连的是它。
- 后果：`process_recent()` 从空库读消息 → 分类的"来源"是哑的；`message_tags.db` 的 410 条标签**关联的是旧库/错库的 id**，与真实 `state.db` 的 id 体系**对不上**（真实最大 id=12013，tags 最大 id=11093）。
- 这解释了"钩子存在但像没接"：钩子本体（`vdb-autoload.py:81 process_context()`）能跑、能写 tags，但它读的消息源是空库 → 标签永远是 07-12 那次手动跑的快照，实时对话不产生新标签。
- **修复**（零侵入核心，只改自己脚本）：把 `STATE_DB` 指向 `~/.hermes/state.db`；清空 `message_tags.db` 旧数据后用修好的库重跑 `process_recent` 重新对齐 id。详见 `references/integration-pitfalls.md`。

## 接入纪律（2026-07-13 用户明确 frustration 驱动 + 本次闭环验证）
用户原话："你弄错了我们所要面对的重点，ppt 只是一个解说，可以放一边去，先不讨论，重点是我们当前做的微型框架没有按照预想方向运行" + "基于结果的行动路径：先确认钩子事实（config/源码）再写代码" + "翻一下先确认事实"。

下沉为**不依赖本技能的通用纪律**（任何"接外部钩子 / 改自己脚本接框架"任务都适用）：
1. **产物 vs 根因分离**：用户给的 PPT/文档/演示是解说产物，根因修复优先于打磨产物。用户说"放一边"时，立刻停手产物、转查框架为何没按预想运行。
2. **不深入核心、避免更新后失效**：改"自己散落在 `scripts/` 的脚本"或"外部钩子（config 的 `hooks:`）"可以；**不要**改 `hermes-agent/` 核心代码（agent_init.py / context_compressor.py / plugins/context_engine/ 内部）。核心随版本变，侵入式改必在更新后失效。
3. **先验证机制真实存在，再抄用户给的 YAML/命令**：用户给的提案格式**常错**（本轮给的 `Hooks:/Post_tool_call:/Command:` 全大写，本机 `cli-config.yaml` 根本无 `hooks:` 加载点；真实是 `cli-config.yaml` 的 `hooks:` 小写段 + `post_tool_call:` 事件 + 插件 `ctx.register_hook("post_tool_call", ...)`）。**照抄提案 = 造死配置**。正确：先 `grep` 源码确认字段名/事件名/路径，再写。
4. **怀疑即查，不靠记忆/推测下结论**：本轮我**误判两次**——先说"预设没接、空中楼阁"，后说"钩子没接"；最终 `find`/`sqlite3` 一查才发现：钩子本体存在（`vdb-autoload.py:81 process_context()`），只是 `STATE_DB` 路径常量指错空库。**凡下"没接/没生效/是空中楼阁"类结论前，必须 sqlite/文件级复现**，否则是假阴性。
5. **config 落点要钉死**：用户说"改 config.yaml 加 hooks"——本机 hooks 实际读 `cli-config.yaml`（非 `config.yaml`，后者只有 `hooks_auto_accept`）；且 `cli-config.yaml` 本机**不存在**（只有 `.example`）。落错文件 = 不生效。

### 本次闭环验证的设计范式（2026-07-13）
本 session 将「不深入核心」约束落实为可复用的**外部钩子架构**：
1. **触发层**：`config.yaml` 的 `hooks: post_tool_call:` 段——纯外部配置，不侵入 agent 核心循环。触发时 payload 以 **JSON 写进 stdin**（`_serialize_payload`，含 `tool_name`/`session_id`/`args`），不是传统 `{var}` 字符串插值。
2. **处理层**：`context-processor.py` 通过 `--from-stdin` 分支读 stdin JSON 取 `session_id`，走阈值自检（`--min-messages`/`--min-tokens`，不达标秒退），达标则分类 + 写 `message_tags.db`。
3. **消费层**：`generate_summary(session_id)` 写 `~/.hermes/memories/compressed/${session_id}.md`——外部摘要文件，留给 SOUL.md 铁律引用（Agent 启动轮次前 `cat` 该文件注入"已发生事实"）。
4. **安全护栏**：agent **不能直写 config.yaml**（`Refusing to write to Hermes config file`），必须告知用户手动追加。不绕护栏、不走 `hermes config set`。

这套范式的价值：**触发/处理/消费三层均不碰 Hermes 核心**（不改 `agent/`、不碰 `plugins/`、不改 `config.engine`），任何核心版本更新都不影响外部钩子和独立脚本的运转。

> 上述验证命令与路径真相见 `references/integration-pitfalls.md`。

## 双压缩架构（2026-07-13 下午实测，易踩的认知坑）
`~/.hermes` 里**两套压缩并存、互不通信**，作用对象与产物消费完全独立：

| 维度 | context-processor.py（侧边钩子） | 系统 `compression:`（config.yaml） |
|------|----------------------------------|-----------------------------------|
| 触发 | `hooks: post_tool_call:` 每次 terminal 后跑 | 核心 `context_compressor.py` 在会话达预算阈值时就地触发 |
| 阈值 | hook 命令写死 `--min-tokens 10000 --min-messages 50`（**绝对 token**，非预算%） | `compression.threshold: 0.5`（预算 50%）→ 压到 `target_ratio: 0.2` |
| 产物 | 覆盖写 `memories/compressed/<sid>.md` | 核心就地压缩历史消息（进 system prompt） |
| 影响对话? | **2026-07-14 起：是**——SOUL.md 铁律#7 强制 >50 条消息时加载该 .md 回收事实（详见「铁律#7 读取端闭环」）。此前 P3 未闭环时为「否」 | **是**——真正压缩你看到的上下文 |

⚠ **误区纠正**：用户曾以为"50% 触发 processor、低于 50% 不再触发、75% 系统兜底"。实测：processor 按**绝对 10000 token** 触发，session 超线后每次 terminal 都跑，不是 50% 触发一次；系统 `compression` 才是 50% 预算触发点；config 无 0.75（75% 可能是核心内部硬上限或记忆偏差）。真实状态：**processor 一直在跑但只写不读，系统压缩兜底真正压缩对话**，两者压同一份 session、重复劳动。
**决定（2026-07-13）**：保持现状——processor 落盘备用、系统兜底、P3 挂起等验证。验证配方见 `references/dual-compression-verification.md`。

## 铁律#7 读取端闭环（2026-07-14 收口 + 当日修订）

此前 P3 "写了不读"已反转：SOUL.md 新增**铁律#7（长对话上下文管理）**，把 `compressed/<sid>.md` 从"落盘备用"变成"条件触发读取"。

**铁律#7 修订版内容要点**（已写入 SOUL.md，位于铁律#0 之后）：

触发条件（**必须同时满足**）：
1. 会话消息数 > 50 条。
2. **且** 当前用户输入明确回指历史（"之前提到的" / "根据刚才讨论" / "回到 X 问题" / "上次那个"等）。
3. **且** 当前无进行中的 `session_search` 或其他历史检索操作（避免重复加载）。

执行动作：
- 检查 `~/.hermes/memories/compressed/${session_id}.md` 是否存在，且头部作用域声明 `本摘要仅适用于会话 <session_id>` 与当前 session_id 一致（scope=current_session_only）。
- 存在且作用域匹配 → `cat` 该文件，但**仅提取 `[EXECUTED]` 和 `[ARGUMENT]` 段**，忽略 `[DATA]` 段（工具输出密度低且可能含嵌套历史压缩块）。
- 不存在 / 作用域不匹配 / 过期（`generated_at` 早于最新消息时间，或 `last_message_id` < state.db 该 session 最新 id） → 跳过加载，回退读 state.db 最近 N 条原始消息。

禁止行为：
- ❌ 每轮无条件加载摘要文件（仅当用户明确回指历史且满足全部触发条件才加载）。
- ❌ 加载包含其他 session 压缩块的摘要文件（仅限当前会话作用域）。
- ❌ 加载摘要的 `[DATA]` 段（只取执行决策与讨论总结）。

**支撑改动**：
- `generate_summary()` 头部写入三行元数据：
  ```
  # 会话 <sid> 精简上下文 (生成于 <ts>)
  <!-- generated_at=<iso8601> last_message_id=<N> -->
  <!-- 本摘要仅适用于会话 <sid> (scope=current_session_only) -->
  ```
- `last_mid=max(mid)` 循环追踪，`ts` 用 `datetime.now().isoformat(timespec="seconds")`。

**演进（2026-07-14 当日两次修订）**：
- 初版（上午）：>50 条即每轮加载全量摘要 → 实测暴露 83KB 摘要反成 token 膨胀源（DATA 段含嵌套 `[CONTEXT COMPACTION]` 块）。
- 修订版（当日）：改为**条件触发（用户回指历史）+ 过滤加载（只取 EXEC/ARG）+ 作用域隔离**，彻底规避膨胀源。验证：重新生成摘要头部三行元数据齐全，模拟过滤加载确认只定位 EXEC/ARG 段、剥离 DATA、作用域声明可解析。

**调用方式修正**：`--session` 不是 argparse 定义参数，必须
`echo '{"session_id":"<sid>"}' | python3 context-processor.py --summary --from-stdin`，
否则 sid 被当成位置参数 `n` 报错。

## 验证方法（复现本轮查证，防止再误判"已接"）
```bash
# 1. config 实际启用的引擎
grep -n 'engine:' ~/.hermes/config.yaml          # 应见 context: engine: compressor
# 2. context_engine 插件目录是否真有引擎实现
find ~/.hermes/hermes-agent/plugins/context_engine -maxdepth 2   # 若只有 __init__.py = 无挂载点
# 3. install.sh 是否真有建表/触发调用（证伪"自动"）
grep -niE 'message_tags|context-processor|--process-context' ~/.hermes/hermes-agent/scripts/install.sh
# 4. 标签库是否随本轮对话更新（区分"手动跑过" vs "实时自动"）
ls -la --time-style=+%m-%d_%H:%M ~/.hermes/scripts/message_tags.db
python3 -c "import sqlite3;c=sqlite3.connect('~/.hermes/scripts/message_tags.db');print(c.execute('SELECT MIN(processed_at),MAX(processed_at) FROM message_tags').fetchone())"
# 5. 核心 compressor 是否消费标签（应为空 = 未接）
grep -niE 'role_filter|message_tags|EXECUTED' ~/.hermes/hermes-agent/agent/context_compressor.py
```
**判定标准**：第 2 步 `find` 只有 `__init__.py` + 第 3 步 grep 无输出 = 钩子存在但**未接入实时路由**（空中楼阁），不要误判为"已按预想架构运行"。

## 权威验证命令：`hermes hooks test`（2026-07-13 本轮发现）
验证 hook 配置是否真实可触发，**用官方测试命令而非手猜**：
```bash
# 用真实 session_id 触发（production 等价 stdin，非 test-session 合成）
echo "{\"session_id\":\"$(python3 -c "import sqlite3;print(sqlite3.connect('~/.hermes/state.db').execute('SELECT session_id FROM messages ORDER BY id DESC LIMIT 1').fetchone()[0])")\"}" > /tmp/hook_payload.json
hermes hooks test post_tool_call --for-tool terminal --payload-file /tmp/hook_payload.json
```
- `run_once` 经 `_spawn` 真实执行，stdin JSON 与 production **完全一致**（源码注释明说否则测试会和生产行为悄悄偏离）。
- exit=0 + stdout 见 `阈值达标 / 处理完成 / 摘要已写` = 配置正确、脚本链路通。
- ⚠️ 但 `hermes hooks test` 通过 **≠** 运行中老 session 会自动触发：钩子注册在进程启动时，改 config 前已启动的 session 没加载新 `hooks:` 段。看真实自动刷新必须**开新 session** 用 terminal 工具（详见 `references/integration-pitfalls.md` §7）。

## 调用侧优先检索约定（接口就绪但**当前无人自动消费**）
`hermes_state.py` 的 `search_messages` **确有 `role_filter` 参数**（4763 行定义，4845-4980 行实现），传 `role_filter=["user","assistant"]` 可排除 tool（DATA 类）。
⚠ **但当前没有任何引擎在压缩时自动传它**——`config.engine: compressor` 跑核心 `context_compressor.py`，其全程不读 `message_tags.db`、不调 `role_filter`。所以这是「可用未接」状态，不是「已生效」。
符合铁律#5（改进优先于新增）的**目标**是：在私有侧用 `role_filter` 扩展，不侵入核心。但**实际落地还差「压缩前钩子调 process_context + 压缩时读 message_tags 用 role_filter」这步**——见上方「真实架构缺口」。

也可直接用 `context-processor.py --demo <关键词>` 做分类优先检索演示
（先召回 EXECUTED/ARGUMENT，不足再用 DATA 补足）。

## 真实验证数据（两个长 session，state.db 实测）
| 指标 | 结果 |
|------|------|
| Data 类占比 | 75.5% / 85.4% |
| 分类压缩节省 | 74.1% / 83.0% |
| 历史检索命中执行决策率 | FTS 50% → 分类优先 100% |
| 执行上下文保留 | 100%（EXECUTED 压缩比 1.0） |

当前已分类 208 条消息：EXECUTED 101（保留比 1.0），DATA 96（保留比 0.08），
ARGUMENT 11（保留比 0.2）。平均省 46.7% token（混合近期消息，Data 占比低于极端长 session）。

## 能力边界
- 当前分类靠规则（`role=tool` → DATA），在实测 session 中准确率足够。
  `COMMENT` 类实测为 0（符合此用户"反馈阈值低、直接给方案"的交互风格）。
- 真实价值集中在"Data 识别"这一刀，不夸大四分类全上。
- 复杂边缘场景（如 tool 输出中混入决策性内容）暂不处理，后续可引入轻量 LLM 二次校验。

> 完整真实验证报告（session 元数据、分布明细、复现脚本）见 `references/empirical-validation.md`。
> 同源的语义检索召回失败诊断方法（vdb 索引完整性 vs 融合错误的判定，2026-07-12）见 `references/vdb-recall-diagnostics.md`。
> 双压缩架构 + 钩子是否真触发 + 压缩收益验证配方（2026-07-13 下午实测）见 `references/dual-compression-verification.md`。
> **P3 收口（铁律#7 读取端闭环）+ 摘要反成 token 膨胀源的新坑 + 调用方式修正**见 `references/read-loop-closed-2026-07-14.md`。

## 触发方式

### 手动触发
```bash
# 处理最近 50 条
python3 ~/.hermes/scripts/context-processor.py 50

# 查看分类统计
python3 ~/.hermes/scripts/context-processor.py --stats

# 演示分类优先检索
python3 ~/.hermes/scripts/context-processor.py --demo disable

# 阈值自检 + 分类 + 生成 session 摘要 (不达标自动跳过)
python3 ~/.hermes/scripts/context-processor.py 200 --min-messages 50 --min-tokens 10000 --summary --session <session_id>

# 随 vdb 自动触发（--auto 模式已包含 --process-context）
python3 ~/.hermes/scripts/vdb-autoload.py --auto
```

### post_tool_call 自动触发 (config.yaml hooks: 段)
```yaml
# 加在 ~/.hermes/config.yaml 末尾
hooks:
  post_tool_call:
    - matcher: "terminal"
      command: "python3 ~/.hermes/scripts/context-processor.py 200 --min-messages 50 --min-tokens 10000 --summary --from-stdin"
```
- **不侵入 Hermes 核心**：纯外部钩子 + 独立脚本。
- **阈值自检不依赖 hook**：每次跑前脚本先查 `session_id` 的消息数和估算 token，不达标直接退出（0.01s 级开销）。
- **打标 + 摘要**：达标则分类 + 写 `~/.hermes/memories/compressed/${session_id}.md`。
- **双保险**：`--from-stdin` 优先取 stdin JSON payload 的 `session_id`；若没有则脚本自己从 `state.db` 取最近消息的 session。

⚠ **安全护栏**：agent 不能直写 `config.yaml`（hermes 护栏），需**手动**编辑 `~/.hermes/config.yaml` 追加上述 `hooks:` 段。不绕护栏、不走 `hermes config set`（嵌套 list 不好拼）。

## 后续进化方向（未实现，记录待用）
- 轻量 LLM 二次校验：规则分类在复杂场景不够准时，用极小模型（如 hermes-2-pro）做二次校验。
- 语义压缩：对 DATA 类内容，除截断外用 vdb 做语义摘要（保留关键信息）。
- 与 vdb 技能检索联动：检索历史时优先展示 EXECUTED 决策点，并自动关联当时触发的 skill，
  形成"决策-执行"链路。
