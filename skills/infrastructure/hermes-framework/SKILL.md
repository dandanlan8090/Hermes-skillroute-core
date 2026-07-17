---
name: hermes-framework
description: >-
  Hermes 微内核框架的 CLASS-LEVEL 总纲：架构（文件结构/加载机制/铁律/4层召回）、
  配置文件加载与 profile、框架演进（新增铁律/skill/路由的安全流程）、变更日志规范、
  框架自身故障诊断与回滚、system prompt 微内核优化（SOUL.md 瘦身/技能抽取）、
  自身进化规则（改进优先于新增/增量变更/验证/持久化边界）。
  触发：框架架构/设计/故障、加载顺序/SOUL.md/USER.md/MEMORY.md/profile、
  vdb不工作/skill加载失败/召回不准/铁律失效、新增或扩展规则或skill、
  变更日志/框架审计、system prompt优化/SOUL.md精简/降低token消耗/微内核。
  禁用：日常任务执行、用户业务代码变更、不涉及框架的普通查询。
version: 2.0.0
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
        - 框架架构
        - 框架设计
        - 文件结构
        - 加载机制
        - 框架故障
        - 框架原理
        - 系统设计
        - 修改框架
        - 架构优化
        - 重构框架
        - 加载顺序
        - SOUL.md加载
        - 框架文件
        - profile切换
        - system prompt
        - 配置文件
        - 新增铁律
        - 新增规则
        - 创建约束
        - 新增skill
        - 修改方法
        - 框架演进
        - 路由表更新
        - 扩展框架
        - 变更日志
        - 框架历史
        - 回溯变更
        - 框架审计
        - vdb不工作
        - skill加载失败
        - 索引过期
        - 召回不准
        - 铁律失效
        - is_healthy false
        - build_index失败
        - 系统prompt优化
        - SOUL.md精简
        - 降低token消耗
        - 微内核架构
        - 技能抽取
        - prompt thinning
        - 规则拆分
        - 去除冗余
        - SOUL.md瘦身
        - prompt瘦身
        - 精简内核
        - 微内核
        - SOUL.md重写
        - 飞书通道验证
        - cron投递
        - 通知通道
      disable:
        - 日常任务执行
        - 用户业务代码变更
        - 不涉及框架的普通查询
        - 项目开发 commit
    gate:
      enabled: true
      keywords:
        - SOUL.md
        - 铁律
        - vdb
        - 召回
        - 微内核
        - 技能路由
        - frontmatter
        - RRF
        - Chroma
        - 主脑模式
        - Oracle Mode
        - 框架架构
        - 索引过期
    skill_type: methodology
    priority: high
    related_skills:
      - vdb-retrieval-pipeline
      - autoload-vdb
      - hermes-agent-skill-authoring
      - hermes-evolution-rules
      - hermes-skill-index-optimization-insights
      - hermes-routing-table-index-proposal
---
# Hermes Framework — 微内核架构总纲

本 skill 是框架类知识的总入口，吸收并取代原先分散的 7 个框架微技能：
`hermes-framework-architecture`、`hermes-framework-loader`、`hermes-framework-evolution`、
`hermes-framework-changelog`、`hermes-framework-troubleshooting`、`hermes-self-optimization`、
`hermes-evolution-rules`。按需阅读对应小节。

## 0. 概览（第一性原理）

Hermes 采用**微内核路由**架构：SOUL.md 是精简内核（身份 + 铁律 one-liner + 技能路由表 +
故障处理），细则全部分布到独立 skill，通过 vdb 语义召回按需加载。每一条新增约束必须放在唯一正确的位置。

**配置领域无关性（2026-07-11 确立）**：SOUL.md 七条铁律是跨所有生产类型的"宪法"——
保证无论干哪类任务都守规矩（真实/验证前置/安全/代码完整输出…），但**不决定当前配置适合什么生产类型**。
真正决定配置适配度的是 `skills/` 资产库的主题分布：vdb 按需注入，不命中的 skill 永不进对话，
所以"适合什么生产类型" = 你手里有什么 skill。

