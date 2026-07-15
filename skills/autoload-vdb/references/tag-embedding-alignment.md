# Tag Embedding Alignment Technique

## Problem

BGE-Small-ZH (and most embedding models) are highly sensitive to **text format/sentence structure**.
Embedding a bare tag word like "部署" produces a vector in a very different region of the space
than the embedding of "用户需求：部署 nginx 到 ubuntu" (the query template). Cosine similarity
between the two is only ~0.56, barely above random, even though semantically they overlap.

## Solution: Context-Aligned Tag Embeddings

During indexing (`indexer.py`), each trigger tag is wrapped in the **same query-side template**
before embedding:

```
embedder.embed(["用户需求：部署"])
embedder.embed(["用户需求：服务器"])
...
```

This aligns the tag vectors with query vectors in the embedding space, since queries at match time
also use `"用户需求：{query}"`. The result: tag-query cosine similarities jump from ~0.56 to ~0.75-0.97.

## Implementation

- `indexer.py` line ~178: `tag_query_texts = [_build_query_text(t) for t in tag_list]`
- `matcher.py` `_tag_score()`: uses precomputed tag embeddings, compares with query vector

## Key Insight

This is a general principle for any embedding model used in a query-document setup:
**align the context of precomputed auxiliary embeddings with the query context, not the document context.**
For tag scoring specifically, tags serve as "mini-queries" — they should live in query-space, not doc-space.

## When to Rebuild

Any change to `_build_query_text()` or the embedding model requires rebuilding the tag index:
```bash
cd ~/.hermes/vdb && source .venv/bin/activate && PYTHONPATH=$PWD python3 -c \
  "from indexer import build_index; build_index(force=True)"
```
