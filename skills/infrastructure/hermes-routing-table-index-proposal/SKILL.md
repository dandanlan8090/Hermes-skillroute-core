---
name: hermes-routing-table-index-proposal
description: 把 available_skills 从启动期全量注入改为路由表即索引（names-only/routing-only），含三路验证、基线快照、vdb
  检索健康监控与 cron 看门狗。
metadata:
  hermes:
    tags:
      trigger:
      - 路由表即索引
      - available_skills改造
      - 上下文精简方案
      - 技能索引架构
      - 启动期注入优化
      - 按需加载技能
      - 路由表索引
      - 索引模式
      - routing-table
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

# 提案：路由表即索引（Routing-Table-as-Index）

> **状态：Phase 1 已实施（2026-07-14）** — `index_mode` 开关已落地，默认 `full` 零行为变更。
> 仅改 `build_skills_system_prompt()` 渲染分支 + `system_prompt.py` config 读取，**未碰检索/缓存框架**，符合授权边界。
> 记录时间：2026-07-14

## 0. 一句话

把 `available_skills` 从「启动期全量注入 name+description」改为「常驻薄索引（SOUL 路由表 + 技能名）+ 命中后 `skill_view` 动态补 description」。这是**对铁律#0（强制技能检索入口）的合规增强**，不是违反。

## 1. 动机与结构性权衡

单次 \"hi\" 请求的真实注入约 45KB（实测），其中：
- 框架三件套（SOUL/USER/MEMORY）：已重切，20.5KB → 现更小
- `available_skills` 区块：**~14.7KB（实测 14,681 bytes）**，占 ~30%
- 工具 schema：~10-12KB

`available_skills` 是每轮固定全量注入 96 个技能的 `<name>: <description>`。这是「预热成本」付得最狠的一块——99% 的 description 这轮根本用不上。

`focus` 模式实测仅省 792B（-5.4%，见 `hermes-skill-index-optimization-insights`），因为本仓库技能多在 `core/workflow/methodology` 等顶层类，不在降级名单。所以 focus 不解决结构性问题。

## 2. 关键 reframing（老黎原话，已采纳）

> 铁律#0 的核心是「强制技能检索入口」，它并不规定检索入口必须在启动期全量注入。将 available_skills 从「启动期全量注入」改为「路由命中后动态补全」，是对铁律的合规增强，而非违反。

澄清两道被混用的铁律：
- **#0 技能检索（SOUL.md 铁律）**：管**行为**——干活前必须先检索。与注入形态无关。✅ 本提案不违反。
- **框架修改铁律①（memory 2026-07-13）**：不深入 Hermes 核心（agent/内部）、优先外部钩子、避免更新失效。⚠️ 本提案**会触碰** `prompt_builder.py`，须授权。

## 3. 当前机制（已查实，file:line）

- `agent/prompt_builder.py:1445` `build_skills_system_prompt()` 生成 `available_skills` 区块（`:1691-1693` 包裹 `<available_skills>` 标签），**每次请求全量内联**所有技能 name+desc。
- `agent/system_prompt.py:314` 调用它，`:322` `stable_parts.append(skills_prompt)` —— **该区块属于 STABLE 系统提示层**（会话内字节稳定，命中 prompt 缓存）。
- `vdb/routing.py` `is_query_allowed_for_skill()` 是**检索后过滤器**，只决定 vdb 返回哪几个 skill，**完全不碰** available_skills 注入（两条独立管线）。→ 门禁做不到「路由命中才展开」。
- `coding_context.py` `_NON_CODING_SKILL_CATEGORIES`（18 类）+ `focus` 模式：只能降级非 coding 类为 names-only（实测 -5.4%），不解决结构问题。
- **vdb 覆盖已修复（2026-07-14）**：原 `indexer.py` 用 `Path.rglob` 在 Python 3.14 不跟进软链，漏掉 27 个 lark-*。改为 `os.walk(followlinks=True)` 后，vdb 索引 71→98，目录 96 个技能 **100% 覆盖**（含 28 个飞书 skill）。→ 「路由表即索引」的**检索覆盖前置条件已满足**。

## 4.1 Phase 1 实测数据（2026-07-14，真实运行）