推论：想让配置适配某新生产类型，无需改 SOUL，只需往 `skills/` 加对应 skill + rebuild vdb 即可。
铁律提供约束框架，skill 资产提供能力覆盖——两者正交。

> **常见归因错误（2026-07-11 用户纠正）**：分析"当前配置适合什么生产类型"时，
> **禁止归因于 SOUL.md 路由表关键词**。正确归因链：
> 铁律 = 跨领域通用宪法（不挑领域）→ 适配度 = `skills/` 资产库主题分布（vdb 按需注入，不命中的 skill 永不进对话）→
> "适合什么" = 你手里有什么 skill。
> 错误做法：看到路由表关键词偏工程化就下结论"适合代码开发"——那只是 skill 入口索引，根因在 skill 资产。
> 想适配新领域也只需加 skill + rebuild vdb，无需改 SOUL。

```
系统 prompt（旧公式，已纠正见下）= SOUL.md(~2,500t) + USER.md(~180t) + MEMORY.md(~650t) + 固定框架(~2,800t) ≈ ~6,100t/轮

> ⚠ **旧公式严重低估真实注入量（2026-07-14 源码实测纠正）**。上式漏算两个最大头：
> `<available_skills>` 块（~13KB ≈ 3.5K t，全量内联所有 skill 描述）+ 工具 schema（~10-12KB ≈ 3K t）。
> **真实单次注入 ≈ 45–47KB（~1.5–1.7 万 t）**。详见 `references/available-skills-prompt-block.md`。
> 推论：SOUL.md 瘦身只动其中一个小头（框架文件 ~5.5KB）；大头在 skills 区块与工具 schema，
> 砍 skills 区块靠 `agent.coding_context: focus` 模式（零核心改动），非 routing.py 门禁。

## 1. 文件结构

```
~/.hermes/
├── SOUL.md                 微内核（铁律 + 路由表 + 故障处理）
├── AGENTS.md               已废弃（2026-07-10 删除）
├── memories/
│   ├── USER.md             用户画像
│   └── MEMORY.md           环境事实
├── skills/                 按分类组织（活跃 ~99 技能，含 27 个软链目录如飞书 lark-*；`.archive/` 与 `.curator_backups/` 下的不计入、不索引；vdb 索引实测 99）
├── vdb/
│   ├── matcher.py          主入口：search() + is_healthy()
│   ├── indexer.py          索引构建与过期检查 check_index_stale()
│   ├── embed.py            云端稠密 BGE-M3 1024d + 本地 sparse
│   ├── sparse.py           lexical matching
│   ├── chroma/             Chroma hnsw 持久化
│   ├── vdb_state.json      索引状态
│   └── .venv/              Python 虚拟环境
└── plans/                  计划文件
```

## 2. 加载机制与配置文件

会话启动注入顺序：**SOUL.md → USER.md → MEMORY.md**。

- 默认 profile：`~/.hermes/SOUL.md`
- 非 default profile：`~/.hermes/profiles/<name>/SOUL.md`
- USER.md：`~/.hermes/memories/USER.md`
- MEMORY.md：`~/.hermes/memories/MEMORY.md`
- Profile 技能目录：`~/.hermes/profiles/<name>/skills/`（与 vdb 索引默认 SKILLS_DIR 不同；
  设置 `HERMES_SKILL_DIR` 环境变量或用 `install.sh --profile <name>` 安装）

确认当前 profile：`hermes profile list`（◆ 标记活跃 profile）。

**AGENTS.md 已废弃**（2026-07-10），被以下机制替代：SOUL.md §0 铁律（4 层召回链）、
SOUL.md §技能路由表、各独立 skill、系统 prompt 内置的 "Before replying, scan the skills below"。

## 3. 七条铁律与四层召回

| # | 铁律 | 对应 skill |
|---|------|-----------|
| 0 | 技能检索优先 vdb；**不规定检索入口必须在启动期全量注入**（行为约束，非注入策略） | 无（检索方法本身） |
| 1 | 信息真实性 | hermes-truth-redline |
| 2 | 代码输出 | hermes-code-output |
| 3 | 验证前置 | hermes-verification-rules |
| 4 | 安全约束 | hermes-safety |
| 5 | 改进优先于新增 | 本 skill §8（原 hermes-evolution-rules，已并入） |
| 6 | 思考范围限本轮 | 本 skill §9（原 hermes-boundary-rules，已并入） |

**⚠ 铁律#0 常见理解偏差（2026-07-14 用户纠正）**：
铁律#0 的语义是「**强制技能检索入口**」（行为约束——干活前必须先检索），**不是**「启动期必须全量注入 available_skills」。
将 available_skills 从「启动期全量注入 name+description」改为「路由命中后动态补全 skill_view(name)」是对铁律#0 的
**合规增强**而非违反——它把检索从「隐式（模型看着目录自己决定）」变成「显式（路由匹配/matcher 命中才展开）」。
这不同于 **框架修改铁律①**（不深入 agent/核心，优先外部钩子），两者常被混用。详见 `hermes-routing-table-index-proposal` §2。

4 层召回通道（可靠度叠加，无单点依赖）：
1. vdb 语义检索（BGE-M3, ~116ms, top-5）
2. 路由表查表（SOUL.md §技能路由表）
3. available_skills 列表扫描（系统 prompt 内置 "MUST load"）
4. skills_list + skill_view 手动扫描（最后兜底）

## 4. 框架故障诊断与回滚

**本质**：某条加载链路中断（vdb 链路 / skill 链路 / 铁律链路）。沿链路逐段排查。

| 症状 | 根因 | 修复动作 |
|------|------|----------|
| vdb 返回空 / is_healthy()==False | chromadb 损坏 / .venv 丢失 / API key 无效 | `~/.hermes/scripts/init-vdb.sh` 重装 |
| vdb 返回旧技能 | 新增/修改后未 rebuild | `build_index(force=True)` |
| **vdb 召回含已删除技能（幽灵记录）/ 新技能不在索引** | **增删/归档/恢复技能后只改了本地文件、没重建索引**；`check_index_stale()` 能识别新增+删除，但**无自动触发**（仅手动 `vdb-autoload.py --auto/--check` 调用），`is_healthy()` **只测可访问不测 staleness**——健康库也可能是过期库 | 任何技能**新增/删除/归档/恢复**后必须 `python3 ~/.hermes/scripts/vdb-autoload.py --check` 确认 stale 原因，再 `build_index(force=True)` 全量重建，最后 `--check` 复验 `stale=False`。强制规则与触发场景见 `hermes-agent-skill-authoring` §召回质量约束 #4/#5 |
| skill_view 失败 | frontmatter 损坏 / 文件误删 | `ls ~/.hermes/skills/`；`skill_manage(action='create')` 重建 |
| recall top-5 全无关 | trigger 标签太少/脱离用户用语 | 补 trigger 后 rebuild |
| **业务 query 误命中重型框架文档（如"重构函数"→hermes-framework 瞬间注入 7K）** | 中文 sparse 单字切分 + dense 语义歧义；disable/摘词/前缀过滤都无效 | 用 vdb/routing.py **专名门禁**（静态或 frontmatter 声明式 gate）；设计+踩坑+验证清单见 `references/routing-gate-layer.md` |
| 铁律未体现 | SOUL.md 措辞模糊 | 检查铁律格式：one-liner + `→ skill_view(...)` |
| system prompt 膨胀 | SOUL/USER/MEMORY 过多 | 移非铁律内容入 skill |
| 新 skill 无法召回 | 新增后未 rebuild | `build_index(force=True)` |
| **铁律 skill_view 返回 not found / 路由表跳转失败** | **skill 合并或归档后（如 2.0 把 7 个微技能并入本总纲、移入 `.archive/`），SOUL.md 的 skill_view() 引用、路由表右栏、技能索引段仍指向旧名** → 铁律细则调不出来 | 跑 `scripts/audit-soul-refs.sh` 定位所有悬空引用，把旧名 patch 为合并后的真名（如 hermes-evolution-rules→`hermes-framework §8`、hermes-boundary-no-*→`§9`） |
| 飞书 `/new` 等确认只有纯文本（reply /approve…），无按钮卡片 | Feishu adapter **未实现 `send_slash_confirm`**，命中 base 默认 `success=False` → 文本 fallback | 见 `references/gateway-slash-confirm.md`：补发卡片按钮 + 卡片回调分支闭环 |
| **cron `deliver` 写 `hermes-feishu` → `no delivery target resolved`** | 混淆 **toolset 名**（`hermes-feishu`）与 **cron 投递平台标识**（gateway 里平台叫 `feishu`）。`hermes-feishu` 是 toolset 名，cron 的 `_KNOWN_DELIVERY_PLATFORMS` 只认 `feishu` | deliver 用字符串 `'feishu'`（cron 会拆成单元素列表）；先查 `cron/scheduler.py` 的 `_KNOWN_DELIVERY_PLATFORMS` 确认真实标识。**验证通道铁律（用户 2026-07-14 纠正「飞书是通的啊」）**：建外部集成/通知前，先用 `gateway_state.json` 的 `platforms.feishu.state` / cron `_KNOWN_DELIVERY_PLATFORMS` 确认真实通道，勿凭记忆假设 `FEISHU_WEBHOOK_URL`（本机 `.env` 无此键，飞书走 Hermes 原生 gateway websocket，connected）。自建 notify 脚本推群机器人 webhook 是死路——框架 `deliver=feishu` 直接投。详见 `references/feishu-delivery-pitfalls.md` |
| **断言某框架能力不存在/碰核心才改得了（如"路由门禁管不到 available_skills，只能动核心"）** | **凭印象下结论，未读源码**；实际存在官方内置开关（focus 模式）在注入侧即可精简，零核心改动 | **铁律（2026-07-14 用户纠正"先检查拿到真实的数据"）**：对框架机制/边界/改动成本做任何断言前，必须先读真实源码（prompt_builder / coding_context / routing.py）+ 实测，再下结论。详见 `references/available-skills-prompt-block.md` |
| **凭直觉估算框架开销（"focus 能砍 13KB→3KB""80 个 skill 大多非 coding"）** | **未测量**；实际 focus 仅降级 18 个特定编码无关类，80 个 skill 几乎都在顶层类、不在降级名单，实测仅 -792B(-5.4%) | **铁律延伸（同上）**：体量/性能数字禁止凭分布直觉估算，必须写脚本实地测量。测法见 `hermes-skill-index-optimization-insights` |

**⚠ 断言框架限制/数字前先读源码（2026-07-14 用户强纠正，两条延伸）**：
(A) 能力边界：当用户质疑"某机制做不到 X"或你想给"这得改核心/不在边界内"的结论时——**禁止凭记忆/直觉断言**。
先 `search_files`/`read_file` 定位真实实现（prompt_builder.py / coding_context.py / routing.py / system_prompt.py），
确认管线归属与控制点后再答复。本次实测：原话"改注入逻辑不在 SOUL.md 边界内"被"先检查拿到真实的数据"打回；
读源码后发现 `agent.coding_context: focus` 已内置 names-only 降级开关，零核心改动即可精简 available_skills。
(B) **性能/体量估算**：对框架注入量、token 体积、某开关的收益（如"focus 能砍 13KB→3KB"）**禁止凭直觉/分布预判**——
必须写脚本实地测量。本次实测：凭"你这 80 个 skill 大多是非 coding 类"预判 focus 砍 10KB+，
真实测量仅 -792B(-5.4%)——因为实际技能几乎全在顶层类、不在降级名单。印象式估算既错又浪费一轮。
> 测法：`references/available-skills-prompt-block.md` 的 measure 脚本；vdb 用 `~/.hermes/vdb/.venv`。
> `<available_skills>` 注入区块的源码定位、与 routing.py 的区别、focus 开关用法 → `references/available-skills-prompt-block.md`


**一键诊断**：
```bash
cd ~/.hermes/vdb && source .venv/bin/activate || { echo ".venv 激活失败"; exit 1; }
python3 -c "from matcher import is_healthy; from indexer import check_index_stale; \
print(f'healthy={is_healthy()}'); stale,reason=check_index_stale(); print(f'stale={stale} {reason}')"
python3 -c "import chromadb; from chromadb.config import Settings; \
from indexer import CHROMA_DIR, COLLECTION_NAME; \
c=chromadb.PersistentClient(path=str(CHROMA_DIR), settings=Settings(anonymized_telemetry=False)); \
print(f'skills={c.get_collection(COLLECTION_NAME).count()}')"
python3 -c "from matcher import search; [print(r['skill_name'], r['final_score']) for r in search('框架故障')[:5]]"
```

**回滚**（行为退化时立即回退）：
```bash
cd ~/.hermes && git checkout -- SOUL.md memories/USER.md memories/MEMORY.md
cd ~/.hermes/vdb && source .venv/bin/activate && \
PYTHONPATH=$PWD python3 -c "from indexer import build_index; build_index(force=True)"
python3 ~/.hermes/scripts/vdb-autoload.py --check
```

**引用完整性审计**：归档/合并 skill 后跑 `scripts/audit-soul-refs.sh`——检测 SOUL.md 铁律
`skill_view()`、路由表右栏、技能索引段是否有指向已归档 skill 的悬空引用（A 段 FAIL = 真缺陷）。

**失败模式**：SiliconFlow API 限流(429)→等待30s重试；.venv 损坏→删除后重跑 init-vdb.sh；
Chroma 锁残留→`rm -rf ~/.hermes/vdb/chroma/.lock`；磁盘不足→清理 chroma/ 旧索引。

## 5. 框架演进（新增/扩展规则与 skill）

**归属正确原则** — 每一条新增约束必须放在唯一正确的位置：

| 内容类型 | 特征 | 正确存放位置 |
|----------|------|-------------|
| 铁律 | 每轮必须遵守、不依赖场景 | SOUL.md §铁律 |
| 方法论/工作流 | 特定场景使用、有完整步骤 | 独立 skill（skills/） |
| 用户偏好 | 个人习惯 | USER.md |
| 环境事实 | 系统/设备/工具信息 | MEMORY.md |
| 场景→skill 映射 | 路由入口 | SOUL.md §技能路由表 |

**五步决策流程**：① 判断归属 → ② 新增铁律（SOUL.md §铁律末追加 one-liner + `→ skill_view(name=...)`）→
③ 新增方法论 skill（遵守 `hermes-agent-skill-authoring`，路由表加一行，rebuild vdb）→
④ 修改已有规则（优先 patch 现有 skill，不新建）→ ⑤ 验证（rebuild + 测 recall）。

**微技能拆分准则**：一个 skill 只解决一个具体违规行为；若 body 中有多个 H2/H3 描述彼此独立的行为约束 → 拆。
判断标准：大 skill 整体 ~800t 偶尔触发 vs 微技能 ~150-200t 精确匹配。

**⚠ umbrella 正文体积预算（2026-07-13 用户强反应教训）**：合并微技能成总纲时，别把所有细则原样堆进
一个 SKILL.md body——**命中即全量注入**，没有中间档。本 skill 自己就踩了坑：合并 8 个框架微技能后
膨胀到 17,632 字符 ≈ 7,000 tok（= 35 个微技能体积），框架诊断类 query 一命中就瞬间灌 7K，
用户原话「一瞬间注入的 prompt 多到我都怀疑微型架构出错了」。这与微内核初衷（单技能 150-200t 按需）直接冲突。
**正确形态**：umbrella 的 SKILL.md body 只留「索引 + 各节一段概览」（目标 ~1,500t），
每节详情拆进 `references/<节名>.md`，用 `skill_view(name, file_path='references/xxx.md')` 按需取单节——
命中总纲只付概览钱，要哪节调哪节。判据：umbrella body > 3,000t（≈7,500 字符）就该往 references/ 搬。
拆回独立微技能 vs 总纲+references 二选一，取决于「是否需要单一语义入口」；两者都能消除一次性巨额注入。

**合并/归档必须同步更新所有引用者（2026-07-13 自检教训）**：把 skill 合并进总纲或移入 `.archive/` 后，
它就从 vdb 索引和 `skill_view` 可加载集里消失，任何残留引用变成**静默失效**——
`skill_view(name='旧名')` 返回 not found，铁律细则调不出来，且不报错、不进日志，只在真正触发时才暴露。
归档/合并的收尾清单（缺一不可）：
1. `scripts/audit-soul-refs.sh` 扫 SOUL.md 的三处引用点：铁律 `skill_view(name=...)`、路由表右栏、技能索引段。
2. 每个悬空旧名 patch 为合并后的真名或 `总纲 §N`（不是删掉引用——用户仍会用那些关键词）。
3. 本 skill §3/§4 表里的 skill 名同样要改（表格自身也会漂移，本次就漏在这）。
4. `build_index(force=True)` 重建；再实测 `skill_view` 能加载 + 路由表右栏全部命中活跃 skill。
**区分「真漏索引」vs「故意归档」**：磁盘 SKILL.md 数 ≠ 应索引数。`.archive/` 与 `.curator_backups/` 下的
是故意不索引的，别当缺口去"修复"。判据：只有 skills/ 下非 .archive/非 .curator_backups/ 的活跃 skill 才该进 vdb。

**外部 skill 仓库吸收**：重叠→patch 我们的 skill 追加精华；我们没有→用 Hermes 格式封装新 skill；
太偏框架/工具→跳过。

**触发规则阈值**：单轮 input token > 8,000 → 移非铁律到 skill；新 skill recall top-5 < 0.3 → 改 trigger 用词；
铁律偏离 → 检查 one-liner 格式；同场景 ≥3 次 → 按第三步新建。

## 6. 变更日志规范

**⚠ 跨 skill 同步清单（vdb 代码改动必做，2026-07-14 教训）**：改 `~/.hermes/vdb/` 的融合/索引逻辑（`matcher.py` / `indexer.py` / `sparse.py` / `embed.py`）后，**必须同步更新两个描述型 skill**，否则文档会长期停留在旧实现：
- `vdb-retrieval-pipeline`（priority: highest，曾被 pin 保护，日常不触发 review → 最易滞后）
- `autoload-vdb`（正文跟进快，但文件结构注释/数字易漏）
- 同步点：融合公式（RRF(K=60) vs 旧 0.6/0.4 加权）、sparse 输入（trigger_tags + desc 中文短语 vs 仅 trigger_tags）、技能数（索引实测 N，含软链目录）、依赖/文件结构。
- 根因：2026-07-11 `matcher.py` 已从 0.6/0.4 加权切到 RRF(K=60)，但 vdb-retrieval-pipeline 描述直到 2026-07-14 仍写"打分: 0.6dense+0.4sparse"，且被 pin 无人发现。
- 另：技能数随软链（如 27 个飞书 lark-*）增减，以 `build_index` 实测为准，别硬编码旧快照数。
- **关于 pin 保护 skill 的同步（2026-07-14 教训）**：若待同步的目标 skill 被 pin 保护，**须先 `hermes curator unpin <name>` → 完成 review → 同步内容 → `hermes curator pin <name>` 重新 pin**。禁止在 pin 状态下直接改内容或跳过 review——本次滞后的直接原因正是 vdb-retrieval-pipeline 被 pin 后绕过了日常 review。pin 的意义是「防止误改」，而非「绕过审核」；缺的是配套的解 pin 流程，补流程即可，无需拆除 pin 机制。

框架变更必须有记录可查（无法回滚/审计/协作 = 没发生过）。记录位置：
`~/.hermes/memories/FRAMEWORK_EVOLUTION.md`（与演进钩子共享）。

每条记录回答三问：改了什么 / 为什么改 / 怎么验证的。格式：
```markdown
## [YYYY-MM-DD] feat: 新增 hermes-framework skill
- 类型：新增 skill
- 原因：7 个框架微技能合并为总纲，减小碎片
- 变更内容：创建 infrastructure/hermes-framework/SKILL.md，归档 7 个旧 skill
- 验证结果：recall '框架故障' → top-1 命中
- 决策人：@lan
```
类型标签：`feat:`(新增) / `refactor:`(重构) / `fix:`(修复 recall/铁律) / `perf:`(优化 token) / `docs:`(文档)。
审计：`grep "^## " ~/.hermes/memories/FRAMEWORK_EVOLUTION.md`；回滚 = 手动逆向操作。

## 7. System Prompt 微内核优化（SOUL.md 瘦身 / 技能抽取）

**核心理念**：SOUL.md = 精简内核（身份 + 铁律 one-liner + 技能路由表）；每个规则域 = 独立 skill（完整细则）；
每轮只含铁律概要 + 路由表，技能通过 vdb 按需加载。

**内容审计（三类）**：
| 分类 | 含义 | 去向 | 参考 tokens |
|------|------|------|-------------|
| 🔴 CORE | 每轮必需的身份/红线/安全/通信约束 | 留 system prompt | ~800t |
| 🟡 SKILL | 仅特定场景需要的规则/方法论 | 抽取为独立 skill | ~5,000t |
| ⚪ PROFILE | 与 profile 绑定的规则 | 移入对应 profile | ~1,000t |

CORE 判定（不可移动）：影响模型行为基座、每轮回复风格、技能系统前置条件、验证前置概要。
SKILL 判定（可移动）：仅特定场景触发、有明确触发条件、方法论式、不违反时退化为"无约束但不错误"。

**7 步法**：① 内容审计 → ② 设计铁律 one-liner（可执行 + `→ skill:xxx`）→ ③ 构建路由表（左栏用户自然语言，右栏 skill 名）→
④ 创建/修改 skills（trigger≥5, disable≥3, priority 按类）→ ⑤ 4 层召回设计 → ⑥ 文件变更（SOUL 重写、AGENTS.md 删除、USER/MEMORY 压缩、vdb rebuild）→
⑦ 验证（token 节省 + 行为等价 + recall）。

**token 验证**：优化前 ~11,500t/轮 → 优化后 ~4,460t/轮（无 skill 命中省 ~61%）。
**铁律不要超过 8 条**。MEMORY.md 压缩：保留跨会话环境事实，删除过时进度与已固化到 skill 的偏好。

**⚠ 削减 system prompt 体量的真实杠杆（2026-07-14 实测）**：
SOUL.md 瘦身只动框架文件这个小头（~5.5KB）。单次注入两大头是
`<available_skills>` 块（~15KB）与工具 schema（~10-12KB）——
两者**都不在 SOUL.md 边界内**。削减 available_skills 块有三条路（按收益/风险排序）：
1. **focus 模式**（官方内置，零核心改动）：非 coding 类（18 类）降级为 names-only，
   **本仓库实测仅 -792B(-5.4%)**，收益低。详见 `hermes-skill-index-optimization-insights`。
2. **names-only 模式**（Phase 1 已落地，默认 full 零变更）：全部 skill 降级为 names-only，
   保留名称兜底。**实测 -10,751B(-71.9%)，省 ~3,583 tokens**。
   见 `hermes-routing-table-index-proposal`。
3. **routing-only 模式**：仅 SOUL 路由表常驻。**实测 -12,847B(-85.9%)，省 ~4,281 tokens**。
   风险最高（无 names 兜底），建议先运行 names-only 阶段。
工具 schema 体积由核心工具集决定，框架侧不可直接砍。

### 7.1 辅助任务(auxiliary)推理 token 泄漏 ← `references/auxiliary-ta<api-key>-tokens.md`

**症状**：后台自动任务（会话标题 `title_generation`、vision、compression 等）走推理模型时，
对一个极简任务偷偷烧掉上千 reasoning token（实测 hy3:free 生成 7 词标题花 1,154 reasoning token），
且该调用独立、不命中主会话前缀缓存，是纯额外开销。

**根因**：`agent.reasoning_effort`（默认 high）**只作用于主会话主模型**
（`gateway/run.py::_load_reasoning_config`），与辅助任务的
`agent/auxiliary_client.py::call_llm` 是**两条独立通道**。`title_generator.py` 不传 reasoning 抑制，
`_get_task_extra_body(task)` 未配 → 不注入；推理模型在 OpenRouter 默认开 thinking → 整段隐形推理。

**修复**（**不要**动 `agent.reasoning_effort`，那治不了且会拉低主会话）：在
`auxiliary.<task>` 加 `extra_body: {reasoning: {enabled: false}}`（OpenRouter 原生关闭思考字段，
经源码确认形状并实测生效），或把该任务 `model` 换成非推理 instruct 模型。
详见 `references/auxiliary-ta<api-key>-tokens.md`（字段形状）+ `references/config-yaml-write-guardrail.md`（改 config.yaml 的写入护栏陷阱：patch/execute_code.write_file 会拒或静默 no-op，须走终端）。

## 8. 自身进化规则（hermes-evolution-rules）

- **改进优先于新增**：先 patch 现有文件/skill，只有证明现有结构无法承载才新建。
- **增量变更**：所有改动必须 patch（find-replace），不允许 write_file 整文件覆盖；覆盖触发审查。
- **⚠ write_file 是整文件替换，不是追加（2026-07-14 实战踩坑）**：write_file 会**整体覆盖**目标文件，即使你意图是「追加一行」。曾因此把 FRAMEWORK_EVOLUTION.md 的历史记录一次性清零（仅留新写内容）。对已有内容的文件做「追加」，必须用 `patch` 模式：`old_string` = 文件末尾若干行（含换行）+ `new_string` = 末尾 + 新内容。**覆盖后的恢复三招**：① 文件在 git 跟踪内 → `git show HEAD:<path>` 取回；② 本会话 read_file 过该文件 → 缓存完整内容可重建；③ 立即用 write_file 把原文 + 新内容一并写回。最佳防线：追加永远用 patch，绝不用 write_file。
- **环境适配验证**：变更后必在当前主机跑 1 次验证，禁止只改不测。
- **持久化边界**：所有变更在 `~/.hermes/` 边界内，兼容 `hermes update`；不依赖核心代码，仅用已知持久化目录（vdb/ skills/ memories/）。
- **技能维护**：使用中发现过时/不完整/错误 → 立即 patch；复杂任务成功后 → 保存为 skill。

## 9. 回答边界硬约束（合并自 hermes-boundary-rules）

四条规则共同约束回答严格服务于**本轮用户明确提出的问题**，不假设、不扩展、不铺垫下一轮。要点：

- **不提前规划后续对话（no-future-planning）**：禁止"接下来你可以问…""如果你想知道更多…"等引导下一轮的措辞。
- **不过度推演（no-over-reasoning）**：内部完成推理，只输出 1-2 句结论摘要；不输出与问题无关的背景或扩展分析。
- **不自行拓展场景（no-scope-creep）**：禁止主动扩展用户未问的"你还可以考虑…""顺便一提…"。
- **不预判后续任务（no-ta<api-key>）**：不为用户未提及的任务提前准备材料/工具/备选方案。

统一自检（每次回答前）：① 没引导下一轮 ② 没冗余推演 ③ 没主动扩展 ④ 没为未提及任务做准备。

> 完整四条规则 + 禁用场景见 `hermes-boundary-rules` 原 SKILL.md，已并入本 skill 第 6 铁律配套约束。

## 10. 微内核重构速查

目标架构：SOUL.md(~2,300t 精简内核) + USER.md(~180t) + MEMORY.md(~650t) + Skills(按需加载)。
铁律格式 = 一句话规则（可独立执行）+ `→ skill_view(name='skill-name')`。
迁移步骤：识别铁律级/方法论级 → 铁律缩 one-liner 留 SOUL → 方法论移独立 skill → 所有 skill 加路由 → 删 AGENTS.md → rebuild vdb。
每轮 input 目标 5,000~6,000t。详见 `references/recall-test-results.md`（self-optimization 实证数据）。
