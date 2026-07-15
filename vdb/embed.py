"""
Embedding 层 — 云端稠密 + 本地 sparse。

云端: SiliconFlow BAAI/bge-m3 生成 1024d 稠密向量（prose 模板拼接 name+leading+desc+branches）
本地: sparse.py 计算 trigger_tags + desc 中文短语的 lexical weights
v2.1: leading word 命中给 2x sparse 权重（见 sparse.LEADING_WORD_BOOST）
P2:   IDF 增强 — doc side weight = log(1+tf) x idf(t) x leading_boost
P2+:  description 中文短语（>=2字）合并到 tag_sparse 字典
        - 提取: re.findall(r'[\\u4e00-\\u9fff]{2,}', desc)
        - 与 trigger_tags 同一权重公式、同一 IDF 映射
        - 英文完全隔离，避免高频英文词稀释中文权重
P2+F: metadata 字段加权 — trigger_tags 中的 token ×1.2，description 中的 token ×0.8
        - 逻辑：trig 是人工精心挑选的精准触发词，应该比自动提取的 desc 短语更高权重
        - 跨字段重叠 token：分别加权后合并（不叠加 TF）
"""

import os, json, re
from typing import List, Optional
from dotenv import load_dotenv

from openai import OpenAI
from sparse import get_sparse_weights, compute_lexical_matching_score


load_dotenv()

_sf_client: Optional[OpenAI] = None


def _get_client() -> OpenAI:
    global _sf_client
    if _sf_client is None:
        _sf_client = OpenAI(
            base_url="https://api.siliconflow.cn/v1",
            api_key=os.getenv("SILICONFLOW_API_KEY"),
        )
    return _sf_client


def get_cloud_dense(texts: List[str]) -> List[List[float]]:
    """调用硅基流动 BAAI/bge-m3 获取稠密向量 (1024d)。"""
    resp = _get_client().embeddings.create(
        model="BAAI/bge-m3",
        input=texts,
    )
    return [item.embedding for item in resp.data]


def get_tag_sparse_dict(
    tag_list: List[str],
    idf_map: Optional[dict] = None,
    desc: str = "",
    trig_weight: float = 1.0,
    desc_weight: float = 1.0,
) -> str:
    """对 trigger_tags + description 中文短语计算 lexical weights，支持字段级加权。

    P2+: desc 中文短语（>=2字连续中文）与 trigger_tags 合并为同一个权重字典，
         同一套 IDF 映射，英文内容完全隔离。
    P2+F: trigger_tags 的 token ×trig_weight（默认1.0），description 的 token ×desc_weight（默认1.0）。
          可调参数：trig_weight 调高可让精准触发词占优，desc_weight 调低可压制自动提取噪声。
          当前实测 1.2/0.8 在 harder set 反降 → 暂留 1.0/1.0 等 metadata 补齐后再试。

    参数:
        tag_list: trigger_tags 字符串列表
        idf_map: 全局 IDF 映射
        desc: description 原文（自动提取中文短语）
        trig_weight: trigger_tags token 权重倍率（默认 1.2，更重视精准触发词）
        desc_weight: description token 权重倍率（默认 0.8，降低自动提取噪声）
    返回:
        JSON 序列化字符串，存入 Chroma metadata
    """
    # 1. trigger_tags 权重（×trig_weight）
    trig_combined = "\n".join(tag_list)
    trig_weights = get_sparse_weights(trig_combined, idf_map=idf_map)
    for t in trig_weights:
        trig_weights[t] *= trig_weight

    # 2. description 中文短语权重（×desc_weight）
    if desc:
        zh_phrases = re.findall(r"[\u4e00-\u9fff]{2,}", desc)
        if zh_phrases:
            desc_combined = " ".join(zh_phrases)
            desc_weights = get_sparse_weights(desc_combined, idf_map=idf_map)
            for t in desc_weights:
                desc_weights[t] *= desc_weight
            # 合并：trig 优先，desc 叠加
            for token, w in desc_weights.items():
                trig_weights[token] = trig_weights.get(token, 0) + w

    return json.dumps(trig_weights, ensure_ascii=False)


def calculate_sparse_score(query: str, doc_sparse_json: str) -> float:
    """计算 query 与技能预存 sparse 权重的词匹配得分。

    参数:
        query: 用户原始查询（无模板包装）
        doc_sparse_json: meta 中 tag_sparse 字段（JSON 字符串）
    返回:
        0-1 区间 lexical matching score
    """
    doc_weights = json.loads(doc_sparse_json)
    query_weights = get_sparse_weights(query)
    return compute_lexical_matching_score(query_weights, doc_weights)
