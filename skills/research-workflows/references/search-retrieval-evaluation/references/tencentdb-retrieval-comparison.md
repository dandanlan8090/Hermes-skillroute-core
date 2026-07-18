# TencentDB-Agent-Memory vs Hermes vdb 检索能力对比

来源：2026-07-11 深度分析 （https://github.com/TencentCloud/TencentDB-Agent-Memory, v0.3.6）

## 项目定位

OpenClaw 的长期记忆插件，四层管线（L0→L1→L2→L3）。  
有两个后端：SQLite 本地（sqlite-vec + FTS5）和 TCVDB（腾讯云向量数据库）。

本文件聚焦检索层对比，不涉及记忆系统管线本身。

## 检索链路对比

### Hermes vdb（当前）

```
query → BGE-M3 云端稠密 (1024d) → Chroma HNSW cosine (top-16)
     → sparse lexical (trigger_tags 词重叠) → 0.6×dense + 0.4×sparse
     → disable 过滤 → top-5
```

文件：`~/.hermes/vdb/{matcher,embed,indexer,sparse}.py`

### TencentDB-Agent-Memory SQLite 后端

```
query → (FTS5 BM25 关键词) + (sqlite-vec 向量检索) 并行
     → RRF rank fusion
     → 可选 embedding 不可用时降级为纯 FTS5
```

文件：`src/core/store/sqlite.ts` `src/core/hooks/auto-recall.ts`

### TencentDB-Agent-Memory TCVDB 后端

```
query → server-side embedding (Collection 配置自动编码)
     → client-side BM25 sparse vector (BM25LocalEncoder, jieba-wasm 分词)
     → TCVDB /document/hybridSearch (ann + match + rerank)
     → rerank = { method: "rrf", k: 60 }
     → embedding 不可用时降级为 embeddingItems 纯向量搜索
```

文件：
- `src/core/store/tcvdb.ts` — `searchL1HybridAsync()` 核心实现在 671-731 行
- `src/core/store/tcvdb-client.ts` — `hybridSearch()` HTTP 客户端
- `src/core/store/bm25-local.ts` — `BM25LocalEncoder` (纯 TS, 用 `@tencentdb-agent-memory/tcvdb-text`)
- `src/core/store/bm25-client.ts` — BM25 Python sidecar HTTP 客户端 (旧版，已被 local 替代)
- `src/core/store/factory.ts` — store 创建工厂 (sqlite/tcvdb 二选一)

## 逐维度对比

| 维度 | Hermes vdb | TencentDB-Agent-Memory | 判断 |
|------|-----------|----------------------|------|
| dense 检索 | BGE-M3 + Chroma HNSW cosine, 1024d | sqlite-vec 或 TCVDB server-side embedding | Hermes 够用 |
| sparse 检索 | 手写 token overlap，仅 trigger_tags | FTS5 BM25 或 jieba BM25 sparse vector | Tencent 更标准 |
| 融合方式 | 固定权重 0.6/0.4 | RRF rank fusion (k=60) | **RRF 更稳，建议借鉴** |
| 中文分词 | 中文按字 | @node-rs/jieba (Rust) 或 tcvdb-text (jieba-wasm) | 但对 trigger_tags 场景收益有限 |
| 降级策略 | vdb 不健康返回空列表 | embedding 不可用时退 FTS，FTS 不可用时退纯向量 | **Tencent 更工程化，建议借鉴** |
| 能力探测 | is_healthy() 粗粒度布尔 | getCapabilities() 四维：vector/fts/hybrid/sparse | **Tencent 更清楚，建议借鉴** |
| 查询清洗 | 基本无 | sanitizeText() 去元数据/图片/base64 噪声 | **值得借鉴** |
| 超时控制 | embedding 调用无显式 per-call timeout/retry | embedding timeout/retry，recall timeout | **值得借鉴** |
| 索引内容 | trigger_tags + name + desc + 标题 | 全量 memory 文本/对话内容 | 用途不同，不必照搬 |
| 适合 Hermes | 轻量，58-71 skill 场景 | 太重，依赖 Node >=22.16 + TCVDB | 只吸收局部思想 |

