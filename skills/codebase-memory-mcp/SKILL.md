---

name: codebase-memory-mcp
description: 'codebase-memory-mcp: 代码知识图谱 MCP 服务器 - 索引代码仓库并回答架构/调用图/死代码查询'
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
      - mcp
      - 知识库
      - 代码查询
      - 调用关系
      - 代码图谱查询
      - 索引代码库
      disable:
      - code_development
      - read_only
    category: devops
    related_skills:
    - opencode
    - openclaw
    - code-review-and-audit
---

# codebase-memory-mcp 部署与使用

## 定位

**codebase-memory-mcp** 是高性能代码知识图谱 MCP 服务器，由 DeusData 开发。
- 索引速度：Linux 内核 (28M LOC) 3 分钟
- 查询延迟：<1ms (图遍历)
- Token 节省：120 倍 (3.4K vs 412K tokens)
- 部署形态：单一 C 二进制，零依赖

## 安装部署

### 一键安装 (Linux/macOS)

```bash
curl -fsSL https://raw.githubusercontent.com/DeusData/codebase-memory-mcp/main/install.sh | bash
```

### 验证安装

```bash
codebase-memory-mcp --version
codebase-memory-mcp doctor
```

### 自动集成

安装脚本自动配置以下 Agent 的 MCP 入口：
- OpenCode: `~/.config/opencode/opencode.json`
- OpenClaw: `~/.openclaw/openclaw.json`
- Claude Code, Codex CLI, Gemini CLI (如已安装)

## Hermes 三 Agent 集成

### 架构位置

```
Hermes(主脑)
├── 直接 CLI → codebase-memory-mcp cli ... (推荐，无需 MCP 配置)
├── OpenCode (代码协作) → MCP → codebase-memory-mcp (已配置)
├── OpenClaw (脚本执行) → 直接 CLI 或 MCP → codebase-memory-mcp
└── 图索引存储：~/.cache/codebase-memory-mcp/
```

### 连接方式对比

| Agent | 推荐方式 | 配置需求 | 适用场景 |
|-------|----------|----------|----------|
| **Hermes (agent 会话)** | MCP 原生通道 (已接入 config.yaml) | config.yaml mcp_servers 段 | agent 会话中查询代码图谱 |
| **Hermes (terminal 脚本)** | `codebase-memory-mcp cli <command>` | 无需配置 | 批处理、脚本自动化 |
| **OpenCode** | MCP (自动) | `~/.config/opencode/opencode.json` 已配置 | 代码协作会话中查询 |
| **OpenClaw** | `agent --local` + CLI 命令 | 无需配置 | 脚本执行、批量操作 |

**关键认知**：在 Hermes 环境中，**必须通过原生 MCP 通道接入**（config.yaml
mcp_servers 段），否则 agent 无法在会话中调用 codebase-memory 工具，只会变成摆设。
CLI 调用仍可用于 terminal 脚本场景，但 MCP 通道是 agent 的主路径。

> 更新 (2026-07-14)：已从 mcp.json 独立配置接入 Hermes 原生 config.yaml mcp_servers。
> 接入前 hermes mcp list 不显示 codebase-memory（只在 mcp.json 里），接入后
> ✓ enabled + 14 tools discovered。详见 hermes-mcp-server-setup skill 的
> references/codebase-memory-mcp-setup.md。

### 调用方式

#### 1. CLI 直接调用（推荐）

```bash
# 列出已索引项目
codebase-memory-mcp cli list_projects

# 索引仓库
codebase-memory-mcp cli index_repository '{"repo_path":"/path/to/repo","project_name":"my-project"}'

# 搜索图谱
codebase-memory-mcp cli search_graph '{"project":"my-project","name_pattern":".*Handler.*","limit":10}'

# 获取架构概览
codebase-memory-mcp cli get_architecture '{"project":"my-project"}'

# 追踪调用链
codebase-memory-mcp cli trace_path '{"project":"my-project","function_name":"main","direction":"inbound"}'
```

#### 2. 通过 OpenCode 调用（MCP 协议）

```bash
opencode --attach http://<ip> run "索引这个仓库并分析架构"
```

OpenCode 会自动使用 MCP 工具：
- `search_graph` — 按模式查找函数/类/路由
- `get_architecture` — 获取高级架构摘要
- `trace_path` — 追踪调用链
- `query_graph` — Cypher 风格查询

#### 3. 通过 OpenClaw 调用（CLI 直连）

```bash
openclaw agent --local -m "用 codebase-memory-mcp cli list_projects 列出索引项目"
```

OpenClaw 默认走 `agent --local`模式，可直接在任务描述中包含 CLI 命令，无需 MCP 配置。

#### 4. Hermes 原生 MCP（推荐路径）

Hermes 通过原生 MCP 通道调用 codebase-memory（已接入 config.yaml mcp_servers，
14 tools available）。这是 agent 在会话中的主路径。

```bash
# 已接入，无需额外配置。验证：
hermes mcp list                        # codebase-memory ✓ enabled
hermes mcp test codebase-memory         # ✓ Connected, 14 tools
```

