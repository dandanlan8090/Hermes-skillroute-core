---
name: autoload-vdb
description: "Hermes 启动时自动加载 vdb 技能语义匹配（Chroma + SiliconFlow BGE-M3 云端稠密 prose 模板 + 本地 sparse lexical，leading word 2x boost → RRF 融合 RRF_K=60 + trigger 命中 +0.010 加法加成）。触发：Hermes 初始化/启动/新 session/重新加载技能。禁用：离线环境/无 API Key/不需要语义匹配。"
version: 6.1.0
author: Hermes Agent
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags:
      trigger:
        - "自动加载"
        - "autoload"
        - "启动加载"
        - "session start"
        - "vdb"
        - "向量索引"
        - "技能匹配"
        - "init"
        - "startup"
        - "新会话"
        - "embedding"
        - "向量重建"
        - "技能检索"
        - "Chroma"
        - "混合检索"
      disable:
        - "不需要 vdb"
        - "无向量索引"
        - "创建技能"
        - "新建技能"
        - "纯 CLI 查询"
        - "离线强制要求"
    skill_type: "tool"
    priority: "high"
prerequisites:
  commands: []
  env_vars:
    - SILICONFLOW_API_KEY (or SF_API_KEY)  # 必填
---

# autoload-vdb — Hermes 启动时自动加载技能语义匹配

## 概述

vdb 是 Hermes 的**技能语义匹配系统**。给定用户 query，从 `~/.hermes/skills/` 中找出最相关的技能。

**当前架构（v6.1.0 — dcg-inspired）**：Chroma 持久化向量库 + SiliconFlow BGE-M3 云端稠密 + 本地 sparse lexical + leading word 2x boost。2026-07-16 新增三层 dcg 借鉴补丁（query 分类短路 + 白名单直达 + route_stage 标记）。2026-07-10 改进：
- DOC 模板从字段堆叠改成 prose 自然语言段（name+leading+desc+branches）
- 稀疏端加 leading word 2x boost（21 词池）
- query 模板从"用户需求：{}"改成"调用{query}。"（仅 <15 字短查询包装）
- 新增盲测工具 eval_skill.py
- Top-1 命中率: 60% → 100%（5 条 regression query 实测）

```python
from indexer import build_index
build_index(force=True)        # 全量重建

from matcher import search
results = search("部署 flask")  # 混合检索
```

## 混合检索流水线（v6.1.0 — dcg-inspired）

```
query
  │
  ├── 0. (A) dcg query 分类短路
  │     问候/短词不在映射表 → 直接返回 []，省 BGE-M3 API
  │     fast_path：全量精确命中技能名/trigger → 直达，跳过 RRF
  │
  ├── 1. 云端 SiliconFlow BAAI/bge-m3 (1024d)
  │     输入: PROSE_DOC_TEMPLATE = "{name}：{leading}。{desc}。触发：{branches}。"
  │     QUERY 端: 短查询(<15字)用 "调用{query}。" 包装，长查询裸送
  │     Chroma cosine 召回 top-16
  │
  ├── 2. 本地 sparse.py (纯 Python, 无需 torch/FlagEmbedding)
  │     输入: trigger_tags + description 中文短语(>=2字) 合并，TF-IDF 加权
  │     leading word 命中 2x boost（池 21 词）
  │     算法: tokenize(中文按字+英文按词) → log(1+tf)×idf → 余弦归一化
  │     英文 description 完全隔离
  │
  └── 3. disable 过滤 → RRF 融合 (RRF_K=60)
       → trigger 命中 +0.010 加法加成
       → (C) route_stage 标记：fast_path / rrf
       → 路由门禁过滤 → top-5
```

Feature flags（matcher.py 顶部开关，False 即回滚）：
- `USE_QUERY_CLASSIFICATION` — 借鉴A：query 分类短路（对标 dcg SpanKind）
- `USE_FAST_PATH`           — 借鉴B：白名单直达（对标 dcg SAFE_PATTERNS）
- `USE_ROUTE_ANNOTATION`    — 借鉴C：路由阶段标记（对标 dcg confidence 只降级不前置加权）

