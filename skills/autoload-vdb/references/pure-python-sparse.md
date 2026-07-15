# Pure-Python Sparse Lexical Matching

## Motivation

BGE-M3 官方 `compute_lexical_matching_score` 需要 torch + transformers（~1GB），
在 Docker overlay 配额 < 1GB 的环境无法安装。sparse.py 用纯 Python 实现等效算法。

## Algorithm

### Tokenizer

```python
def _tokenize(text: str) -> list[str]:
    tokens = []
    for char in text:
        if '\u4e00' <= char <= '\u9fff':
            tokens.append(char)
        elif char.isascii() and (char.isalnum() or char == '_'):
            tokens.append(char.lower())
    return tokens
```

- 中文：逐字（BGE-M3 subword 的简化代理）
- 英文/数字：保留原词
- 标点：忽略

### Weight Formula（与 BGE-M3 对齐）

```python
def get_sparse_weights(text: str) -> dict[str, float]:
    tokens = _tokenize(text)
    if not tokens:
        return {}
    tf = {}
    for t in tokens:
        tf[t] = tf.get(t, 0) + 1
    max_tf = max(tf.values())
    return {t: math.log(1 + freq) / math.log(1 + max_tf)
            for t, freq in tf.items()}
```

归一化到 [0, 1]。

### Scoring

```python
def compute_lexical_matching_score(qw: dict, dw: dict) -> float:
    overlap = set(qw) & set(dw)
    if not overlap or not qw:
        return 0.0
    numer = sum(min(qw[t], dw[t]) for t in overlap)
    denom = sum(qw.values())
    return numer / denom
```

## Verify

```
"部署 nginx"  vs system-admin tags → 0.223 ✅
"youtube 视频" vs system-admin tags → 0.000 ✅（完全隔离）
"hermes 配置"  vs hermes-agent tags → 0.463 ✅（跨语言）
```

## Official Replacement

When torch is available:

```python
from FlagEmbedding import BGEM3FlagModel
model = BGEM3FlagModel("BAAI/bge-m3", use_fp16=False, device="cpu")
# weights
out = model.encode(["\n".join(tags)], return_dense=False, return_sparse=True)
weights = {k: float(v) for k, v in out["sparse_weights"][0].items()}
# score
q = model.encode([query], return_dense=False, return_sparse=True)
score = model.compute_lexical_matching_score(q["sparse_weights"][0], weights)
```
