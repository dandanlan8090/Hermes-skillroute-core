---

name: codebase-memory-first
description: 工作流钩子：任何编码/重构/排查任务前，先查询 codebase-memory 代码图谱
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
      - 代码图谱
      - 代码搜索
      - 代码理解
      - 索引
      - codebase
      - 查代码结构
      - 先读代码
      disable:
      - code_development
      - read_only
    category: devops
    related_skills:
    - codebase-memory-mcp
    - opencode
    - openclaw
---

# Codebase-First 工作流钩子

## 触发条件

**核心规则：任何涉及代码的任务前必须执行此钩子（用户没说"不用 skill"时）**

**任务类型：**
- 新增功能 / 修改现有代码
- 重构 / 提取函数 / 移动文件
- 排查 bug / 追踪调用链
- Code Review
- 查找"某个功能在哪里实现的"
- 查找死代码 / 未使用的函数
- 运维脚本修改（> 20 行）

**豁免（仅当用户显式指令）：**
- "不用 skill，直接干"
- "跳过 skill"
- "直接执行"
- "别查技能了"
- 纯文档修改
- 配置文件调整（yaml/json/env）
- 一次性脚本（< 20 行）

**违规判定：** 用户没说豁免但你没加载此技能 = 违规（无论结果正确与否）

## 执行步骤

### Step 1: 确认已索引项目

```bash
codebase-memory-mcp cli list_projects
```

**期望输出：**
```json
{"projects":[{"name":"home-lan-.hermes-skills","root_path":"~/.hermes/skills",...}]}
```

**如果项目列表为空：**
→ 立即索引当前工作目录：
```bash
codebase-memory-mcp cli index_repository '{"repo_path":"$(pwd)","project_name":"$(basename $(pwd))"}'
```

### Step 2: 根据任务类型选择查询

#### 场景 A: 查找某个功能/函数的实现位置

```bash
codebase-memory-mcp cli search_graph '{"project":"home-lan-.hermes-skills","name_pattern":".*<FunctionName>.*","label":"Function","limit":10}'
```

**替换 `<FunctionName>` 为实际函数名**，例如：
- `.*Handler.*` — 查找所有 Handler
- `.*build_service.*` — 查找特定函数

#### 场景 B: 追踪调用链（谁调用这个函数）

```bash
codebase-memory-mcp cli trace_path '{"project":"home-lan-.hermes-skills","function_name":"<function>","direction":"inbound"}'
```

#### 场景 C: 查找这个函数调用了谁

```bash
codebase-memory-mcp cli trace_path '{"project":"home-lan-.hermes-skills","function_name":"<function>","direction":"outbound"}'
```

#### 场景 D: 获取架构概览（了解模块关系）

```bash
codebase-memory-mcp cli get_architecture '{"project":"home-lan-.hermes-skills","aspects":["boundaries","clusters","layers"]}'
```

#### 场景 E: 查找死代码（无任何调用的函数）

```bash
codebase-memory-mcp cli search_graph '{"project":"home-lan-.hermes-skills","label":"Function","min_degree":0}'
```

#### 场景 F: 查询某个模块的包结构

```bash
codebase-memory-mcp cli query_graph '{"project":"home-lan-.hermes-skills","cypher":"MATCH (m:Module) WHERE m.name =~ \".*<pattern>.*\" RETURN m"}'
```

### Step 3: 将查询结果写入 Plan

在 `.hermes/plans/YYYY-MM-DD_HHMMSS-<slug>.md` 中添加：

```markdown
## Codebase Memory 查询结果

**查询类型：** [search_graph / trace_path / get_architecture]

**查询参数：** `[复制完整 JSON]`

**关键发现：**
- 相关文件：[path1, path2]
- 调用链：[A → B → C]
- 模块边界：[...]

**后续实施策略：**
基于上述发现，将在 [文件 X] 修改 [功能 Y]，避免与 [模块 Z] 冲突。
```

### Step 4: 执行 Plan

使用 `subagent-driven-development` 按任务逐条实施，每个任务开始前：
1. 重述 codebase-memory 发现
2. 确认修改范围不越界
3. 提交前再次验证调用链未断裂

## 集成到 AGENTS.md

在 AGENTS.md §2.1 工作流决策树中添加：

```
用户消息 → 是否涉及代码修改？
  ├─ 否 → 直接执行
  └─ 是 → codebase-memory-first 钩子
        ├─ list_projects（确认索引）
        ├─ search_graph / trace_path（定位影响范围）
        ├─ 写 plan（包含查询结果）
        └─ 才进入 todo 推进 + 执行
```

## 典型工作流示例

### 示例：修改 ComfyUI 的 `run_workflow` 脚本

