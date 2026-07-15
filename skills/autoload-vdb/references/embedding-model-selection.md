# 向量模型选型方法论

本次会话的关键收获——选 embedding 模型时跨语言能力是隐性硬指标。

## 核心经验

**BGE-Small-ZH 对中英跨语言 = 残废**。
中文 query "我想看 Hermes 配置" vs 英文 description "Skill for configuring, extending, or contributing to Hermes Agent"：
- BGE-Small-ZH（本地 512d）：跨语言相似度 0.18~0.35，hermes-agent 技能不在 top-16
- nv-embedqa-e5-v5（NVIDIA API 1024d）：跨语言相似度 0.44~0.55，hermes-agent 正确命中 top-1

**中文向量模型 vs 多语言向量模型的核心区别**：
- BGE-Small-ZH 训练语料以中文为主，对英文 description 的向量化丢语义
- nv-embedqa-e5-v5 / BGE-M3 训练语料多语言对齐，跨语言 query ↔ doc 也能高相似

## 评估方法

```python
# 跨语言能力探针（3 分钟测出）：
import requests, numpy as np

# 准备 3-5 对跨语言样本
pairs = [
    ("用户需求：部署 flask 到 ubuntu", "System administration tasks: service installation"),
    ("用户需求：调试 python 报错", "Skill for configuring, extending, or contributing to Hermes Agent"),
    ("用户需求：查地图", "POI search and route planning"),
]

# 调用候选模型（query type + passage type）
for model in ["BAAI/bge-small-zh-v1.5", "nvidia/nv-embedqa-e5-v5"]:
    vecs = api_embed_batch(model, [t for pair in pairs for t in pair])
    sims = [cosine(vecs[i*2], vecs[i*2+1]) for i in range(len(pairs))]
    print(f"{model}: avg_cross_sim={np.mean(sims):.3f}")
    # 评估标准：avg > 0.4 表示跨语言合格
```

**通过阈值**：avg_cross_sim > 0.40
**失败阈值**：avg_cross_sim < 0.25

## 模型选型决策树

```
需要多语言（中英混 description）？
├─ 是
│  ├─ 有 NVIDIA API Key？
│  │  ├─ 是 → nv-embedqa-e5-v5（1024d, 6s 延迟）
│  │  └─ 否 → 本地部署 BGE-M3（需 GPU，2-3GB 内存）
│  └─ 跨语言 + 极低延迟
│     └─ BGE-M3 本地部署 + L4 GPU（200ms 级别）
└─ 否（纯中文）
   ├─ 性能敏感？
   │  ├─ 是 → BGE-Small-ZH（512d, 8ms 延迟）
   │  └─ 否 → BGE-Large-ZH（1024d, 50ms 延迟）
```

## 量化对比表

| 模型 | 维度 | 中文 | 跨语言 | 本地延迟 | API 延迟 | 依赖 |
|------|------|------|--------|----------|----------|------|
| BGE-Small-ZH-v1.5 | 512 | ✅ | ❌ 0.18 | 8ms | - | fastembed |
| BGE-Large-ZH | 1024 | ✅✅ | ⚠ 0.30 | 50ms | - | fastembed |
| nv-embedqa-e5-v5 | 1024 | ✅ | ✅ 0.44 | - | 6s | NVIDIA API |
| nv-embed-v1 | 4096 | ✅ | ✅ 0.45 | - | 6.7s | NVIDIA API |
| BGE-M3 | 1024 | ✅ | ✅ 0.50+ | 200ms+ | - | fastembed/gpu |
| jina-embeddings-v3 | 1024 | ✅ | ✅ 0.48 | - | - | fastembed |

## fastembed 兼容性

BGE-M3 在 fastembed 0.8.0 不支持（截至 2026-07）。
可选替代：jinaai/jina-embeddings-v3（1024d，多语言）。
需升级 fastembed 至 0.10+ 或换用 sentence-transformers。

## 红线

- **永远不要假设本地 BGE-ZH 能处理英文 description**——必须实测跨语言相似度
- **API 延迟是网络往返 + 推理时间，6s 是 NVIDIA 平台当前下界**
- **缓存只对重复 query 有效**，每次新 query 都要重新调用 API
- **BGE-M3 本地部署需要 GPU**，纯 CPU 推理 200-500ms 不实用

## 相关文件

- `vdb.py` — 当前架构 A 实现（单文件 ~200 行）
- `core.py / embed.py / indexer.py / matcher.py` — 旧架构 B（已废弃但保留）
- `config.yaml` — 旧架构 B 的权重配置