## 文件结构

```
~/.hermes/vdb/
├── __init__.py        # 导出 build_index / search
├── sparse.py          # 纯 Python lexical weights（无外部依赖，v6.0.0 leading word 2x boost）
├── embed.py           # 云端稠密 API + 本地 sparse 包装
├── indexer.py         # Chroma 索引构建（v6.0.0 PROSE_DOC_TEMPLATE + leading word 提取）
├── matcher.py         # 混合检索入口（v6.0.0 prose 对齐 query 模板）
├── eval_skill.py      # 盲测工具（生成 blind/judge prompt，不走 vdb 索引，单独使用）
├── eval/
│   ├── cases/         # 测试套 JSON（按 skill 名组织）
│   ├── prompts/       # 生成的 blind/judge prompt
│   └── results/       # 手动判定结果
├── chroma/            # Chroma 持久化目录（~1.2MB / 99 技能）
└── .venv/             # pip: chromadb openai python-dotenv pyyaml numpy
```

**对比 v4.0.0（1 文件 vdb.py + numpy dot）**：
- 解决了 tags 被英文 description 稀释的问题
- sparse 分数完全来自 trigger_tags 关键词匹配
- 延迟从 250ms 降到 **116ms**（Chroma HNSW 更快）
- bad case 从 4 个降为 1 个

## 依赖安装

```bash
source ~/.hermes/vdb/.venv/bin/activate
pip install chromadb openai python-dotenv
# sparse.py 零依赖
```

## 核心设计原则

### 1. 稠密 vs 稀疏严格分离

| 通道 | 位置 | 输入 | 输出 |
|------|------|------|------|
| 稠密 (dense) | 云端 SiliconFlow | PROSE_DOC_TEMPLATE `{name}：{leading}。{desc}。触发：{branches}。` | 1024d 向量 → Chroma |
| 稀疏 (sparse) | 本地 CPU | **trigger_tags + description 中文短语(>=2字)**（leading word 2x boost，TF-IDF 加权） | 词权重字典 → Chroma metadata |

**关键约束**：sparse 由 trigger_tags 与 description 中 `re.findall(r'[\u4e00-\u9fff]{2,}')` 提取的中文短语**合并**产生，英文 description **完全不参与** sparse 计算（避免高频英文词稀释中文权重）。两者用同一 IDF 权重公式、同一字典，不区分字段权重。

**v6.0.0 改进**: PROSE_DOC_TEMPLATE 代替旧字段堆叠模板，BGE-M3 拿到自然语言段（name+leading+desc+branches），语义对齐比字段堆叠好。leading word 命中 trigger_tags 时 sparse 权重 ×2。

### 2. 无需 torch / FlagEmbedding（配额受限环境的 fallback）

磁盘配额限制下无法安装 torch（>800MB），sparse.py 用纯 Python 实现了等效算法：

- 中文逐字 + 英文按词的 tokenizer
- `log(1+tf)` 权重公式（与 BGE-M3 内部一致）
- `compute_lexical_matching_score` = 余弦归一化的加权交集

实测验证：
  - "部署 nginx" → system-admin tags "部署" → sparse=0.223 ✅
  - "youtube 视频" → system-admin tags → sparse=0.000 ✅（完全隔离）
  - "hermes 配置" → hermes tags → sparse=0.463 ✅（中英混词匹配）

### 3. Chroma 而非 numpy dot

- 99 个技能，Chroma HNSW cosine 1.2MB 持久化
- 自带的 metadata 过滤、distances 转换省去手写
- 查询 `collection.query(query_embeddings=..., n_results=16)` 一行召回
- 无缝支持 scale 到 1000+ 技能

### 4. 模型/提供方热替换

```python
# embed.py
MODEL = "BAAI/bge-m3"
API_URL = "https://api.siliconflow.cn/v1"

# 换模型：改 MODEL
# 换提供方：改 API_URL + api_key 加载逻辑
# 重启后 build_index(force=True)（dim 可能变）
```

### 5. 融合与加权（已弃用 0.6/0.4，改 RRF）

