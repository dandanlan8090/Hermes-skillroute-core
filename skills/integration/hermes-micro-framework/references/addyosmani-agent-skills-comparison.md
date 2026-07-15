# addyosmani/agent-skills 对比分析

对比日期: 2026-07-10
分析目的: 决定是否将 addyosmani/agent-skills 的技能吸收到 hermes-micro-framework
源仓库: https://github.com/addyosmani/agent-skills (76,514 stars)

---

## 原始数据

| 维度 | addyosmani/agent-skills | hermes-micro-framework |
|------|------------------------|------------------------|
| 技能数 | 24 | 44 |
| 格式 | SKILL.md + YAML frontmatter (name+description only) | SKILL.md + 完整 Hermes metadata (trigger/disable/skill_type/priority) |
| Frontmatter | 无 trigger tags → 不适用 vdb 按需加载 | 7+ trigger tags, 4+ disable tags → vdb 语义检索 |
| 适用平台 | Claude Code / Cursor / Codex | Hermes Agent |
| 风格 | 工程实战型，带代码示例 | 方法论 + 约束型，按铁律组织 |
| 质量 | 很高，生产级 | 参差不齐 |

---

## 重叠技能（10 个）

| addyosmani | 我们的 | 质量对比 | 合并建议 |
|-----------|--------|---------|---------|
| `source-driven-development` | `source-driven-development` | 接近 | 吸收 Their STACK DETECT 流程 |
| `doubt-driven-development` | `doubt-driven-development` | 相当 | 不动（我们的 subagent 约束更强） |
| `code-simplification` | `code-simplification` | addyosmani 更全（331行） | 吸收 Five Principles |
| `code-review-and-quality` | `code-review-and-audit` | 互补（偏前端 vs 通用） | 不动 |
| `test-driven-development` | `hermes-tdd-workflow` | addyosmani 更全（383行） | 吸收 RED/GREEN/REFACTOR 流程 |
| `planning-and-ta<api-key>` | `plan` + `hermes-plan-workflow` | 互补 | 吸收 vertical slicing 部分 |
| `git-workflow-and-versioning` | `hermes-git-worktree` | addyosmani 更全（含 commit 规范/semver/changelog） | 吸收扩展到 workflow 级 |
| `security-and-hardening` | `hermes-safety` | 不同领域（web 安全 vs 代码安全） | 不动 |
| `shipping-and-launch` | `hermes-shipping-verification` | 相当 | 不动 |
| `debugging-and-error-recovery` | `debugging-patterns` + `hermes-fault-troubleshooting` | addyosmani 更全 | 吸收 Production Bug Response |

---

## 缺失但值得新增（6 个）

评估标准：
- 通用性：不绑定特定框架/平台
- 可复用性：至少 3 个以上场景能用
- 方法论性：不是工具教程

| 技能 | 建议分类 | 理由 |
|------|---------|------|
| `ci-cd-and-automation` | workflow/ | 质量门控/CI 工具链，72k star 验证的 CI/CD 实践 |
| `spec-driven-development` | methodology/ | 写 spec 再编码，强方法论 |
| `incremental-implementation` | methodology/ | 渐进式实现，避免大改 |
| `api-and-interface-design` | methodology/ | API 设计规范，前端无关 |
| `performance-optimization` | methodology/ | 前端+后端+数据库性能，保留核心方法论（测量→瓶颈→修复→验证→防护） |
| `deprecation-and-migration` | methodology/ | 代码淘汰与迁移方法论，Hyrum's Law 等 |

---

## 排除的技能（8 个）

| 技能 | 排除原因 |
|------|---------|
| `frontend-ui-engineering` | React/HTML/CSS 实现模式，偏框架 |
| `browser-testing-with-devtools` | 工具教程性质 |
| `context-engineering` | CLAUDE.md 写作指南，不适用 Hermes |
| `observability-and-instrumentation` | 偏运维，和微框架无关 |
| `interview-me` | 用户特定 |
| `idea-refine` | 元技能（帮用户理清想法） |
| `using-agent-skills` | 元技能（教人用这个 repo） |

---

## 方法论：外部技能评估流程

当需要评估外部技能仓库是否融入框架时：

```
Step 1: 目录结构扫描
  → ls / find 了解整体布局
  → 判断格式兼容性（.md? .yaml? 纯文本？）

Step 2: 同类定位
  → 按名称/描述匹配已有技能
  → 标记：重叠/缺失/无关

Step 3: 质量评估
  → 读取重叠技能的 SKILL.md
  → 对比已有版本：深度/广度/准确性
  → 决策：吸收精华 / 保持现状 / 替换

Step 4: 格式适配
  → 需要转 Hermes 格式
  → 需补充 trigger/disable tags
  → 需分配 skill_type/priority
  → 需放入正确分类目录（core/workflow/methodology/infrastructure/integration）

Step 5: 发布前检查
  → 脱敏（原作者信息保留 attribution）
  → vdb 重建
  → SOUL.md 路由表 + README.md 同步
```
