"""
匹配器 — query 分类短路 → 白名单直达 → Chroma 稠密召回 → sparse 重打分 → RRF 融合 → disable 过滤。

流程:
  0. (PATCH A) dcg-inspired query 分类：问候/短词不在映射表 → 直接短路，省 BGE-M3 API
  0. (PATCH B) dcg-inspired 白名单直达：精确命中技能名/trigger → 跳过 RRF，直达返回
  1. query → 云端 BGE-M3 稠密向量
  2. Chroma cosine 距离召回 top-K 候选技能（dense rank）
  3. 每个候选: 计算本地 sparse 匹配分（trigger_tags vs query）
  4. disable 标签命中则过滤
  5. 在有效候选中按 sparse 分排 sparse rank
  6. RRF = 1/(k + dense_rank) + 1/(k + sparse_rank)
  7. (PATCH C) route_stage 标记：fast_path / rrf / gated_filter
  8. 路由门禁过滤，返回 top-K

回滚: 顶部 USE_QUERY_CLASSIFICATION / USE_FAST_PATH / USE_ROUTE_ANNOTATION 设 False

Feature flags (2026-07-16 dcg-inspired):
  USE_QUERY_CLASSIFICATION — 借鉴A：query 分类短路层，对应 dcg SpanKind 状态机
  USE_FAST_PATH           — 借鉴B：白名单直达，对应 dcg SAFE_PATTERNS 短路
  USE_ROUTE_ANNOTATION    — 借鉴C：路由阶段标记，对应 dcg confidence 只降级不前置加权
"""

import json
from typing import List

import chromadb
from chromadb.config import Settings

from embed import get_cloud_dense, calculate_sparse_score
from indexer import VDB_DIR, CHROMA_DIR, COLLECTION_NAME, TOP_K_CANDIDATES
import routing
import re
import logging

logger = logging.getLogger(__name__)

# PATCH: dcg-inspired feature flags (2026-07-16)
USE_QUERY_CLASSIFICATION = True   # 借鉴A：query 分类短路
USE_FAST_PATH = True              # 借鉴B：白名单直达
USE_ROUTE_ANNOTATION = True       # 借鉴C：路由阶段标记

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

# PATCH: dcg-inspired trigger mapping（从 Chroma 元数据构建，用于 fast_path + query 分类）
_TRIGGER_MAPPING: dict[str, str] = {}  # {触发词/技能名 → skill_name}


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


# ── 触发词映射表（借鉴A+B 共用）─────────────────────────────────────

def _build_trigger_mapping() -> None:
    """从 Chroma 全量元数据构建 {触发词/技能名 → skill_name} 映射表。

    调用时机：模块预热成功后一次；_TRIGGER_MAPPING 在 fast_path 和
    query 分类的单 token 查表中查询，不依赖实时检索结果。
    """
    global _TRIGGER_MAPPING
    if not _healthy:
        return
    try:
        collection = _get_collection()
        # 拉取全部记录的 metadata（不含 embedding，轻量）
        all_data = collection.get(include=["metadatas"])
        mapping: dict[str, str] = {}
        for meta in all_data.get("metadatas", []):
            if meta is None:
                continue
            skill_name = meta.get("skill_name", "").strip().lower()
            if not skill_name:
                continue
            # 技能名本身（最高优先级）
            mapping[skill_name] = skill_name
            # trigger_tags 中的别名/触发词
            try:
                triggers = json.loads(meta.get("trigger_tags", "[]"))
                for tag in triggers:
                    tag_clean = tag.strip().lower()
                    if tag_clean:
                        mapping[tag_clean] = skill_name
            except (json.JSONDecodeError, TypeError):
                pass
        _TRIGGER_MAPPING = mapping
        logger.info("dcg: trigger mapping loaded (%d entries)", len(mapping))
    except Exception as exc:
        logger.warning("dcg: trigger mapping build failed: %s", exc)


def refresh_trigger_mapping() -> None:
    """公开入口：手动刷新触发词映射表（技能元数据变更后调用）。"""
    _build_trigger_mapping()


