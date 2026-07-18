# vdb/ — 技能检索工具链

Hermes Agent 的本地可插拔检索引擎，负责技能（SKILL.md）的索引、召回、排序与门禁过滤。

## 模块职责

| 模块 | 功能 | 调用关系 |
|------|------|---------|
| `sparse.py` | 词法权重计算（IDF 增强）。提取 trigger_tags + description 中文短语的 lexical weights，支持字段级加权（trig×1.2, desc×0.8）。 | embed.py 引用 |
| `embed.py` | 云端嵌入层。调 SiliconFlow BAAI/bge-m3 生成 1024d 稠密向量（prose 模板拼接 name+leading+desc+branches）。 | indexer.py / matcher.py 引用 |
| `indexer.py` | Chroma 索引构建。解析 SKILL.md frontmatter，构建稠密+稀疏双路索引。 | 独立运行入口 |
| `matcher.py` | 检索主入口。dcg-inspired 三层流程：query 分类短路 → 白名单直达(fast_path) → RRF 融合(K=60) + trigger 加成 → 路由门禁。 | 业务调用入口 |
| `routing.py` | 专名门禁路由层。阻止业务类 query 误命中重型框架文档（hermes-framework 等）。支持声明式加载（SKILL.md frontmatter gates 字段）。 | matcher.search() 内调用 |

## 检索流程

```
query → 分类短路(问候/空query) → 白名单直达(fast_path，精确命中 skill 名/trigger)
       → 稠密(BGE-M3 1024d, TOP_K=32) → 稀疏(BM25+IDF, same candidates)
       → disable 过滤 → RRF(K=60) 融合 + trigger 加成(0.010)
       → 专名门禁过滤 → 返回 top-K(默认8)
```

## 运维

```bash
# 构建/重建索引
cd ~/.hermes/vdb && .venv/bin/python indexer.py [--rebuild]

# 调用检索（测试用）
cd ~/.hermes/vdb && .venv/bin/python -c "from matcher import search; print(search('飞书文档', top_k=3))"
```

关键文件：每次改 `matcher.py` 的融合策略或 `indexer.py` 的索引逻辑后，须同步更新 `vdb` 的描述型 skill（`vdb-retrieval-pipeline`, `autoload-vdb`）中的对应数字和公式。被 pin 保护时走 `unpin → review → re-pin` 流程。
