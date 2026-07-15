# 技能描述双语化指南（提升 vdb 跨语言匹配质量）

## 背景

vdb 使用 BGE-M3（多语言 embedding）做语义匹配。BGE-M3 支持中英跨语言，但**单语言 description 的向量始终不如双语完整**。

## 形态模型：硅基流动 BGE-M3 的跨语言相似度上限

测试数据（2026-07-09，58 个 Hermes 技能）：

| 技能 description 类型 | 中文 query 平均分 | 英文 query 平均分 | 差异幅度 |
|----------------------|-------------------|-------------------|---------|
| 纯中文 description | 0.65-0.71 | 0.50-0.58 | ~0.10 |
| 纯英文 description | 0.55-0.62 | 0.65-0.72 | ~0.10 |
| **双语 description** | **0.68-0.73** | **0.67-0.73** | **~0.02** |

双语技能在两种语言的 query 下都能稳定达到 0.68+，单语种技能在**非本语言 query 下会损失 5-10% 相似度**。

## 具体案例

| 技能 | 原 description | 中文 query 分 | 修复方案 |
|------|---------------|---------------|----------|
| hermes-agent | `"Configure, extend, or contribute to Hermes Agent."` | 0.599 | 后加中文：`配置、扩展、调试 Hermes Agent 自身。` → 预期 0.65+ |
| hermes-agent-skill-authoring | `"Author in-repo SKILL.md: frontmatter..."` | 0.649 | 后加中文：`写 Hermes 技能 SKILL.md 的规范。` → 预期 0.67+ |
| mlops-inference | `"Local LLM inference: llama.cpp (GGUF), vLLM..."` | 0.36* | 后加中文：`本地 LLM 推理：llama.cpp、vLLM。` → 预期 0.50+ |

*注：mlops-inference 在 "本地跑 AI 模型" query 的 top-8 都进不了，是受创最深的案例。

## 操作步骤

### 给技能 description 加中文摘要

```yaml
# SKILL.md frontmatter
description: >
  <英文原描述，保留面向国际用户的完整语义>
  中文摘要：<20-50 字核心描述，帮助中文 query 落在这个技能上>
```

受限于 1024 字符上限，中文摘要不需要翻译全文——几个核心关键词就够：
- "配置 Hermes Agent" → 不必翻译为长句，"配置 Hermes Agent" 本身够用
- "本地 LLM 推理" → 加 `本地 LLM 推理：llama.cpp、vLLM`
- "前端设计" → 加 `网页设计、CSS、设计模板`

### 怎么知道当前技能的跨语言匹配质量？

1. 检查 vdb 查询结果：
```python
from vdb import VDB
db = VDB()
db.load()
r = db.search("中文 query 描述该技能的功能")
if r and r[0]['skill_id'] != '该技能名':
    # 说明中文 query 命不中
    print(f"期望 {expected}, 实际 top-1: {r[0]['skill_id']} ({r[0]['score']:.3f})")
```

2. 检查 description 内容：
```bash
grep -A1 'description' ~/.hermes/skills/<skill>/SKILL.md | head -3
# 如果全是英文且 trigger_tags 有中文 → 需要加双语
```

## 优先级

**优先修复**：trigger_tags 为中文但 description 为全英文的技能。这类技能的 mismatch 最大。

影响最大的 5 个技能（按 vdb 查询错误率排序）：
1. hermes-agent（中文 trigger + 全英文 desc）
2. mlops-inference（全英文 desc）
3. hermes-agent-skill-authoring（全英文 desc）
4. source-driven-development（全英文 desc）
5. codebase-memory-mcp（英文 desc + 中文 trigger）
