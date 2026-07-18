---
name: search-retrieval-evaluation
description: >-
  搜索/检索系统质量评估方法论。覆盖：benchmark query 集构建、融合策略 A/B 对比
  (RRF vs 加权融合)、Top-1/Top-3 命中率测量、逐案差异分析、分阶段演进 (P0→P1→P2)。
  配套 Hermes vdb 检索基准测试。
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
        - benchmark
        - 检索评估
        - 检索评测
        - retrieval evaluation
        - search quality
        - RRF 对比
        - 融合策略
        - 命中率
        - top1
        - top3
        - recall test
        - search benchmark
        - 检索对比
        - A/B 测试
        - 融合评测
      disable:
        - deep_review
        - code_development
    skill_type: methodology
    priority: high
    depends_on:
      - vdb-retrieval-pipeline
---

# search-retrieval-evaluation — 检索质量评估与融合策略对比

## 背景

Hermes 的 vdb 混合检索使用 `0.6 × dense + 0.4 × sparse` 线性加权融合。  
2026-07-11 对 RRF (Reciprocal Rank Fusion) 做了基准对比，发现 RRF 在 Top-1 上领先 3.3pp。

本 skill 记录如何搭建检索评估、运行对比、以及逐步改进的流程。

## 评估方法论

### 构建 benchmark query 集

Benchmark 应由三种 query 类型组成：

1. **路由表场景** — 命中 `§技能路由表` 的关键词（最真实）
2. **中文场景** — 用户实际可能输入的碎片化口语 query
3. **英文场景** — 保留触发词原样，验证跨语言召回

61 条正式集 + 17 条 harder set 的当前基准：`T1=90.0% / T3=95.0%`（正式集），`T1=70.6% / T3=94.1%`（harder）。详见 `references/benchmark-case-set.md`（含名称映射表、harder set 根因分析）。

每条 query 配一个 **期望 skill 名**（注意：SKILL.md 的 `name` 字段不一定等于期望简称，需查名称映射）。

### 对比脚本结构

```
query → Chroma dense top-16 (含 dense_score, metadata)
     │
     ├─ 0.6/0.4 融合: final = 0.6*dense + 0.4*sparse → 排序 → top-1/3
     │             命中 = expected in top-1/3
     │
     └─ RRF 融合:   dense_rank = Chroma 序 (1..16)
                    sparse_rank = 候选内 sparse_score 排序 (1..N)
                    rrf_score  = 1/(k + dense_rank) + 1/(k + sparse_rank)
                    k = 60 (TencentDB 取值, 也可调参)
                    → 排序 → top-1/3
                    命中 = expected in top-1/3
```

逻辑保留 `dense_score`, `sparse_score`, `dense_rank`, `sparse_rank`, `rrf_score` 供差异分析。

完整可运行脚本在 `scripts/benchmark_rrf.py`。

### 指标

- **Top-1 命中率** — 最重要的单一质量指标
- **Top-3 命中率** — 副指标，检索卡可以容忍前 3 中有正确答案
- **逐案差异** — 分析两种融合策略的不一致 case，判断谁更「对」

### 差异解构方法

对 Top-1 不一致的 case：查看哪个结果更符合语义。常见模式：

| 模式 | RRF 赢 | 基线赢 |
|------|--------|--------|
| sparse 分把高 TF 的干扰 skill 推上前排 | RRF 的 rank-only 抑制了这种干扰 | 基线吃到了高位 dense 分 |
| 期望 skill dense 分中高但不在第 1，sparse 分中下 | RRF 通过 rank 加权把它抬到第 1 | 基线 linear 权重不足 |
| 期望 skill 名称/trigger 和 query 高度不匹配 | — | 基线 dense 语义匹配胜出 |

## P0→P1→P2 分阶段演进

这是对 vdb（或其他检索系统）进行安全迭代的推荐流程：

### P0：只评估，不动线上

1. 构建 benchmark case 集（可复用现有技能列表）
2. 写离线对比脚本，读 Chroma 数据但不改任何线上文件
3. 跑一次，输出 Top-1/Top-3 命中率差异
4. 做差异解构，判断新策略是否值得推进

**产出**：benchmark 结果 + 差异分析 + 决策（推/不推）

### P1：如果新策略胜出，只 patch 融合层

1. 只改 `matcher.py` 的 score 计算段
2. 保留 `dense_score`/`sparse_score` 独立字段输出
3. 新字段 `rrf_score` 用于调试，`final_score` 保持命名兼容
4. 重跑 benchmark 确认指标不退化

**受影响文件**（极小改动面）：
- `matcher.py` — 融合算法行
- `matcher.py` 顶部常量 — 删或保留旧权重注释

### P2+：description 中文短语入 sparse（description enrichment）

**问题**：sparse 仅索引 trigger_tags（~600 token），description 中文内容完全浪费。

**方案**：用 `re.findall(r'[\u4e00-\u9fff]{2,}', desc)` 提取连续中文短语，与 trigger_tags 合并为同一权重字典，统一用 `log(1+tf) × idf(t)`。

