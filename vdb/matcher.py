"""
匹配器 — Chroma 稠密召回 → sparse 重打分 → RRF 融合 → disable 过滤。

流程:
  1. query → 云端 BGE-M3 稠密向量
  2. Chroma cosine 距离召回 top-K 候选技能（dense rank）
  3. 每个候选: 计算本地 sparse 匹配分（trigger_tags vs query）
  4. disable 标签命中则过滤
  5. 在有效候选中按 sparse 分排 sparse rank
  6. RRF = 1/(k + dense_rank) + 1/(k + sparse_rank)
  7. 按 RRF 分数排序返回

回滚: VEC_WEIGHT/SPARSE_WEIGHT 保留，切回 line:113 的旧表达式即可。
"""

import json
from typing import List

import chromadb
from chromadb.config import Settings

from embed import get_cloud_dense, calculate_sparse_score
from indexer import VDB_DIR, CHROMA_DIR, COLLECTION_NAME, TOP_K_CANDIDATES
import routing

# ── 参数 ──────────────────────────────────────────────────────────
# 旧权重保留供回滚对比（2026-07-11 前用 0.6/0.4）
VEC_WEIGHT = 0.6
SPARSE_WEIGHT = 0.4
# RRF 融合参数
RRF_K = 60

# v2.1: prose 对齐 query 模板。DOC 侧是 "{name}：{leading}。{desc}。触发：{branches}。"
# QUERY 侧用 "{query}" 动词对齐。短查询(<10字)才包装，长查询保留裸 query
QUERY_TEMPLATE_PROSE = "调用{query}。"
MIN_QUERY_LEN = 15

# ── Chroma 客户端 ────────────────────────────────────────────

_client: chromadb.ClientAPI | None = None
_collection = None
_healthy = False  # 模块加载时是否预热成功


def _get_collection():
    global _client, _collection
    if _collection is None:
        _client = chromadb.PersistentClient(
            path=str(CHROMA_DIR),
            settings=Settings(anonymized_telemetry=False),
        )
        _collection = _client.get_collection(COLLECTION_NAME)
    return _collection


def is_healthy() -> bool:
    """返回 vdb 是否可用（预热 + 索引有效）。"""
    return _healthy


# ── 匹配 ─────────────────────────────────────────────────────────

def search(query: str, top_k: int = 5) -> List[dict]:
    """主入口：稠密→sparse→RRF→过滤→排序。

    vdb 不可用时（chroma 损坏 / 未构建）返回空列表，不抛异常。
    """
    if not _healthy:
        return []
    collection = _get_collection()

    # 1. query 稠密向量（v2.1: 短查询用 prose 模板包装，长查询裸送）
    q_text = query if len(query) >= MIN_QUERY_LEN else QUERY_TEMPLATE_PROSE.format(query=query)
    query_dense = get_cloud_dense([q_text])[0]

    # 2. Chroma 召回 top-K
    results = collection.query(
        query_embeddings=[query_dense],
        n_results=TOP_K_CANDIDATES,
        include=["distances", "metadatas", "documents"],
    )

    if not results["ids"][0]:
        return []

    distances = results["distances"][0]
    metadatas = results["metadatas"][0]

    # Chroma 返回按余弦距离升序（最近优先），迭代序号即 dense rank
    candidates = []
    for dense_rank, (dist, meta) in enumerate(zip(distances, metadatas), start=1):
        dense_score = 1.0 - dist  # cosine 距离转相似度
        tag_sparse = meta.get("tag_sparse", "{}")
        sparse_score = calculate_sparse_score(query, tag_sparse)

        disable = json.loads(meta.get("disable_tags", "[]"))
        trigger = json.loads(meta.get("trigger_tags", "[]"))

        candidates.append({
            "skill_name": meta["skill_name"],
            "skill_path": meta["skill_path"],
            "trigger_tags": trigger,
            "disable_tags": disable,
            "dense_rank": dense_rank,
            "dense_score": round(dense_score, 4),
            "sparse_score": round(sparse_score, 4),
            # final_score 在 RRF 计算后填充
        })

    # 3. 过滤 disable（禁用标签匹配即排除）
    # 兼容 DISABLE_TAG_POOL 下划线格式（cli_only→匹配"cli only"或"cli_only"）
    query_lower = query.lower().replace("_", " ")
    valid = []
    for item in candidates:
        hit = False
        for d in item["disable_tags"]:
            d_lower = d.lower().replace("_", " ")
            # 支持: cli_only → "cli"+"only" 都出现在 query 中
            parts = d_lower.split()
            if len(parts) > 1 and all(p in query_lower for p in parts):
                hit = True
                break
            # 或精确匹配
            if d_lower in query_lower:
                hit = True
                break
        if not hit:
            valid.append(item)

    if not valid:
        return []

    # 4. RRF 融合：按 sparse_score 降序赋予 sparse rank
    # （dense_rank 已在 Chroma 结果中固化）
    sparse_sorted = sorted(valid, key=lambda x: x["sparse_score"], reverse=True)
    for i, item in enumerate(sparse_sorted, start=1):
        item["sparse_rank"] = i

    # 5. 计算 RRF final_score = 1/(k + dense_rank) + 1/(k + sparse_rank)
    # 5+. trigger_tags 命中加分：query 含触发词则 +0.005（加法叠加，避免 dense 主导时 boost 无效）
    TRIG_HIT_BONUS = 0.010
    for item in valid:
        sr = item["sparse_rank"]
        dr = item["dense_rank"]
        rrf_score = 1.0 / (RRF_K + dr) + 1.0 / (RRF_K + sr)
        if any(t.lower() in query_lower for t in item["trigger_tags"]):
            rrf_score += TRIG_HIT_BONUS
        item["final_score"] = round(rrf_score, 4)

    # 6. 按 final_score 排序
    valid.sort(key=lambda x: x["final_score"], reverse=True)

    # 7. 路由门禁过滤（进检索后、返回前）：基于原始 query 剔除无资格的重型技能。
    #    仅影响 routing.get_gated_skills() 命中的技能，其余一律放行。
    gated = [it for it in valid if routing.is_query_allowed_for_skill(query, it["skill_name"])]
    return gated[:top_k]


# ── 冷启动预热（模块导入时初始化 Chroma）────────────────────────
# 预热失败不阻止导入，设 _healthy=False 让调用方降级
try:
    _get_collection()
    _healthy = True
except Exception:
    _healthy = False


# ── CLI ────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import sys
    q = " ".join(sys.argv[1:]) or "部署 flask"
    results = search(q)
    print(f"🔍 {q}")
    for r in results:
        trig = ", ".join(r["trigger_tags"][:3])
        print(f"  {r['final_score']:.3f}  {r['skill_name']:35s}  "
              f"d={r['dense_score']:.3f}  s={r['sparse_score']:.3f}  "
              f"dr={r['dense_rank']}  sr={r['sparse_rank']}  [{trig}]")
