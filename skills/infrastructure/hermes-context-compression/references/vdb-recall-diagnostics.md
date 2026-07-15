# 附：语义检索召回失败诊断方法（vdb 同源，可复用）

> 本会话为排查 vdb 技能检索失败而提炼的方法论，与"进检索前的路由/分层"思路同源。
> 适用于任何基于向量 + 倒排混合检索的召回问题诊断。

## 核心判定：两种失败，两种修复层

失败不是一律"改融合公式"。先区分：

| 现象 | 根因 | 修复层 |
|------|------|--------|
| 期望 skill 名不在索引内 | 索引完整性缺口（indexer 漏收 / benchmark 期望名写错） | 重新 build_index / 核对期望名 |
| 目标在候选(top-16)但排错（dense_rank 低、sparse_rank 高） | 融合/路由问题 | 进检索前的路由/分层（上下文分类），非改分数 |
| dense 完全 recall 不到（e_dr=NA，连 top-16 都没进） | embedding 缺口 | 补 trigger/desc 元数据或 prose 模板 |

**必须先判再改**：直接调融合权重会掩盖真实根因。

## 判定脚本（vdb/ 下用 .venv 运行）

```python
from matcher import _get_collection, search
c = _get_collection()
res = c.get(include=['metadatas'])
names = sorted(m['skill_name'] for m in res['metadatas'])
print('索引内 skill 数:', len(names))   # 对照 benchmark 期望名，找缺失

r = search("changelog 更新了啥", top_k=16)
for i, x in enumerate(r):
    print(i, x['skill_name'], 'd=%.3f'%x['dense_score'], 's=%.3f'%x['sparse_score'])
```

## 真实教训（2026-07-12）

- 旧结论"dense 偏差导致 6-7 条失败"被推翻：实测 8 条期望 skill 从未被索引
  （hermes-framework-changelog / hermes-base-config-sync / hermes-self-optimization 等），
  2 条 dense 完全 recall 不到（github / doubt-driven-development）。真实索引内 Top1 失败仅 5 条。
- 原型"LEXICAL 型 sparse 优先路由"仅 +2 Top1 且引入 2 条误伤 ——
  证实在候选集不完整 + trigger 不精准时，路由补丁收益有限。
- 用户设计边界（铁律）：向量天花板内不靠置信度加权/分数微调；正确方向是路由/分层。

## 诊断流程图（二分法）

```python
indexed = {m['skill_name'] for m in _get_collection().get(include=['metadatas'])['metadatas']}
if expected not in indexed:
    print("根因=索引完整性缺口（目标未进候选），查 indexer 漏扫 / benchmark 期望名过时")
else:
    r = search(query, top_k=16)
    for i, hit in enumerate(r):
        if hit['skill_name'] == expected:
            print(f"目标在候选 rank≈{i}，被前置 skill 顶下 → 融合/路由层问题")
```

## 关联

- vdb 真实架构：`vdb-retrieval-pipeline` SKILL.md 当前被 pin 且描述过时
  （仍写 0.6/0.4 加权 + 仅 trigger_tags；实际是 RRF(K=60) + trigger +0.010 + desc 中文短语入词表）。
  该 skill 已 pin，需用户 `hermes curator unpin vdb-retrieval-pipeline` 后才能修正主体。
- 同源衍生 skill：`hermes-context-compression`（SpanKind 上下文分类，落地的"进检索前路由"实例）。