# PATCH: dcg-inspired — query 分类短路（借鉴A，对应 dcg SpanKind 状态机）
def _classify_query(query: str) -> str:
    """快速判断 query 是否属于检索型。

    返回值:
      - 'retrieval'     → 正常进完整检索流水线
      - 'non_retrieval' → 直接短路返回 []（省一次 BGE-M3 API 调用）

    规则（确定性、fail-open）:
      1. 完整 query 在映射表 → retrieval（避免 "docker" 误判）
      2. 问候语模式 → non_retrieval
      3. 单 token 且是短词（中≤2 或 英数≤4）且在映射表 → retrieval；
         不在映射表 → non_retrieval
      4. 多 token 或长短语 → retrieval（fail-open）
    """
    q = query.strip()
    if not q:
        return 'non_retrieval'

    # 规则1：完整输入精确匹配映射表（最大确定性）
    if q.lower() in _TRIGGER_MAPPING:
        return 'retrieval'

    # 规则2：问候/元指令（覆盖“你好吗”“你好呀”等变体）
    if re.search(r'^(你好|hi|hello|hey|谢谢|感谢|ok|好的|在吗|在不在)', q, re.I):
        return 'non_retrieval'

    # 提取有效 token（字母数字 + 中文连续字符）
    tokens = re.findall(r'[a-zA-Z0-9\u4e00-\u9fa5]+', q)
    meaningful = [t for t in tokens if len(t) >= 2 or t.isalnum()]

    # 规则3：单 token → 短词不走检索（除非命中映射表）
    if len(meaningful) == 1:
        token = meaningful[0]
        if token in _TRIGGER_MAPPING:
            return 'retrieval'
        # 短中文（≤2字）或短英文/数字（≤4位）→ 闲聊式，短路
        is_short_chinese = re.fullmatch(r'[\u4e00-\u9fa5]{1,2}', token)
        is_short_alnum = re.fullmatch(r'[a-zA-Z0-9]{1,4}', token)
        if is_short_chinese or is_short_alnum:
            return 'non_retrieval'
        # 长短语（如"帮我写脚本"）→ 走检索
        return 'retrieval'

    # 规则4：多 token / 复杂查询 → 走检索（fail-open）
    return 'retrieval'


# PATCH: dcg-inspired — 白名单直达（借鉴B，对应 dcg SAFE_PATTERNS 短路）
def _fast_path(query: str) -> list | None:
    """高置信精确命中时跳过 RRF，直达返回。

    策略（对应 dcg 白名单优先）:
      1. query 整体精确命中 skill_name / trigger
      2. 任一独立词命中 trigger
      3. 全不命中 → None，走正常 RRF

    返回格式与 search() 一致，带 route_stage='fast_path'。
    """
    q = query.strip().lower()
    if not q or not _TRIGGER_MAPPING:
        return None

    # 1. 完整输入精确匹配
    if q in _TRIGGER_MAPPING:
        return [_build_fast_result(_TRIGGER_MAPPING[q])]

    # 2. 独立有义词匹配
    tokens = re.findall(r'[a-zA-Z0-9\u4e00-\u9fa5]+', q)
    meaningful = [t for t in tokens if len(t) >= 2 or t.isalnum()]
    for token in meaningful:
        if token in _TRIGGER_MAPPING:
            skill_name = _TRIGGER_MAPPING[token]
            logger.info("dcg: fast-path by token '%s' -> '%s'  query=%s",
                        token, skill_name, q[:60])
            return [_build_fast_result(skill_name)]

    return None


def _build_fast_result(skill_name: str) -> dict:
    """构造 fast path 返回条目（补齐 search() 返回格式的最小字段集）。"""
    return {
        "skill_name": skill_name,
        "final_score": 1.0,
        "route_stage": "fast_path",
    }


# ── 匹配 ─────────────────────────────────────────────────────────

def search(query: str, top_k: int = 5) -> List[dict]:
    """主入口：稠密→sparse→RRF→过滤→排序。

    vdb 不可用时（chroma 损坏 / 未构建）返回空列表，不抛异常。
    """
    if not _healthy:
        return []

    # ---------- PATCH A: dcg-inspired — query 分类短路 ----------
    if USE_QUERY_CLASSIFICATION:
        cls = _classify_query(query)
        if cls == "non_retrieval":
            logger.info("dcg: query non-retrieval, short-circuit (saved BGE-M3): %s", query[:50])
            return []

    collection = _get_collection()

    # ---------- PATCH B: dcg-inspired — 白名单直达（在 dense 召回后、RRF 前） ----------
    if USE_FAST_PATH:
        fast_result = _fast_path(query)
        if fast_result is not None:
            return fast_result

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

    # ---------- PATCH C: dcg-inspired — 路由阶段标记 ----------
    if USE_ROUTE_ANNOTATION:
        for it in gated:
            it["route_stage"] = "rrf"

    return gated[:top_k]


# ── 冷启动预热（模块导入时初始化 Chroma）────────────────────────
# 预热失败不阻止导入，设 _healthy=False 让调用方降级
try:
    _get_collection()
    _healthy = True
    _build_trigger_mapping()  # PATCH: dcg-inspired - 构建触发词映射表
except Exception:
    _healthy = False


# ── CLI ────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import sys
    q = " ".join(sys.argv[1:]) or "部署 flask"
    results = search(q)
    print(f"🔍 {q}")
    for r in results:
        stage = r.get("route_stage", "?")
        trig = ", ".join(r.get("trigger_tags", [])[:3])
        if stage == "fast_path":
            print(f"  FAST {r['skill_name']:35s}  stage={stage}")
        else:
            print(f"  {r['final_score']:.3f}  {r['skill_name']:35s}  "
                  f"d={r['dense_score']:.3f}  s={r['sparse_score']:.3f}  "
                  f"dr={r['dense_rank']}  sr={r['sparse_rank']}  [{trig}]  stage={stage}")