```bash
# Step 1: 确认索引
codebase-memory-mcp cli list_projects

# Step 2: 查找 run_workflow 的调用者
codebase-memory-mcp cli trace_path '{"project":"home-lan-.hermes-skills","function_name":"run_workflow","direction":"inbound"}'

# Step 3: 查找 run_workflow 调用了谁
codebase-memory-mcp cli trace_path '{"project":"home-lan-.hermes-skills","function_name":"run_workflow","direction":"outbound"}'

# Step 4: 查找相关函数（_url, http_request 等）
codebase-memory-mcp cli search_graph '{"project":"home-lan-.hermes-skills","name_pattern":".*_url.*","label":"Function","limit":10}'

# Step 5: 获取架构概览（了解 creative 模块边界）
codebase-memory-mcp cli get_architecture '{"project":"home-lan-.hermes-skills","aspects":["boundaries","clusters"]}'
```

### 查询结果整合到 Plan

```markdown
# ComfyUI run_workflow 错误处理改进 Plan

## Codebase Memory 查询结果

**查询 1: trace_path (inbound)**
- 调用者：无直接调用（entry point）
- 使用场景：主要通过 CLI 调用

**查询 2: trace_path (outbound)**
- run_workflow → _url → HTTPRequest.json
- run_workflow → extract_schema → load_schema

**查询 3: search_graph (.*_url.*)**
- _url 在 creative/comfyui/scripts/run_workflow.py:23
- 被调用 10 次（hotspot）

**查询 4: get_architecture (boundaries)**
- creative 模块 → research 模块（8 次跨边界调用）
- creative 内部：comfyui 集群（24 文件，cohesion=1.0）

## 实施策略

基于上述发现：
1. 修改集中在 `creative/comfyui/scripts/run_workflow.py`
2. _url 是热点函数（10 次调用），修改需向后兼容
3. 无外部调用者，可安全重构
4. 测试集中在 `creative/comfyui/tests/test_run_workflow.py`

---
（后续是具体 Task 列表）
```

## 与 plan skill 的关系

此钩子是 `software-development/plan` 的**前置步骤**：

```
用户任务 → codebase-memory-first → plan → todo 推进 → 执行
```

codebase-memory-first 的输出**直接写入 plan 文档**的"Codebase Memory 查询结果"章节。

## 自动化建议（未来）

可通过 Hermes 钩子系统自动触发：

```bash
# ~/.hermes/hooks/pre-plan.sh
#!/bin/bash
if [[ "$HERMES_CONTEXT" == *"code"* ]]; then
  codebase-memory-mcp cli list_projects
  # 根据任务关键词自动搜索
fi
```

当前手动执行，未来可集成到 `hermes chat` 的 preflight 钩子。

## 与 graphify 的分工（2026-07-14 审查确立）

codebase-memory 和 graphify 不是替代关系，而是互补。按问题类型选择：

| 问题 | 用谁 | 理由 |
|------|------|------|
| "这个函数在哪/谁调用了它" | codebase-memory | 持久化索引 + Cypher，毫秒级查询 |
| "这个改动影响哪些调用链" | codebase-memory | detect_changes + trace_path |
| "debug 报错栈，追调用链" | codebase-memory | trace_path inbound/outbound |
| "重构前查上下游" | codebase-memory | search_graph + get_architecture |
| "某函数源码" | codebase-memory | get_code_snippet |
| "这个 PR 影响哪些模块" | graphify | triage_prs / get_pr_impact (cbm 无 PR 工具) |
| "哪些 PR 值得 review" | graphify | triage_prs (cbm 无 PR 工具) |
| "架构总览报告" | graphify | GRAPH_REPORT.md + graph.html |
| "代码+文档+PDF+图片一起建图" | graphify | 支持非代码资产 (cbm 仅代码) |
| "社区检测可视化" | graphify | graph.html (cbm 有 clusters 但无 HTML 可视化) |

> PITFALL — graphify-mcp 服务的是**已存在的 graph.json**，不自动增量索引。
> 代码变更后必须先跑 `graphify <path> --code-only` 或 `graphify <path> --update`
> 重建图，graphify-mcp 才能查到最新状态。codebase-memory 则有持久化索引 +
> detect_changes 自动增量更新。用于"代码搜索/调用链追踪"时选 codebase-memory，
> 不要用 graphify（图可能过时）。用于"PR 审查"时选 graphify（cbm 无 PR 工具）。

## Pitfalls

- **项目名称不是路径**：用 `list_projects` 查实际项目名称（如 `home-lan-.hermes-skills`）
- **大仓库索引 OOM**：>20K 文件分目录索引，或增加 swap
- **查询结果过多**：加 `limit` 参数，或用 cypher 精确过滤
- **索引过时**：git 变更后跑 `detect_changes` 或重新索引

## 验证

跑完钩子后应能回答：
- [ ] 哪些文件会改动？
- [ ] 谁调用了这些文件？
- [ ] 改动会影响哪些模块？
- [ ] 测试文件在哪里？

如果以上问题仍模糊，说明查询不够，继续深挖。

---
Generated by Hermes
      - 查代码结构
      - 先读代码