CLI 调用仍适用于 terminal 脚本和批处理场景。

**Pitfall 已验证并修复 (2026-07-14)**：
- **已修复**：`hermes mcp list` 显示 `No MCP servers configured` 曾被视为"正常"——实则 codebase-memory 只在 mcp.json 里（独立配置），Hermes 原生 MCP 通道看不到它。已接入 config.yaml mcp_servers 段，现在 `hermes mcp list` 显示 ✓ enabled，`hermes mcp test codebase-memory` → ✓ Connected, 14 tools。
- OpenCode 的 MCP 配置独立于 Hermes，位于 `~/.config/opencode/opencode.json`（仍有效）
- OpenClaw 默认不配置 MCP 也能通过 CLI 调用（仍有效）
- **接入流程详见** hermes-mcp-server-setup skill → references/codebase-memory-mcp-setup.md

```bash
# 验证当前状态
hermes mcp list                        # codebase-memory ✓ enabled
hermes mcp test codebase-memory        # ✓ Connected, 14 tools
codebase-memory-mcp cli list_projects  # CLI 仍可用于 terminal 脚本
```

## 可用 MCP 工具

| 工具 | 用途 |
|------|------|
| `search_graph` | 按名称/标签/文件范围搜索节点 |
| `get_architecture` | 获取架构概览 (语言/包/入口点/热点/边界/层/聚类) |
| `trace_path` | 追踪函数调用链 (inbound/outbound) |
| `get_code_snippet` | 读取特定函数/类的源代码 |
| `query_graph` | 运行 Cypher 风格查询 |
| `detect_changes` | 检测 git diff 影响的符号 |
| `manage_adr` | 管理架构决策记录 |
| `semantic_query` | 语义搜索 (嵌入向量) |

## 图可视化

```bash
# 启动 Web UI
codebase-memory-mcp --ui=true --port=9749

# 浏览器访问 http://localhost:9749
```

## 索引阈值

| 仓库规模 | 索引时间 | 内存需求 |
|----------|----------|----------|
| < 1K 文件 | <1 秒 | <500MB |
| 1K-5K 文件 | 1-10 秒 | 500MB-1.5GB |
| 5K-20K 文件 | 10-60 秒 | 1.5GB-3GB |
| >20K 文件 | 1-5 分钟 | 3GB+ |

**注意**：大仓库索引可能被 SIGKILL (OOM)，建议分目录索引或增加内存预算。

## 典型工作流

### 1. 新仓库分析

```bash
# 索引
codebase-memory-mcp cli index_repository '{"repo_path":"~/my-project","project_name":"my-project"}'

# 获取架构
codebase-memory-mcp cli get_architecture '{"project":"my-project"}'

# 搜索关键组件
codebase-memory-mcp cli search_graph '{"project":"my-project","name_pattern":".*Service.*","limit":20}'
```

### 2. 代码审查辅助

```bash
# 查找谁调用这个函数
codebase-memory-mcp cli trace_path '{"project":"my-project","function_name":"process_order","direction":"inbound"}'

# 检测死代码
codebase-memory-mcp cli search_graph '{"project":"my-project","label":"Function","min_degree":0}'
```

### 3. 架构重构

```bash
# 识别模块边界
codebase-memory-mcp cli get_architecture '{"project":"my-project","aspects":["boundaries","clusters","layers"]}'

# 查找跨模块调用
codebase-memory-mcp cli query_graph '{"project":"my-project","cypher":"MATCH (a:Module)-[r:CALLS]->(b:Module) WHERE a.name != b.name RETURN a,b,r"}'
```

## 项目持久化

索引数据存储在 `~/.cache/codebase-memory-mcp/graph.db`。

### 导出共享图谱

```bash
# 导出压缩图谱到仓库
.codebase-memory/graph.db.zst
```

团队成员克隆后可跳过完整索引。

## 常见问题

### 索引被 SIGKILL

**原因**：内存超限 (RSS 超过系统限制)

**解决**：
1. 分目录索引：`--repo_path` 指向子目录
2. 减少文件数：设置 `auto_index_limit`
3. 增加系统内存或使用 swap

### 项目找不到

**原因**：CLI 需要 `project` 参数而非 `repo_path`

**解决**：
```bash
# 先列出项目名
codebase-memory-mcp cli list_projects

# 用项目名称查询
codebase-memory-mcp cli get_architecture '{"project":"home-lan-repo-name"}'
```

## 与 Hermes 技能集成

索引 Hermes 技能目录：

```bash
codebase-memory-mcp cli index_repository '{"repo_path":"~/.hermes/skills","project_name":"hermes-skills"}'
```

结果：
- 449 文件
- 9378 节点
- 10778 边
- 索引时间：868ms

## 相关资源

- GitHub: https://github.com/DeusData/codebase-memory-mcp
- arXiv 论文：https://arxiv.org/abs/2603.27277
- 文档：https://github.com/DeusData/codebase-memory-mcp/blob/main/README.md

---
Generated by Hermes
      - 代码图谱查询
      - 索引代码库