## 持借鉴项（具体建议）

### 1. RRF 替代固定 0.6/0.4 加权

当前两个分数的标度不可比（dense cosine ∈ [0,1], sparse 无界）。  
RRF 只看排名，天然规避标度问题。

对 Hermes 更合适的做法：
- Chroma dense 召回 top16 → 得 dense_rank
- sparse 对候选重排 → 得 sparse_rank
- RRF: `1/(k + dense_rank) + 1/(k + sparse_rank)` with k=60
- disable 过滤保持现状

2026-07-11 benchmark 验证：RRF Top-1 78.7% vs 0.6/0.4 的 75.4%（+2/61）。

### 2. 能力探测

当前 Hermes 在模块启动时设 `_healthy`，之后不再更新。  
建议加轻量 `status()`：

```python
def status() -> dict:
    return {
        "chroma_ok": _collection is not None,
        "cloud_embedding_ok": _cloud_check(),
        "state_stale": check_index_stale()[0],
        "skills_count": len(chroma_metadata),
        "healthy": _healthy,
    }
```

### 3. 降级策略

当前 `_healthy == False` 时 `search()` 直接返回 `[]`。  
建议降级到路由表逐 key 匹配 + skills_list 扫描，类似于 SOUL.md 的检索流程 Step 2→3。

### 4. IDF 增强 sparse（不引入 jieba）

当前 sparse 只做词重叠计数，相同词在不同 skill 间权重一样。  
在 `build_index` 时计算全局文档频率 df，sparse 分改成：

```python
score = sum(log(1 + tf(t, d)) * idf(t) for t in query_tokens)
```

不引入 jieba（trigger_tags 已是最优关键词切割），不引入 BM25 服务。

## 不建议借鉴的部分

1. **不接记忆系统** — Hermes 当前记忆够用，外部记忆钩子不一定可靠
2. **不引入 TCVDB** — 对几十 skill 规模太重
3. **不引入 node/TypeScript 依赖** — 与 Python vdb 栈不兼容
4. **不改 server-side embedding** — 当前 BGE-M3 云端已稳定
5. **不引入 FTS5** — 和 Chroma 两套存储不自然，维护成本高

## 文件取证

### TCVDB hybridSearch 核心实现（`tcvdb.ts` 671-731）

```typescript
// searchParams: ann (dense) + match (sparse) + rerank
searchParams.ann = [{
  fieldName: "text",  // 或 L0 用 "message_text"
  data: [queryText],  // embeddingItems — server-side embedding
  limit: topK,
}];
searchParams.match = [{
  fieldName: "sparse_vector",
  data: [sparse[0]],  // BM25LocalEncoder.encodeQueries()
  limit: topK,
}];
searchParams.rerank = { method: "rrf", k: 60 };

// 降级：当 BM25 不可用时退化为纯 dense
// if (!match) → embedOnly = { embeddingItems: [queryText], limit: topK }
```

### BM25 写入（upsert 时计算 sparse_vector）

```typescript
// bm25-local.ts — encodeTexts() 用 BM25Encoder.default("zh")
// tcvdb.ts 430-436 行 — 写入 sparse_vector 到文档
if (this.bm25Encoder) {
  const sparse = this.bm25Encoder.encodeTexts([record.content]);
  if (sparse.length > 0 && sparse[0].length > 0) {
    doc.sparse_vector = sparse[0];
  }
}
```

### SQLite FTS5 + sqlite-vec 双索引

`src/core/store/sqlite.ts` 使用 `CREATE VIRTUAL TABLE IF NOT EXISTS fts5_memories USING fts5(...)`  
并行执行 FTS5 BM25 查询和向量查询后 RRF 融合（`auto-recall.ts` 641 行）。

**注意**：FTS5/BM25 与 Hermes 当前 sparse.py 不兼容：
- 索引内容不同（全文 vs 仅 trigger_tags）
- 语言栈不同（TS vs Python）
- 存储不同（SQLite vs Chroma metadata）
