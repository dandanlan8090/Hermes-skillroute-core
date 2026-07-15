# addyosmani/agent-skills 吸收记录

## 来源
- 仓库：https://github.com/addyosmani/agent-skills（76k stars）
- 日期：2026-07-10
- Commit：de0e2eb

## 吸收方法

### Phase A — 重叠吸收（patch 现有 skill）

| 我们的 skill | 吸收内容 | 变更 |
|-------------|---------|------|
| `code-simplification` | 此前已吸收 | 不变 |
| `source-driven-development` | 此前已吸收 | 不变 |
| `hermes-tdd-workflow` | RED/GREEN/REFACTOR 详细流程、Prove-It Pattern、Test Pyramid | patch |
| `hermes-git-worktree` | commit 规范、分支策略、semver、changelog | patch + 扩展 |
| `debugging-patterns` | 5-step 系统排查流程、flaky 诊断、git bisect | patch |

### Phase B — 新增 skill

| skill | 分类 | 基于 addyosmani 同名 skill |
|-------|------|---------------------------|
| `ci-cd-and-automation` | workflow/ | 质量门禁 pipeline + GitHub Actions |
| `performance-optimization` | methodology/ | Measure→Identify→Fix→Verify→Guard |
| `spec-driven-development` | methodology/ | SPECIFY→PLAN→TASKS→IMPLEMENT |
| `deprecation-and-migration` | methodology/ | 废弃决策 + 4 阶段迁移 |
| `incremental-implementation` | methodology/ | 垂直切片增量交付 |
| `api-and-interface-design` | methodology/ | REST + GraphQL 设计规范 |

## 未吸收的技能及理由

| 跳过的 skill | 理由 |
|-------------|------|
| `frontend-ui-engineering` | 前端框架特定（React/Vue），不通用 |
| `browser-testing-with-devtools` | 工具教程性质，非通用方法论 |
| `context-engineering` | CLAUDE.md 写作指南，不适用微框架通用架构 |
| `observability-and-instrumentation` | 偏运维方向，与现有 skill 不搭 |
| `interview-me` | 用户特定，非通用工程技能 |
| `idea-refine` | 元技能，不在工程通用范畴 |
| `using-agent-skills` | 元技能，本框架无需 |

## 转换规则

所有吸收/新增 skill 必须：
1. 补全 Hermes frontmatter：name, description, version, author, license, platforms
2. 补全 metadata/hermes/tags：trigger ≥5, disable ≥3
3. 设置 skill_type（workflow/methodology/infrastructure）
4. 放入正确的分类目录（core/workflow/methodology/infrastructure/integration）
5. 添加 related_skills 建立关联
6. SOUL.md 路由表 + 技能索引同步更新
7. README.md 技能全集同步更新
