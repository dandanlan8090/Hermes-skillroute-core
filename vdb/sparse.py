"""
Sparse lexical embedding — 纯 CPU 本地, 无需 torch, 无额外依赖。

算法对齐 BGE-M3 `compute_lexical_matching_score`:
  1. Tokenize: 中文按字 + 英文/数字按词 (BPE 风格代理)
  2. Weight: log(1 + tf)          ← BGE-M3 内部公式
  3. IDF:    idf(t) × weight      ← P2 IDF 增强（索引时传入 idf_map）
  4. Score:  Σ w_q[t] × w_d[t]    for token ∈ overlap

v2.1 leading word boost:
  - 命中 LEADING_WORD_BOOST 池中 token，权重 ×2
  - 池子与 NEW_SKILL_TEMPLATE.md §leading word 词汇库对齐
  - 命中判断：trigger_tags 中含 leading word 的子串

P2 IDF:
  - doc 侧: weight = log(1+tf) × idf(t) × (leading_boot 可选)
  - query 侧: weight = log(1+tf) 不变（无 IDF）
  - idf 在 build_index 时计算并存入 Chroma metadata tag_sparse
  - 检索时无需 IDF，doc_weights 已固化
"""

import math, re
from typing import Dict, Iterable, Optional


def _tokenize(text: str) -> list[str]:
    """将文本拆分为 token 列表。

    中文单字 + 英文词/数字词组（保持数字完整）。
    """
    tokens = []
    # 按词拆分：匹配中文单字 OR 英文词 OR 数字
    for part in re.findall(r"[\u4e00-\u9fff]|[a-zA-Z]+|[0-9]+(?:\\.?[0-9])*", text):
        if re.match(r"[\u4e00-\u9fff]", part):
            # 中文单字逐个拆开（保证细粒度匹配）
            tokens.extend(list(part))
        else:
            tokens.append(part.lower())
    return tokens


def _compute_weight(tf: int) -> float:
    """log(1 + tf) — BGE-M3 权重公式。"""
    return math.log(1.0 + tf)


# ── leading word 池子 (v2.1) ────────────────────────────────────────
# 来自 NEW_SKILL_TEMPLATE.md §leading word 词汇库（21 个初始词）
# query 端命中池子任意 token，sparse 权重 ×2
LEADING_WORD_POOL = {
    # methodology
    "red", "green", "fog", "war", "tracer", "bullet", "root", "cause",
    "verify", "first", "sunk", "cost", "ship", "it", "ground", "truth",
    # workflow
    "dispatch", "gate", "handoff", "slice",
    # tool
    "probe", "fire", "scaffold",
    # integration
    "bridge", "mirror",
}
LEADING_WORD_BOOST = 2.0


def _is_leading_token(token: str) -> bool:
    """token 是否属于 leading word 池。"""
    return token.lower() in LEADING_WORD_POOL


def get_sparse_weights(
    text: str,
    leading_word_boost: float = LEADING_WORD_BOOST,
    boost_pool: Optional[Iterable[str]] = None,
    idf_map: Optional[Dict[str, float]] = None,
) -> Dict[str, float]:
    """对文本计算 sparse lexical weights（token -> weight 字典）。

    参数:
        text: 输入文本（trigger_tags 或 query）
        leading_word_boost: leading word 命中后权重乘数（默认 2x）
        boost_pool: 自定义 leading word 集合；None 用默认池
        idf_map: {token: idf} 字典（索引端传入）。None 则无 IDF 增强。
    返回:
        {token: weight} 字典（可 JSON 序列化）
    """
    tokens = _tokenize(text)
    if not tokens:
        return {}
    # term frequency
    tf: Dict[str, int] = {}
    for t in tokens:
        tf[t] = tf.get(t, 0) + 1
    # weight = log(1+tf) × idf (if provided) × leading_boost (if hit)
    pool = set(boost_pool) if boost_pool is not None else LEADING_WORD_POOL
    weights = {}
    for token, freq in tf.items():
        w = _compute_weight(freq)
        if idf_map is not None:
            w *= idf_map.get(token, 1.0)
        if token.lower() in pool:
            w *= leading_word_boost
        weights[token] = w
    return weights


def compute_lexical_matching_score(
    query_weights: Dict[str, float],
    doc_weights: Dict[str, float],
) -> float:
    """与 FlagEmbedding compute_lexical_matching_score 算法对齐。

    score = Σ query_weight[t] × doc_weight[t]   for overlapping t

    返回 0–1 归一化分数。
    """
    if not query_weights or not doc_weights:
        return 0.0
    overlap = set(query_weights) & set(doc_weights)
    if not overlap:
        return 0.0
    raw = 0.0
    q_norm = 0.0
    d_norm = 0.0
    for t in query_weights:
        q_norm += query_weights[t] ** 2
    for t in doc_weights:
        d_norm += doc_weights[t] ** 2
    for t in overlap:
        raw += query_weights[t] * doc_weights[t]
    return raw / (math.sqrt(q_norm) * math.sqrt(d_norm) + 1e-8)


def compute_idf_from_skills(
    skills_data: list[tuple],
    extract_desc_zh: bool = True,
) -> Dict[str, float]:
    """从所有技能的 trigger_tags + description 中文短语计算全局 token IDF 映射。

    参数:
        skills_data: [(name, path, doc_text, trigger_tags_list, disable_list, desc), ...]
        extract_desc_zh: 是否提取 description 中的中文短语（≥2字）补充到 IDF
    返回:
        {token: idf_value} — idf(t) = 1 + log(N / (df(t) + 1))
    """
    N = len(skills_data)
    df: Dict[str, int] = {}
    for item in skills_data:
        if len(item) >= 6:
            _, _, _, trig, _, desc = item[:6]
        else:
            _, _, _, trig, _ = item[:5]
            desc = ""
        seen = set()
        # trigger_tags
        combined = "\n".join(trig)
        for t in _tokenize(combined):
            if t not in seen:
                seen.add(t)
                df[t] = df.get(t, 0) + 1
        # description 中文短语（≥2字连续中文）
        if extract_desc_zh and desc:
            zh_phrases = re.findall(r"[\u4e00-\u9fff]{2,}", desc)
            if zh_phrases:
                for t in _tokenize(" ".join(zh_phrases)):
                    if t not in seen:
                        seen.add(t)
                        df[t] = df.get(t, 0) + 1
    idf_map = {}
    for token, doc_count in df.items():
        idf_map[token] = 1.0 + math.log(N / (doc_count + 1))
    return idf_map