**关键约束**：
- 只取中文，拒绝英文（避免高频英文词稀释中文权重）
- 连续 2 字以上才提取
- 与 trigger_tags 同一 IDF 映射，不同字段不做 TF 累计
- 字段加权（trig×1.2/desc×0.8）在 harder set 上实测反降，**暂不启用**；字段加权应在 metadata 补齐后再测

**效果**：IDF token 从 657 → 791（净增 134），正式集 Top-1 +3.3pp。

### P2+F：RRF 融合阶段 trigger 命中加分（而非乘法）

**问题**：乘法 boost（×1.05）在 dense-rank=1 vs dense-rank=7 的 case 中完全无效——base 差 0.001 而乘后差距不变。

**方案**：加法叠加 `rrf_score += 0.010`（而非乘法）。加法让命中 trigger 的技能 score 上浮固定值，dense-1 的技能 base 高但没有 bonus，形成可叠加的胜负。

**公式**：
```
final_score = 1/(60+dense_rank) + 1/(60+sparse_rank) + (0.010 if trigger命中 else 0)
```

**效果**：
- "帮我排错"（dense=1 vs dense=7）：fault-troubleshooting base=0.0262，debugging-patterns base=0.0252 + 0.010 bonus = 0.0352 → 翻盘成功
- 对已有乘法 boost 的 case（×1.05）无回归

**注意**：`any(t.lower() in query_lower for t in trigger_tags)` — 检查 trigger 是否在 query 中，而非反向。

## P0→P2→P2+F 完整演进记录（2026-07-11）

| 阶段 | 方法 | 正式集 Top-1 | harder Top-1 |
|------|------|-------------|--------------|
| P0 | 0.6/0.4 + TF-only | 75.4% | — |
| P1 | RRF 融合（k=60） | 78.7% | — |
| P2 | TF-IDF（仅 trigger_tags） | 78.7% | — |
| P2+ | desc 中文短语入 sparse | 82.0% | — |
| P2+F | RRF + trigger 命中 +0.010 | **90.0%** | **70.6%** |

## 常见陷阱（每次 benchmark 迭代前必读）

### 陷阱 1：disable 精确子串匹配导致失效
**症状**：disable 标签加进去了但 query 仍命中该 skill。
**原因**：`disable='排查报错'` 不在 `query='排查一下为什么报错'` 中（多词短语需逐词匹配）。
**解法**：disable 短语须全部出现在 query 中才生效；避免用多词 disable，用单字/单意 disable（如"排错"、"排查"而非"排查报错"）。

### 陷阱 2：YAML 多行 patch 缩进嵌套
**症状**：多次 patch 同一 YAML 块导致缩进错乱，索引里 trigger 丢失。
**解法**：多行 patch 尽量一次性 patch 完成；或直接 patch 整个 section 后立即 `grep -A` 验证 YAML 正确性。

### 陷阱 3：benchmark 期望名与索引名不一致
**症状**：query 正确但 Top-1 不对，排查 trigger/disable 都无果。
**原因**：SKILL.md 的 `name` 与 benchmark 期望名不同（如 `audiocraft` vs `audiocraft-audio-generation`）。
**解法**：建立名称映射表；benchmark 前先跑 `matcher._get_collection().get(include=['metadatas'])` 对所有 skill name 建索引。

### 陷阱 4：dense-rank-1 压制问题
**症状**：期望 skill 的 trigger 全命中，但 RRF 仍然输给 dense-rank=1 的干扰技能。
**原因**：dense embedding 太强，即使 sparse 完全命中也无法翻盘。
**解法**：
- 给目标技能加更多能提升 dense 相关性的 trigger（让它的 prose 模板包含 query 关键词）
- 给干扰技能加 disable（精确子串，单词级）
- dense vs sparse 的边界是 hard limit，无法通过调参解决

### 陷阱 5：字段加权（trig×1.2/desc×0.8）harder set 反降
**症状**：加字段加权后正式集不变，harder set 降 10+ pp。
**原因**：harder set 的成功 case 很多依赖 description 中文短语命中，压 desc 权重直接毁了这批 case。
**结论**：字段加权需等 metadata（trigger 覆盖率）补齐后再测，当前保持 1.0/1.0。

## 依赖

- `vdb-retrieval-pipeline`（被评估的目标系统）
- `chromadb`, `openai`, `python-dotenv`（同 vdb 依赖）

## 依赖

- `vdb-retrieval-pipeline`（被评估的目标系统）
- `chromadb`, `openai`, `python-dotenv`（同 vdb 依赖）

## 验证

运行 benchmark 脚本验证指标与上次基准持平或提升：
```bash
source ~/.hermes/vdb/.venv/bin/activate
python3 eval/benchmark_rrf.py
```

脚本位置：`~/.hermes/vdb/eval/benchmark_rrf.py`（与 vdb 同目录，非 skill 内复制）
