# index_mode 在线监控方法论

> 配套 `hermes-routing-table-index-proposal` Phase 2 监控落地。本文件沉淀操作方法、关键边界、cron 看门狗模式，供未来会话直接复用。

## 三路交叉验证 names-only 是否生效
1. **查真实配置**：`grep skills_index_mode ~/.hermes/config.yaml`（env `HERMES_SKILLS_INDEX_MODE` 为空时走 config）。默认 `full`；若非 full 即已启用。
2. **看本轮实际注入**：系统提示 `<available_skills>` 区块若全标 `[names only]`、无 description → 生效。
3. **跑真实测量**：`references/measure_skill_index_extended.py --all --json` 看区块字节（full=14962 / names-only=4211 / routing-only=2115）。

不要只信记忆或文档声明——以「配置值 + 实际注入形态 + 测量字节」三者吻合为准。

## monitor_index_mode.py
复用 `matcher` 的 RRF 检索（与线上一致），对核心 query 集测 top1/top3 命中率。
- `--init`：从原始 82 条 query 筛出 53 条「expected 真实存在于索引」的有效对，存 `core_queries_baseline.json`。**务必剔除悬空 expected**——`vdb/eval/benchmark_rrf.py` 含 ~20 个索引中不存在的技能名（如 `hermes-base-config-sync`、`mlops-inference`、`segment-anything`、`audiocraft`、各 `hermes-framework-*` 子类），留着会污染监控。
- 默认 `--compare`：与基线对比，超 5pp（§7 阈值）触发回滚建议并 append `monitor_log.jsonl`。
- **必须在 vdb 独立 .venv 跑**：`cd ~/.hermes/vdb && .venv/bin/python <path>/monitor_index_mode.py`（该 .venv 含 chromadb，系统/hermes-agent venv 无）。

## ⚠ 关键边界（最重要的认知）
`index_mode` **只改 `available_skills` 注入，完全不碰 vdb 检索管线**（`vdb/routing.py` 与注入是两条独立管线，见 SKILL.md §3）。因此：
- 本监控测的是 **vdb 检索健康**（索引漂移/损坏、embed 变更），能证明 index_mode 切换**未引入检索回归**（构造上命中率应恒等）。
- 本监控 **抓不到** names-only 的真正风险：模型失去 description 后的端到端选技能退化。那需跑 LLM 端到端评估（给 names-only 注入、喂真实 query、看模型实际 `skill_view` 命中），不在本监控范围。
- 结论：本监控是「无回归」证据，不是「names-only 安全」证据。报告时勿误读为后者。

## cron 看门狗模式（已落地）
- `cronjob create` 用 `no_agent=true` + `script=` 时，**script 必须在 `~/.hermes/scripts/` 且用相对名**；传绝对/家目录路径会被拒（报错 "Script path must be relative to ~/.hermes/scripts/"）。
- 因监控需 vdb `.venv`，不能在 scripts/ 直接跑。用薄壳 wrapper `scripts/index_mode_monitor.sh`：切到 vdb `.venv` 调真实脚本，仅超阈值/vdb 异常时输出告警。符合 cron 看门狗范式——**无偏差静默**（"silence = nothing to report"），避免每次跑都刷无意义通知。
- 已注册：`cronjob ece8c80f7016`，每周一 09:00 UTC，`deliver=local` 存盘（本 CLI 会话无推送通道）。

## 回滚动作（触发阈值时）
`hermes config set agent.skills_index_mode full` 并核查 vdb 索引/embed 是否漂移。