`build_skills_system_prompt(index_mode=...)` 直接测量 `<available_skills>` 区块：

| 模式 | 区块 bytes | 占 full 比 | 节省 tokens(估) | 备注 |
|------|-----------|-----------|----------------|------|
| `full`（默认） | 14,962 | 100% | — | 与改动前**逐字节一致**（default==full 验证通过） |
| `names-only` | 4,211 | **-71.9%** | ~3,583 | 保留全部技能名兜底，无 desc |
| `routing-only` | 2,115 | **-85.9%** | ~4,281 | 仅 SOUL 路由表（30 行），无逐技能列表 |

缓存安全：三种模式的 `cache_key` 均含 `index_mode`（`prompt_builder.py:1481` 区域），生成不同缓存条目，不互相污染；STABLE 系统提示层字节仍 session 内稳定。

检索无副作用验证：发飞书消息→lark-im、调试报错→debugging-patterns、写测试→hermes-tdd-workflow、部署发布→hermes-shipping-verification，top3 命中不变。vdb 覆盖仍为 100%（Phase 0 修复后 98 索引 / 96 目录）。

测量脚本：`references/measure_skill_index_extended.py`（`--all` 测三模式，`--json` 导出）。

## 5. 缓存安全性分析（决定性）

AGENTS.md 铁律：「Per-conversation prompt caching is sacred… system prompt byte-stable for life of conversation」。

- 三种模式的常驻部分（full / names-only 列表 / 路由表）均**小且会话内不变** → STABLE 层字节稳定 → 缓存安全。
- `skill_view(name)` 的结果进**对话层**（assistant/user 消息），不进系统提示 → 不触发缓存失效。
- `index_mode` 在 `system_prompt.py:_resolve_skills_index_mode()` 会话启动时解析一次 → 会话内不变（同 `coding_context` 契约，下次会话生效）。

## 6. 风险与缓解

| 风险 | 严重度 | 缓解 |
|------|--------|------|
| vdb 漏召 → 模型无 desc 可判断相关性 | 中 | names-only 保留 names 兜底；vdb 现已 100% 覆盖；加路由表精确匹配双通道 |
| 弱相关技能联想退化 | 中 | names-only 已含语义线索（如 `lark-base`/`performance-optimization`）；可保留 high-value 类 full-desc（选项 C） |
| 改 prompt_builder 核心 → 更新失效风险（铁律①） | 已控 | 仅改 `build_skills_system_prompt` 渲染分支 + 加 `index_mode` 参数，不动检索/缓存框架；local patch 受护栏保护 |
| 会话中途切换形态 → 缓存击穿 | 高（设计规避） | 形态会话启动时定（同 focus 契约：deferred to next session），会话内不变 |
| skill_view 不可用（toolset 禁用）时退化 | 低 | 仅在 `has_skills_tools` 为真才启用动态补全（system_prompt.py:292 已有守卫） |
| SOUL 路由表标题变更导致 routing-only 空 | 低 | `_build_routing_index` 正则匹配 `## 路由表`（已对齐重切后 SOUL.md）；匹配失败返回空字符串（退化为无技能区块，需人工关注） |
| 告警投递错配（webhook 假设） | 中 | **此环境飞书走 Hermes 原生 gateway（platform `feishu`，websocket，connected），不是群机器人 webhook URL**——`.env` 无 `FEISHU_WEBHOOK_URL`。cron 告警用 `deliver='feishu'`（cron 平台标识，非 toolset 名 `hermes-feishu`）经 gateway 送达，**不要**内置 notify.py 调 webhook（死路）。验证通道：`gateway_state.json` 的 `platforms.feishu.state` 或 `hermes cron`；飞书连通态以 gateway 为准，非 env 变量。教训：接通知前先查真实通道，勿凭记忆假设机制。 |
| cron `deliver` 标识符错配 | 中 | cron 投递平台标识是 **`feishu`**（见 `cron/scheduler.py` 的 `_KNOWN_DELIVERY_PLATFORMS`，对应 `FEISHU_HOME_CHANNEL`），**不是** toolset 名 `hermes-feishu`。实测：首跑 `deliver='hermes-feishu'` → `last_delivery_error="no delivery target resolved"`；改 `deliver='feishu'` → `last_delivery_error=null` 并真投飞书。铁律：填 deliver 前先查 scheduler.py 的真实平台集合，勿把 toolset 名当投递标识。 |

