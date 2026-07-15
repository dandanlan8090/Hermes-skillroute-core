# Description 中的 leading word 对 vdb 召回的影响

## 映射链路

```
SKILL.md 中的 description 字段
    ↓
vdb/indexer.py _extract_leading_word()
    ├── 从 description 前 30 字符提取 leading word
    ├── 匹配 LEADING_WORDS 池（21 词）或中文同义词表
    └── 兜底：取前 30 字符原文
    ↓
PROSE_DOC_TEMPLATE = "{name}：{leading}。{desc}。触发：{branches}。"
    ↓
BGE-M3 稠密向量 (1024d) + sparse 2x boost
    ↓
final = 0.6 × dense + 0.4 × sparse
```

## leading word 命中 → sparse 权重 ×2

`sparse.py` 的 `LEADING_WORD_POOL` 有 21 个词，按 skill_type 分桶：

| 类别 | 词汇 |
|------|------|
| methodology | red, green, fog, war, tracer, bullet, root, cause, verify, first, sunk, cost, ship, it, ground, truth |
| workflow | dispatch, gate, handoff, slice |
| tool | probe, fire, scaffold |
| integration | bridge, mirror |

如果 description 中出现了这些词（或其中文同义词，如"根因排查"→"root-cause"），稀疏端分数 ×2。

## 实际影响

实测数据（2026-07-10，58 技能，5 条基准 query）：

| query | 改进前 Top-1 | 改进后 Top-1 | 变化 |
|-------|-------------|-------------|------|
| "dzhng skills 写法" | research-paper-writing (0.41) | **hermes-agent-skill-authoring** (0.36) | rank swap ✓ |
| "write-skills 怎么写" | research-paper-writing (0.42) | **hermes-agent-skill-authoring** (0.40) | rank swap ✓ |
| "部署 flask" | mlops-inference (0.37) | mlops-inference (0.38) | 同序 ✓ |
| "git commit" | github (0.42) | github (0.38) | 同序 ✓ |
| "gmail" | himalaya (0.47) | himalaya (0.47) | 同序 ✓ |

Top-1 命中率: 60% → 100%，2 个 rank swap 全部为正确方向。

## 对 description 作者的实操建议

### 写法

```
# 3-zone: leading word + 核心动作 + 触发条件
"verify-first：发布前执行质量门控和回滚计划。Use when deploying to production, preparing a release."
  ↑ leading word           ↑ 核心动作                    ↑ 触发分支 / 禁用场景
  池中命中 → 2x boost      BGE-M3 语义向量               match trigger
```

### 常见反模式

| 反模式 | 为什么不好 | 改进 |
|--------|-----------|------|
| description 只有"AI 求职助手" | 无 leading word，无触发分支 | "job-match：AI 求职全流程编排。评估 JD/改 CV/写求职信。" |
| description 写满 1024 字符 | 稠密向量稀释，sparse 命中率低 | 压到 150 字符内 |
| description 首词是通用动词("使用此技能在部署前...") | leading word 兜底取前 30 字，这种无信号词浪费 boost 机会 | 首词放強概念词 |

## leading word 池扩展

如需新增 leading word：
1. 写入 `NEW_SKILL_TEMPLATE.md §Leading Word 词汇库`
2. 写入 `sparse.py` 的 `LEADING_WORD_POOL` 常量
3. 写入 `indexer.py` 的 `LEADING_WORDS_ZH` 中文同义词表（如果适用）
4. `build_index(force=True)` 重建索引
5. 5 条 query 回归验证
