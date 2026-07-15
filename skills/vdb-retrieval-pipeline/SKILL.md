---
name: vdb-retrieval-pipeline
description: >-
  路由门禁层(routing.py 专名门禁, 防重型技能误注入)。Chroma + SiliconFlow BAAI/bge-m3 混合检索管道。云端稠密向量(name+desc+tags) + 本地
  sparse关键词权重(trigger_tags词权重 + desc中文短语, IDF增强)。融合: RRF(K=60)=1/(60+dense_rank)+1/(60+sparse_rank)+trigger命中+0.010 (已弃用 0.6dense+0.4sparse)。索引 99 技能。
  Hermes 技能检索核心基础设施。
version: 1.0.0
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
        - vdb
        - 技能检索
        - 向量数据库
        - 技能匹配
        - skill retrieval
        - skill search
        - 稠密检索
        - 混合检索
        - 重建索引
        - rebuild index
        - chroma
        - bge-m3
        - 硅基流动
        - siliconflow
      disable:
        - deep_review
        - code_development
    skill_type: infrastructure
    priority: highest
---

# vdb-retrieval-pipeline — Hermes 技能混合检索管道

## 架构

```
query
  │
  ├──▶ 云端 (SiliconFlow API)
  │     BAAI/bge-m3 ── 稠密向量 (1024d)
  │     Chroma hnsw cosine 召回 top-16
  │
  ├──▶ 本地 (sparse.py, 纯 Python, 无 torch)
  │     trigger_tags 词权重 + desc 中文短语 ── IDF 增强 ── compute_lexical_matching_score
  │
  └──▶ RRF(K=60): final = 1/(60+dense_rank) + 1/(60+sparse_rank) + (trigger命中 ? 0.010 : 0)
       → disable 过滤 → top-5
```

## 文件位置

| 文件 | 作用 |
|------|------|
| `~/.hermes/vdb/sparse.py` | 纯 Python lexical weights，无额外依赖 |
| `~/.hermes/vdb/embed.py` | 云端稠密 API + 本地 sparse 接口 |
| `~/.hermes/vdb/indexer.py` | Chroma 索引构建 |
| `~/.hermes/vdb/matcher.py` | 检索入口 `search(query, top_k=5)` |
| `~/.hermes/vdb/__init__.py` | 包入口，导出 `build_index` / `search` |
| `~/.hermes/vdb/chroma/` | Chroma 持久化存储（~1.2MB） |

## 依赖

```
pip install chromadb openai python-dotenv
```

`sparse.py` 无依赖（纯 Python）。

## 常规操作

### 检查索引状态

```python
from indexer import check_index_stale
stale, reason = check_index_stale()
print(f"索引过期: {stale}, 原因: {reason}")
```

### 重建索引（技能更新后）

```python
from indexer import build_index
build_index(force=True)
```

### 检索

```python
from matcher import search
results = search("部署 flask", top_k=5)
# 返回: [{"skill_name", "final_score", "dense_score", "sparse_score", ...}]
```

### 修改模型/提供方

只改 `embed.py` 中 `_get_client()` 的 `base_url` + `api_key` 来源。

## 融合策略（RRF，非加权求和）

`matcher.py` 实际用 **RRF 倒数排名融合**（2026-07-11 起弃用 `VEC_WEIGHT/SPARSE_WEIGHT` 的 0.6/0.4 加权）：

```python
# matcher.py
RRF_K = 60
TRIG_HIT_BONUS = 0.010   # trigger 命中加法加成
# final = 1/(RRF_K + dense_rank) + 1/(RRF_K + sparse_rank) + (trigger命中 ? 0.010 : 0)
```

⚠ `VEC_WEIGHT=0.6` / `SPARSE_WEIGHT=0.4` 这两个常量**仅作旧权重保留，不参与实际打分**——调它们无效。融合逻辑以 RRF 为准。trigger 加成用**加法**不用乘法（乘法对 dense 主导 case 无效）。详见 `autoload-vdb` §5。

## 配置

API Key 从 `~/.hermes/.env` 读取 `SILICONFLOW_API_KEY`。