2026-07-11 起 `matcher.py` **不再用 `VEC_WEIGHT/SPARSE_WEIGHT`**，改为 RRF 倒数排名融合：

```python
# matcher.py
RRF_K = 60
TRIG_HIT_BONUS = 0.010   # trigger 命中加法加成（见下方坑位 1/2）
# final = 1/(RRF_K+dense_rank) + 1/(RRF_K+sparse_rank) + (trig命中 ? 0.010 : 0)
```

**不要**改回 0.6/0.4 —— RRF 在中文 query 上 Top-1 高约 3pp。trigger 加成用**加法**不用乘法（乘法对 dense 主导的 case 无效）。

### 关键坑位（2026-07-11 实测，务必遵守）

1. **trigger 加成用加法不用乘法**。
   乘法 `×1.05` 对 dense 主导的 case 完全无效：dense_rank=1 vs dense_rank=7 的 base 分差约 0.0010，
   乘法按比例缩放两边、差距不变。改用**加法 +0.010** 后，同有 trig 命中的两边各 +0.010，可翻转
   dr=7→dr=1 的差距。调参经验：先试 +0.005（偏小会引入回归），再试 +0.010（稳定）。

2. **不要对 desc 中文短语降权**。
   试过 `trig×1.2 / desc×0.8` 字段加权，harder set 从 47.1% 暴跌到 35.3%——缺 trig 全依赖 desc 的
   query 被压死后反而匹配不到正确技能。已回退 1.0/1.0（trigger_tags 与 desc 短语同权重）。

3. **disable 匹配是 `disable in query`（disable 必须是 query 的连续子串）**。
   `any(d.lower() in query_lower for d in disable_tags)` —— disable 标签要能**原样**出现在用户自然语言里。
   拼起来的短语如 "排查报错" 在 "排查一下为什么报错" 中不是连续子串 → 不匹配 → 失效。
   正确做法：disable 用单词或 query 中真实出现的短语（如 "排错" 在 "帮我排错" 中命中）。

4. **dense 主导的 case 是天花板**。
   两技能 dense 向量很近时（fault-troubleshooting dr=1 vs debugging-patterns dr=7~9），
   sparse + trigger 加成翻不动。根因是 embedding 质量，不是元数据。trigger 补全 + disable 加强
   只救 sparse 主导的 case；信息密度低的自然语言 query（harder set）卡在 ~70% 是 embedding 上限。

> 完整演化线与负结果记录见 `references/benchmark-evolution-2026-07-11.md`（本次新增）。

### 6. dcg-inspired 三层补丁（2026-07-16）

借鉴 dcg（Destructive Command Guard）的分类路由方法，在 RRF 融合前新增两层短路，对标 dcg 的 SpanKind 状态机 + SAFE_PATTERNS 白名单。

#### 借鉴A：query 分类短路（_classify_query）
matcher.py 入口处先判断 query 类型。问候/短词不在 _TRIGGER_MAPPING → 直接返回 []，省一次 BGE-M3 云端 API 调用。
- 规则1：完整 query 精确命中映射表 → retrieval
- 规则2：问候/元指令模式 → non_retrieval
- 规则3：单 token 且是短词（中≤2 或英数≤4）且不在映射表 → non_retrieval；长短语（如"帮我写脚本"长度 5）→ retrieval
- 规则4：多 token / 复杂 → retrieval（fail-open）
- PITFALL：中文无空格，整句可能被合并为一个 token。必须按长度区分短词（闲聊）和长短语（可能是查询意图），不能仅凭 len(meaningful)==1 就短路。

#### 借鉴B：白名单直达（_fast_path）
dense 召回后、RRF 前，精确命中技能名/trigger 时跳过 RRF 直达返回。对应 dcg SAFE_PATTERNS 白名单短路。
- 策略：完整 query 精确命中技能名/trigger → 直达；独立有意义词命中 trigger → 直达
- _TRIGGER_MAPPING 从 Chroma 全量元数据构建（模块预热时自动加载、技能变更后 refresh_trigger_mapping() 刷新）
- PITFALL：映射表只包含 skill_name + trigger_tags，不含 description 自动提取的中文短语——避免扩大化误触发。

