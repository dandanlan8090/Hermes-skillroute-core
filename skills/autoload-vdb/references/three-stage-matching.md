# vdb 三阶段匹配：v2.0 实现（2026-07-09）

> **Supersedes:** 旧版 three-stage-matching.md（fuzzywuzzy 版本已归档）
> **主持 skill:** `autoload-vdb` SKILL.md v2.0.0

## 当前架构

### Stage 1：向量检索（FAISS IndexFlatIP）

- 模型：BGE-Small-ZH-v1.5（512d）
- 入库模板：`技能名称：{name}\n技能描述：{desc}\n适用场景：\n{tag}\n{tag}`（标签重复 2 遍）
- 查询模板：`用户需求：{query}`（必须与入库句对齐）
- top-K 候选：16（config `matching.top_k_candidates`）
- BGE 句式敏感，不可省略/修改前缀

### Stage 2：Tag-Embedding 语义重打分（取代 fuzzywuzzy）

- 方法：query embedding vs 每个 trigger_tag 的预计算 embedding，cosine similarity max
- **关键技巧**：tag embedding 预计算时也使用 query 句式上下文 `用户需求：{tag}`
  裸词 "部署" 的 embedding 与 "用户需求：部署 nginx" 在向量空间很近
  裸词 embedding 则散落在不同区域，cosine 仅 ~0.56
- 效果：tag-query similarity 从 ~0.56 提升至 ~0.75-0.97
- 详见 `references/tag-embedding-alignment.md`

### Stage 3：disable 惩罚 + BM25 混合

- disable 有两种模式（config 驱动）：
  - `"filter"`：match ≥ 阈值（0.75）直接排除
  - `"penalty"`（默认）：match ≥ 阈值（0.55）从总分扣减 `w_dp × penalty_value`
- BM25 通过 config `bm25.enabled` 开关，依赖 `rank_bm25` 库，默认关闭

### 打分公式

```python
final = vec_score × w_vec + tag_score × w_tag + bm25_score × w_bm25
if disable_match >= penalty_threshold:
    final -= w_dp × penalty_value
```

当前权重（config.yaml）：w_vec=0.55, w_tag=0.35, w_bm25=0.10, w_dp=0.10

### 配置系统

所有权重/阈值/模式来自 `~/.hermes/vdb/config.yaml`，无硬编码。
修改后无需重启，下次 `match()` 自动生效。

## 标签体系

### trigger_tags（100% 覆盖 58 个活跃技能）

- 平均 5.9 个标签/技能，范围 5-14
- 中英文混合，粒度 2-6 字
- 参与 embedding 构建 + tag 重打分两阶段

### disable_tags（100% 覆盖 58 个活跃技能）

- 从 DISABLE_TAG_POOL（10 个标准值）选取
- 不进向量文本，只参与 disable 计算
- 分布：read_only(36) network_request(16) cli_only(10) ...

### 批量修复工具

`fix_tags.py` — 遍历全量 skills，规则映射补全 trigger 和 disable：
- trigger：预置 42 个技能的映射表，其余从 description 提取
- disable：基于路径分类 + description 关键词推断

## 已知坑

1. **Query 句式敏感性**：不可省略/修改前缀"用户需求："
2. **英文 description 的 BGE-ZH 效果差**：hermes-agent 等全英文 description 技能的中文 query 匹配弱
3. **权重调节**：如果英文技能匹配不足，建议 w_vec 降到 0.45，w_tag 提至 0.45
4. **版本守卫**：切换模型必须更新 `embedding.version` + ` embedding.dimension`
5. **frontmatter 格式**：`---#正文`（无换行）已被支持，但用 `re.match(r"^---\n...", ...)` 严格校验

## 版本历史

| 版本 | 架构 |
|------|------|
| v0 | BGE-Small-EN(384d) + fuzzywuzzy + 硬编码 0.6/0.4 |
| v1 | BGE-Small-ZH(512d) + fuzzywuzzy + meta.jsonl tags |
| **v2** | **BGE-ZH + tag-embedding + config 驱动 + disable 惩罚 + watcher** |
