# vdb 命中率调优实测笔记 (2026-07-14)

## 核心结论: dense_rank 主导 RRF, sparse/trigger 词救不回 dense 天花板

Hermes vdb 融合 = RRF(K=60) = `1/(60+dense_rank) + 1/(60+sparse_rank)`。
dense_rank 1-2 的 RRF 分远高于 sparse 拉回的 rank, 所以**给 skill frontmatter 加中文 trigger 词(进 sparse)无法把被 dense 向量误排的 query 拉回 top1**。

实证(本轮): 给 `spec-driven-development` 加 `功能设计/模块设计/功能方案/设计实现/system design`, 给 `doubt-driven-development` 加 `设计原则/SOLID/OCP/原则落地/设计权衡/设计评审`, `indexer.build_index(force=True)` 重建后重跑 `diag_vdb_misses.py` —— 这两个 query 仍没进 top5 (top1 仍是 `hermes-plan-workflow`)。**trigger 词没达成降未命中目标。**

对齐铁律(老黎: 向量天花板内不调分数/置信度加权, 允许命中失败):
- 对 dense 天花板类未命中, **不要烧一次 force-rebuild 去 padding trigger 词** —— 实测无效。
- 真正能降未命中的只有: (a) 修正 benchmark 期望错误; (b) 在 SOUL 路由表加精确匹配双通道(影响全局, 需授权)。

## 未命中三分法 (诊断流程)

1. 跑 `references/diag_vdb_misses.py` 看每个 query 的 top5 候选 dense/sparse/rank。
2. 归类:
   - **benchmark 期望错误/有争议**: query 字面指向别的 skill 更对 (如飞书语境『待办列表』→`lark-task`; 『合并到主分支』→`hermes-git-worktree`)。→ 改 monitor 的 `RAW_QUERIES` 期望为真实正确 skill, 重建基线。
   - **skill doc/trigger 弱覆盖**: 期望 skill 完全没进 top5 且 sparse 也没命中 → 可加 trigger 词, 但先看是不是 dense 天花板(上面结论: 多半无效)。
   - **dense 天花板**: 期望 skill 在候选里但被 dense 推给别人, gap 小 → 接受, 保留在监控可见。

## benchmark 期望修正纪律

- `expected` = **人类判断的真实正确 skill**, 不是『vdb 当前返回什么』。
- 禁止为让评测通过而把 expected 改成 actual (那是 rig 评测)。
- 本轮回合: 未命中 7→5, top3 86.8%→90.6%, 靠的是修正 2 个争议期望, **不是** trigger 词。

## cron 投递 gotcha (飞书)

- cron `deliver` 平台标识 = gateway 平台名 **`feishu`**, 不是 toolset 名 **`hermes-feishu`** (后者 cron 不认, 报 `no delivery target resolved for deliver=hermes-feishu`)。改 `feishu` 后 `last_delivery_error` 变 null。
- no_agent 模式: 脚本 stdout **原样投递** (`its stdout is delivered verbatim`) → 每周心跳天然成立, 只要脚本总有输出。
- `[SILENT]` 标记会抑制投递; 心跳任务要确保不含该标记、总输出内容。
- 查真实通道: `gateway_state.json` 的 `platforms.feishu.state`, 或 cron scheduler `_KNOWN_DELIVERY_PLATFORMS` 集合 (含 feishu/telegram/discord/slack...)。

## 重建索引 (改 frontmatter 后必做)

```python
cd ~/.hermes/vdb && .venv/bin/python -c "import indexer; indexer.build_index(force=True)"
```
trigger 词必须 nested 格式 (`metadata.hermes.tags.trigger` 列表), 顶层 trigger 键被 indexer 忽略 (老黎 07-13 踩过的坑)。

## 已知重叠

vdb 检索融合机制本身属 `vdb-retrieval-pipeline` skill (当前 pinned, 需 `hermes curator unpin` 才能改)。本笔记只沉淀『监控/调优 workflow』视角; 若 curator 解 pin, 可将『dense_rank 主导 RRF』这条移入该 skill 作权威说明。