#### 借鉴C：路由阶段标记（route_stage）
返回结果带 route_stage 字段（fast_path / rrf），零逻辑变更仅观测增强。对应 dcg confidence 只用于后处理降级、不前置加权。

#### Feature Flags（matcher.py 顶部）
```python
USE_QUERY_CLASSIFICATION = True   # 借鉴A
USE_FAST_PATH = True              # 借鉴B
USE_ROUTE_ANNOTATION = True       # 借鉴C
```
设 False 即回滚对应功能，不改其他代码。灰度顺序：先 C（零风险）→ A（低风险）→ B（中风险），每步观察 1-2 天。

#### 与 dcg 的关键对比

| 维度 | dcg | vdb |
|------|-----|-----|
| 路由时机 | 命令匹配前：字节级 SpanKind 状态机 | 嵌入检索前：轻量 query 分类 |
| 分层依据 | 命令语法上下文 | query 语义/token 查表 |
| 融合方式 | 白名单短路 + 黑名单（确定性） | RRF(K=60) 融合 |
| 失败策略 | fail-safe 偏严（宁可误拦） | fail-open 偏召回（拿不准就走检索） |
| 分数用途 | 决策后置信度降级（Critical 保护） | trigger +0.010 加法后处理 |
| 实时接入 | 同进程 PreToolUse hook | vdb-autoload process_context 钩子 |

> 核心启示：机制层必须 == 实时层。dcg 的 SpanKind 分类直接写在 PreToolUse 实时路径上（hook.rs→evaluator.rs→context.rs），无 side table 异步消费。vdb 的 process_context 钩子是正确形态（实时路径内做分类/路由），不要学只写 message_tags.db 等离线消费的架构。

### 7. 方法论改进原则

当引入外部方法论（如 dzhng/skills）优化现有系统时，遵守"做改进不做新技能"原则：
- **先比对**：识别外部方法论中高于现有体系的部分
- **在现有体系上改进**：在现有文件/功能上做插拔式增强，不另起炉灶
- **回调测试**：改完后用同一组 query 做 before/after 对比，确保回归 <= 原有 bad case
- **嵌入偏好**：用户明确表态的改进逻辑写入 skill body，不只是 memory

示例（2026-07-10 引入 dzhng/skills leading word 方法论）：
  1. 在 `sparse.py` 加 `LEADING_WORD_POOL` + `LEADING_WORD_BOOST=2.0`
  2. 改 `indexer.py` 的 `DOC_TEMPLATE` → `PROSE_DOC_TEMPLATE`
  3. 不改 Chroma 架构、权重比例、disable 过滤、AGENTS.md 触发链
  4. 5 条 query 前/后对比，2 个 rank swap 改善，0 回归

---

## 通用流程

> 📌 元数据编写规范（trigger/disable/description 写法 + 边界认知）：见 `references/METADATA_GUIDE.md`。本段只讲"何时重建索引"，写法细节以该指南为准。

### 创建新技能后

1. 按 NEW_SKILL_TEMPLATE.md 写 frontmatter（**trigger ≥ 7**，disable 必填 ≥ 2-3 条；详见 `hermes-agent-skill-authoring` 的「召回质量约束」）
2. 重建索引（**必须**，否则新技能永不被召回）：
   ```bash
   cd ~/.hermes/vdb && source .venv/bin/activate && PYTHONPATH=$PWD \
     python3 -c "from indexer import build_index; build_index(force=True)"
   ```
3. 验证：`python3 ~/.hermes/scripts/vdb-autoload.py --check` 应返回 "索引最新"

### 新装外部技能后（clone / copy / skill_manage create）

任何把新 SKILL.md 放进 `~/.hermes/skills/` 的操作（不限于本会话内 create）都必须重建索引：

- `skill_manage(action='create')` 写入后立即 `build_index(force=True)`
- clone 一个 repo 的 `skills/` 到本地后，同样重建
- **当前 session 的检索缓存不会自动感知磁盘变化**——不重建索引就查不到新技能

### 修改技能 description / trigger / disable 后