## 7. 回滚阈值（老黎设定，已落地）

客观硬阈值：**评估周期内（一周，或一组核心查询测试），技能检索精确率/召回率下降超过 5% → 自动回滚到 `full` 并记日志。**

- **当前 Phase 2 已实际启用** `names-only`（`config.yaml` 当前值，非默认 full），监控+基线+ cron 已就位（见 §8 Phase 2）。回滚动作：`hermes config set agent.skills_index_mode full` + 查 vdb 索引/embed 漂移。
- 启用某模式后，用 `measure_skill_index_extended.py --json` 做基线 + 定期对核心 query 集跑 vdb 命中率对比，超 5% 降幅即回滚。监控详见 `references/monitoring.md`。

## 8. 分阶段实施（进度）

- ✅ **Phase 0（已完成）**：vdb 100% 覆盖（修 indexer 软链跟进）。
- ✅ **Phase 1（已完成 2026-07-14）**：
  - `prompt_builder.py:build_skills_system_prompt` 加 `index_mode` 参数（默认 `full`，零行为变更）
  - 渲染分支：`names-only` 复用 `demoted` 全类降级；`routing-only` 新增 `_build_routing_index()` 解析 SOUL `## 路由表`
  - `cache_key` 加入 `index_mode`
  - `system_prompt.py` 新增 `_resolve_skills_index_mode()`（env `HERMES_SKILLS_INDEX_MODE` > config `agent.skills_index_mode`，默认 full）
  - `config.yaml` 加 `agent.skills_index_mode: full`（经 `hermes config set`）
  - `references/measure_skill_index_extended.py` 三模式测量脚本
- ✅ **Phase 2（已启用 2026-07-14）**：灰度启用 `names-only` 已落地——`config.yaml` 当前 `agent.skills_index_mode: names-only`（代码默认仍为 `full`，由 config 覆盖生效）。基线快照已存 `references/baseline.json`：full=14962B / names-only=4211B(-71.9%) / routing-only=2115B(-85.9%)。回滚阈值（§7）：若核心 query 集的 vdb 命中率较基线下降 >5%，自动回滚 `full`（`hermes config set agent.skills_index_mode full` 并记日志）。
  - **检索层健康监控已上线 (v2)**：`references/monitor_index_mode.py`（`--update-baseline` 重建核心 query 集基线 `core_queries_baseline.json`；`--check` 默认对比，`--dry` 仅给回滚建议不执行，`--json` 输出；超 5pp 触发回滚建议并写 `monitor_log.jsonl`）。命中判定用 **RRF top1/top3 精确匹配 expected**（非 final_score 阈值，避免绝对值无参照的误报）。核心集由原始 82 条 query 筛出 53 条有效对（剔除 29 个索引中不存在的悬空 expected）。⚠ **边界**：该监控测的是 vdb 检索健康（证明 index_mode 未引入检索回归），**抓不到** names-only 真正的端到端选技能退化（模型失 description），后者需跑 LLM 端到端评估，不在本监控范围。
  - **cron 周巡检**：`scripts/index_mode_monitor.sh`（薄壳桥接 vdb `.venv`，跑 `monitor --check` 人类可读输出）已注册 `cronjob ece8c80f7016`，每周一 09:00 UTC 跑，**每周固定投递一次状态摘要**（无偏差也发 ✓ 心跳，超阈值发回滚建议）。**告警经已连通的飞书 gateway 送达（`deliver=feishu`）**，不内置 webhook/notify——你的飞书通道是 Hermes 原生平台（cron 标识 `feishu`，非 toolset 名 `hermes-feishu`），不是群机器人 webhook URL（`FEISHU_WEBHOOK_URL` 不存在于 `.env`）。回滚默认不自动执行（config 受护栏保护，需人工 `hermes config set agent.skills_index_mode full` 确认）。

