# Hermes-skillroute-core 架构

本仓库是 Hermes Agent 微内核架构的配置模板。本文档用 [C4 模型](https://c4model.com/)（参考 [softaworks/agent-toolkit](https://github.com/softaworks/agent-toolkit) 的 C4 实践）描述系统边界与内部容器，并附一张检索/路由流的时序图，展示核心价值：**技能路由 + MCP 调用链**。

> GitHub 原生渲染 Mermaid，无需额外工具链。修改本文即可更新图——这是「文档跟得上代码」的关键。

## 1. System Context（系统上下文）

谁在与系统交互，系统依赖什么外部能力。

```mermaid
C4Context
    title System Context - Hermes-skillroute-core

    Person(user, "用户", "通过 SSH 终端与 Hermes Agent 对话")
    Person(developer, "开发者", "克隆本仓库、改 skill、提 PR")

    System(hermes, "Hermes Agent", "微内核路由架构的 AI Agent；SOUL.md 铁律 + 技能路由表 + vdb 语义召回")
    System_Boundary(repo, "Hermes-skillroute-core 仓库") {
        System(config, "配置模板", "SOUL.md / skills/ / vdb/ / scripts/ / memories/")
    }

    System_Ext(llm, "LLM Provider", "OpenAI 兼容端点（本地代理或云端）")
    System_Ext(embed, "Embedding API", "BGE-M3 云端嵌入（SiliconFlow 等）")
    System_Ext(mcpSrv, "MCP 服务器", "scrapling / codebase-memory / graphify 等原生接入")
    System_Ext(gh, "GitHub", "仓库托管（本仓库）")

    Rel(user, hermes, "对话 / 下发任务")
    Rel(developer, hermes, "扩展 skill、调 frontmatter")
    Rel(hermes, llm, "推理调用")
    Rel(hermes, embed, "稠密向量化")
    Rel(hermes, mcpSrv, "工具调用（检索/抓取/图谱）")
    Rel(developer, gh, "push / PR")
    Rel(gh, config, "托管配置模板")
    Rel(hermes, config, "加载 SOUL + skills + vdb")
```

## 2. Container（容器 / 模块边界）

仓库内部结构，按职责切分。

```mermaid
C4Container
    title Container - Hermes-skillroute-core

    System_Boundary(repo, "Hermes-skillroute-core") {
        Container(soul, "SOUL.md", "Markdown", "微内核：铁律 + 技能路由表 + 故障处理")
        Container(skills, "skills/", "Markdown + YAML frontmatter", "75 个合规技能，按分类组织")
        Container(vdb, "vdb/", "Python + Chroma", "混合检索：BM25 + BGE-M3 + trigger 加成，RRF(K=60)")
        Container(scripts, "scripts/", "Bash + Python", "init-vdb.sh / audit-soul-refs.sh 等运维脚本")
        Container(memories, "memories/", "Markdown", "USER.md 模板 + FRAMEWORK_EVOLUTION.md")
    }

    Container(llm, "LLM Provider", "API", "推理与标题生成")
    Container(embed, "Embedding API", "API", "BGE-M3 稠密向量")
    Container(mcp, "MCP Servers", "stdio", "scrapling / codebase-memory / graphify")

    Rel(soul, skills, "路由表指向")
    Rel(skills, vdb, "索引源")
    Rel(vdb, embed, "调用嵌入")
    Rel(soul, llm, "系统 prompt 注入")
    Rel(skills, mcp, "运行时工具调用")
    Rel(scripts, vdb, "重建索引 / 诊断")
```

## 3. 检索 / 路由流（时序图）

展示一次「用户提问 → 技能路由 → 工具调用」的完整链路。这是本仓库的核心价值。

```mermaid
sequenceDiagram
    autonumber
    participant U as 用户
    participant S as SOUL.md（铁律#0）
    participant V as vdb（matcher.py）
    participant R as 路由表
    participant K as skills/（skill_view）
    participant M as MCP 服务器
    participant L as LLM Provider

    U->>S: 下发任务（自然语言）
    S->>V: 先检索合适 skill（vdb 语义召回）
    V->>V: BM25 + BGE-M3 + trigger 加成，RRF(K=60)
    V-->>S: top-5 候选技能（含 final_score）
    S->>R: 命中路由表关键词？
    alt 路由表直接命中
        R-->>S: 指向目标 skill
    else 4 层召回兜底
        S->>K: skills_list + skill_view 扫描
        K-->>S: 加载细则
    end
    S->>L: 注入 SOUL + USER + MEMORY + 命中 skill
    L->>M: 执行任务（枚举专用工具，含 MCP）
    alt 抓取网页
        M-->>L: scrapling get/fetch
    else 代码结构查询
        M-->>L: codebase-memory search_graph/trace_path
    else PR 影响分析
        M-->>L: graphify triage_prs
    end
    M-->>L: 结构化结果
    L-->>U: 最终交付
```

## 4. 设计原则（与图对应）

| 原则 | 图中的位置 |
|------|-----------|
| 微内核：SOUL 只留铁律 + 路由表 | `SOUL.md` 容器，细则全在 `skills/` |
| 4 层召回无单点依赖 | 时序图 step 4-7（vdb → 路由表 → available_skills → skill_view） |
| 工具选型效率优先 | 时序图 step 11-14（MCP 专用工具优先于原始手段） |
| 配置与代码分离 | `memories/USER.md` 个性化，不入库；`skills/` 是元数据真源 |
| 脱敏：本仓库零个人数据 | 所有路径/IP/模型名已清洗为占位 |

## 参考借鉴

- [softaworks/agent-toolkit — c4-architecture skill](https://github.com/softaworks/agent-toolkit) — C4 模型 Mermaid 实践
- [NousResearch/hermes-agent Issue #486 — Code Wiki Skill](https://github.com/NousResearch/hermes-agent/issues/486) — 自动生成 `architecture.md` 的思路
- [mermaid.js — Architecture Diagrams](https://mermaid.js.org/syntax/architecture.html) — 图表语法参考