同上（暂未实现 watcher，需手动 build）。改完跑 `--check` 确认索引与 skills 列表一致。

### 切换模型/提供方

1. 改 `embed.py` 的 `MODEL` / `API_URL`
2. `build_index(force=True)` 全量重建

### 查询使用

```python
from matcher import search
results = search("部署 nginx", top_k=5)
# 返回 [{
#   "skill_name": ..., "skill_path": ...,
#   "final_score": ..., "dense_score": ..., "sparse_score": ...,
#   "trigger_tags": [...], "disable_tags": [...]
# }]
```

### 验证查询结果

```bash
cd ~/.hermes/vdb && source .venv/bin/activate && PYTHONPATH=$PWD \
  python3 -c "from matcher import search; [print(f'{r[\"final_score\"]:.3f}  {r[\"skill_name\"]}') for r in search('你的查询')]"
```

## 全局红线

### ⚠ Key 必须配置

- 写入 `~/.hermes/.env`：`SILICONFLOW_API_KEY=sk-...`
- 不要硬编码进代码文件

### ⚠ 离线环境不可用

- 当前架构强依赖 SiliconFlow API
- 无 API 时所有 build/search 均失败

### ⚠ 不要自动推 GitHub

- `~/.hermes/vdb/` 中的代码是公开发布项目的一部分
- 未经用户明确指令禁止 git push
- 详见 `repo-publishing-workflow` 红线

### ⚠ vdb 不会自动作为默认检索生效

- 仅安装代码 + 建索引不够，Hermes 仍用 available_skills 手动匹配
- 需要 AGENTS.md §0 指令：禁用手动匹配，优先 search()
- 需要 ~/.hermes/scripts/vdb-autoload.py 预热 Chroma
- 详见 `scripts/vdb-autoload.py` 或 GitHub 仓库的 TROUBLESHOOTING.md

### ⚠ 磁盘配额限制

- 当前环境有 overlay2 storage quota（~3-4GB）
- 无法安装 torch/transformers/FlagEmbedding 等大包
- sparse.py 用纯 Python 实现，无需任何外部依赖（详见 `references/pure-python-sparse.md`）
- 如果后续环境解除配额，可升级到官方 FlagEmbedding + `compute_lexical_matching_score`

### ⚠ Disable 标签使用下划线格式

- DISABLE_TAG_POOL 全部使用下划线（`cli_only`, `deep_review`, `read_only`）
- matcher.py 的 disable 过滤逻辑会把下划线转空格后再做子串匹配
- 示例：`"read only cli 查看"` → `read_only` 拆成 `"read"` + `"only"` → 都出现在 query 中 → 命中
- 新技能使用 disable 时必须从 DISABLE_TAG_POOL 选取，不要自创格式

## 评估数据（2026-07-09 实测）

| 指标 | v4.0 (numpy dot) | v5.0 (Chroma + sparse) |
|------|------------------|------------------------|
| 25 条 Top-1 正确 | 17/25 (68%) | **20/25 (80%)** |
| Bad case 数 | 4 ❌ + 4 ⚠️ | **1 ❌ + 3 ⚠️** |
| 延迟 | 250ms | **116ms** |
| 索引大小 | 237KB | **1.2MB (Chroma)** |
| 文件数 | 2 | 5 |
| sparse 纯度 | tags 混在 doc 文本 | **仅 trigger_tags** |

**Bad case 根因（非架构问题，是技能元数据）**：
- "配置 postgresql" → airtable：system-admin 缺"数据库"tag
- "查股票行情" → gif-search：无股票技能，合理降级

## 参考链接

- `references/embedding-provider-comparison.md` — NVIDIA/SiliconFlow/本地实测
- `references/three-stage-matching.md` — v3.0 三阶段架构文档（已归档）
- `references/description-leading-word-impact.md` — description leading word 对 vdb 召回影响的实测与建议（v6.0.0）
- `references/recall-gap-analysis-2026-07-10.md` — **本次会话新增** 54 技能的逐 query 召回实测数据（dense/sparse 分量、bad case 根因、system prompt 瘦身影响评估）