**vdb 检索质量优化（2026-07-14 第二轮）**：核心 query 集未命中从 7→5（top3 86.8%→90.6%）。修正了 2 个有争议的 benchmark 期望（"看看我的待办列表"→lark-task 飞书语境正确；"合并代码到主分支"→hermes-git-worktree 分支语义更贴）。剩余 5 个未命中**全部为稠密向量语义召回天花板**（"设计方案/开闭原则"被 plan-workflow 的 dense 带偏；"排错/系统信息"被 truth-redline 的"错/真实"词带偏；yuanbao 为 niche 场景）。已验证：给 spec-driven/doubt-driven 加中文 trigger 词（功能设计/SOLID 等）**未能拉回 top1**——RRF 中 dense_rank 主导（K=60），sparse 词救不回 dense 偏置，印证铁律"向量天花板内不调分数、允许命中失败"。**trigger 词已拍板保留**（老黎 2026-07-14：词本身语义合理、对非目标 query 有正常触发价值、rebuild 为单次操作无持续成本，回退亦需 rebuild 纯收益不明）。诊断脚本：`references/diag_vdb_misses.py`。 投递机制细节见 `references/cron_feishu_delivery.md`。

**方法论文件**：`references/monitoring.md` 沉淀了"三路交叉验证 names-only 生效"的操作方法，含 session 级注入检测、stats 验证、依赖链接检查，供未来会话直接复用。
- ⬜ **Phase 3（待定）**：按数据决定是否进 routing-only。

## 9. 待老黎决策的点（已决策部分）

1. ✅ 授权碰 prompt_builder.py？— **授权**，边界限定为渲染分支，已实施。
2. ✅ 选 A/B/C？— **选 B（names-only）为基线，C 作为配置变体**（coding 类保留 full-desc，通过 names-only + 白名单实现）。
3. ✅ 会话级 opt-in？— **接受**（env/config 解析，下次会话生效）。
4. ✅ 回滚阈值？— **精确率/召回率降 >5% 自动回滚 full**（§7）。
5. ✅ Phase 2 实际启用？— **是**，`config.yaml` 设为 `names-only`，监控+基线+ cron 已就位。

## 10. 参考

- `agent/prompt_builder.py` — `build_skills_system_prompt()` (:1445, 加 `index_mode`), `<available_skills>` 包裹 (:1717), `demoted` 集合 (:1651), `cache_key` (:1486 区域), `_build_routing_index()` (新增)
- `agent/system_prompt.py` — `has_skills_tools` 守卫 (:292), `stable_parts.append` (:321), `_resolve_skills_index_mode()` (新增)
- `vdb/routing.py` — `is_query_allowed_for_skill()`（检索门禁，不碰注入）
- `agent/coding_context.py` — `_NON_CODING_SKILL_CATEGORIES`, `focus` 模式
- `vdb/indexer.py` — 已修 `os.walk(followlinks=True)`（2026-07-14）
- `skills/infrastructure/hermes-skill-index-optimization-insights/` — focus 实测（-5.4%）
- `AGENTS.md` — prompt caching 铁律
- `references/monitoring.md` — 在线监控方法论：三路验证 names-only 生效、monitor 脚本用法、关键边界（测 vdb 健康非 names-only 端到端）、cron 看门狗模式
- `references/monitor_index_mode.py` — 核心 query 集 RRF 命中率监控（--init 建基线 / --compare 对比，超 5pp 触发回滚建议）
- `references/core_queries_baseline.json` — 核心 query 集基线（53 条有效对，剔 29 个悬空 expected）
- `references/monitor_log.jsonl` — 每次对比运行日志（delta/触发标记）
- `references/cron_feishu_delivery.md` — Hermes cron→飞书投递机制实测摘录（deliver 标识 `feishu` 非 `hermes-feishu`、no_agent 每次投递、`[SILENT]` 抑制、gateway 连通前提）
- `scripts/index_mode_monitor.sh` — cron 薄壳 wrapper（桥接 vdb `.venv`，跑 `monitor --check`，退出码非 0 透传错误），cronjob `ece8c80f7016` 每周一 09:00 UTC，deliver=feishu 心跳+告警
- `references/vdb_hitrate_tuning.md` — vdb 命中率调优实证笔记：dense_rank 主导 RRF(K=60) 使 sparse trigger 词无法拉回 dense 误排（实证）、benchmark 期望修正纪律、cron deliver 标识 gotcha、重建索引操作
