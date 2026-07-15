# 外部系统架构审查示例 — TencentDB-Agent-Memory 检索层评估

日期：2026-07-11
审查范围：仅检索层（embedding + store + recall + ranking），不评估记忆系统。

## 对方架构摘要

项目：TencentDB-Agent-Memory (v0.3.6)，OpenClaw 记忆插件。
检索层有两个后端：

### SQLite 本地路径
- `node:sqlite` + `sqlite-vec` (vec0 virtual table)
- 向量检索：vec0 cosine similarity
- FTS5 BM25 关键词检索（@node-rs/jieba 中文分词）
- 融合：FTS5 + 向量并行 → client-side RRF
- 降级：一方不可用时纯用另一方

### Tencent Cloud VectorDB 路径
- server-side dense embedding
- client-side BM25 sparse vector（@tencentdb-agent-memory/tcvdb-text）
- 融合：dense + sparse + RRF (k=60)，单次 hybridSearch API
- 降级：BM25 sidecar 不可用时回退纯 dense

### 关键源码位置
- `src/core/tools/memory-search.ts` — L1 记忆混合搜索工具
- `src/core/tools/conversation-search.ts` — L0 对话混合搜索工具
- `src/core/hooks/auto-recall.ts` — 自动召回管道（含降级逻辑）
- `src/core/store/sqlite.ts` — SQLite 存储（FTS5 + vec0，含 jieba 分词）
- `src/core/store/tcvdb.ts` — TCVDB 存储（hybridSearch）
- `src/core/store/bm25-local.ts` — BM25 本地编码器
- `src/core/store/embedding.ts` — 嵌入服务（local/OpenAI/ZeroEntropy）
- `src/core/store/types.ts` — IMemoryStore 接口 + StoreCapabilities

## 逐维度对比

| 维度 | Hermes vdb | TencentDB-Agent-Memory |
|---|---|---|
| dense embedding | BGE-M3 1024d (SiliconFlow) | 可配：OpenAI / local / TC VDB |
| vector store | Chroma HNSW cosine | sqlite-vec / TCVDB DISK_FLAT |
| sparse/关键词 | 手写 token overlap（仅 trigger_tags） | FTS5 BM25 或 BM25 sparse vector |
| 融合方式 | 0.6*dense + 0.4*sparse 固定加权 | RRF (k=60) rank fusion |
| 中文分词 | 按字拆分 | @node-rs/jieba / tcvdb-text |
| 降级策略 | vdb 不健康返回空，走路由表 | embedding/FTS 一方不可用自动用另一方 |
| 能力探测 | is_healthy() 布尔值 | getCapabilities() 返回 4 维度 |

## 可借鉴项（Hermes 框架内可复现）

1. **RRF 融合**（P0）
   - 替代 0.6/0.4 固定加权
   - 只需改 matcher.py：dense top16 rank + sparse rank → RRF score
   - 用 eval_skill.py 回归对比再部署

2. **IDF 增强 sparse**（P1）
   - 当前 weight = log(1+tf)，未考虑 df
   - build_index 时统计全局 token df → 权重改为 log(1+tf) * log(N/df)
   - 不动 query 端，不动 Chroma 结构

3. **能力探测细化**（P2）
   - 从 is_healthy() 改为 status() 字典
   - 包含 chroma_ok / cloud_ok / stale / count 等维度

## 不建议项

| 项 | 理由 |
|---|---|
| 接入其记忆系统 | Hermes 记忆系统够用；外部钩子不可靠，改动风险大 |
| 使用 TCVDB 后端 | 技能量级（几十个）不需要云级向量库 |
| 引入 node/TypeScript 依赖 | Hermes vdb 是纯 Python；jieba/sqlite-vec/tcvdb-text 属另一生态 |
| jieba 替换当前按字分词 | 引入 @node-rs/jieba 需要 Node 22+；收益 vs 复杂度不成比例 |
| server-side embedding | BGE-M3 云端 API 已稳定，无需迁移 |
