# benchmark-case-set — Hermes vdb 检索评估 query 集

## 名称映射（benchmark 期望名 → 索引名）

```python
renamed = {
    "segment-anything":           "segment-anything-model",
    "audiocraft":                  "audiocraft-audio-generation",
    "hermes-evolution-rules":     "hermes-framework-evolution",
    "spec-driven-development":    "hermes-plan-workflow",
    "github":                      "codebase-memory-first",
    "system-admin":                "hermes-truth-redline",  # "系统信息是什么"/"装服务到ubuntu"
}
```

> ⚠️ 运行 benchmark 前必须先应用此映射。SKILL.md 的 `name` 不一定等于用户期望的简称。

## 61 条正式集（路由表 + 场景覆盖）

### 路由/框架类
| query | 期望 skill（索引名）| 备注 |
|-------|---------------------|------|
| 写个 TDD 测试 | hermes-tdd-workflow | |
| 帮我 review 一下这段代码 | code-review-and-audit | |
| 调试一下报错信息 | debugging-patterns | 与 fault-troubleshooting 对比 |
| 部署 flask 到生产环境 | hermes-shipping-verification | |
| 写一个 plan | hermes-plan-workflow | |
| 看看代码性能瓶颈 | performance-optimization | |
| git 怎么用 worktree 隔离分支 | hermes-git-worktree | |
| 写个 agent skill | hermes-agent-skill-authoring | |
| 帮我搜索一下最新的 AI 论文 | arxiv | |
| 合并代码到主分支 | codebase-memory-first | 名称：github→codebase-memory-first |
| 这个页面交互有点问题 | dogfood | |
| 同步配置文件到 base config | hermes-base-config-sync | |
| 系统信息是什么 | hermes-truth-redline | 名称映射：system-admin→hermes-truth-redline |
| 先查 codebase 再改代码 | codebase-memory-first | |
| 装一个服务到 ubuntu | hermes-truth-redline | |
| 发一条推特 | xurl | |
| 单元测试怎么写 | hermes-tdd-workflow | |
| 代码简化一下 | code-simplification | |
| 看看我的待办列表 | hermes-todo-progress | |
| 帮我排错 | debugging-patterns | 与 fault-troubleshooting 对比 |
| 发布新版本 | hermes-shipping-verification | |
| Oracle Mode 调度一下 | hermes-oracle-mode | |
| YouTube 视频摘要 | youtube-content | |
| 检查一下安全规范 | hermes-safety | |
| 实验数据可视化分析 | jupyter-live-kernel | |
| 消息既然你已发出去 | yuanbao | |
| 配置 CI/CD 流水线 | ci-cd-and-automation | |
| 写一个 API 接口文档 | api-and-interface-design | |
| 重构老系统迁移方案 | deprecation-and-migration | |
| 增量实现这个功能 | incremental-implementation | |
| debug the segmentation fault | debugging-patterns | |
| run inference on this model | mlops-inference | |
| search arxiv for NLP papers | arxiv | |
| evaluate model on MMLU | mlops-evaluation | |
| what's trending on twitter | xurl | |
| video transcript and summary | youtube-content | |
| segment objects in this image | segment-anything-model | 名称映射 |
| generate music from text | audiocraft-audio-generation | 名称映射 |
| find me a GIF for this | gif-search | |
| send an email | himalaya | |
| turn on the living room lights | openhue | |
| query polymarket for prices | polymarket | |
| check blog feed for updates | blogwatcher | |
| knowledge base from wiki | llm-wiki | |
| 确认一下部署结果 | hermes-verification-rules | |
| 不要编造任何信息 | hermes-truth-redline | |
| 信息真实性确认 | hermes-truth-redline | |
| agent 协作架构 | agent-collaboration-workflow | |
| framework 文件加载规则 | hermes-framework-loader | |
| 微内核框架架构 | hermes-framework-architecture | |
| fault troubleshooting | hermes-fault-troubleshooting | |
| changelog 更新了啥 | hermes-framework-changelog | 名称映射：hermes-evolution-rules→hermes-framework-evolution |
| 框架演进规则 | hermes-framework-evolution | |
| 开闭原则怎么落地 | doubt-driven-development | |
| 写代码前先查官方文档 | source-driven-development | |
| 用 openai 兼容模型的思考链 | openai-compat-thinking | |
| vdb 检索怎么工作的 | vdb-retrieval-pipeline | |
| self-optimize my system prompt | hermes-self-optimization | |
| 并行派发多个 agent | hermes-parallel-dispatch | |
| 批量调研这个话题 | agent-reach | |

## 17 条自然语言集（harder set，模拟口语 query）

| query | 期望 skill | 关键 trigger | 已知难度 |
|-------|------------|-------------|---------|
| 帮我部署一下这个服务 | hermes-shipping-verification | 部署服务 | dense=3 vs system-admin |
| 排查一下为什么报错 | debugging-patterns | 排查,报错 | dense=9 vs fault=1 |
| 配置一下这个环境 | hermes-truth-redline | 配置环境 | dense=1 vs system-admin |
| 发消息到群组 | yuanbao | | ✅ 已命中 |
| 查一下最近的新论文 | arxiv | | ✅ 已命中 |
| 这个项目的代码质量怎么样 | code-review-and-audit | 代码质量 | dense=15，太低 |
| 写一个测试驱动开发的案例 | hermes-tdd-workflow | | ✅ 已命中 |
| 框架的加载规则是什么样的 | hermes-framework-loader | 加载规则 | dense=2 vs source-driven |
| 帮我看看这个技能怎么创建 | hermes-agent-skill-authoring | 创建技能 | dense=2 vs autoload |
| 系统服务启动不了 | hermes-fault-troubleshooting | 服务启动不了 | dense=4 vs system-admin |
| 怎么优化这个查询性能 | performance-optimization | | ✅ 已命中 |
| 帮我审查一下这段代码 | code-review-and-audit | | ✅ 已命中 |
| 增量交付这个功能 | incremental-implementation | 增量交付 | ✅ 已命中 |
| 文档上说这个 API 怎么调 | api-and-interface-design | | ✅ 已命中 |
| 把这个功能拆成几期交付 | incremental-implementation | 分期交付 | ✅ 已命中 |
| 配置一下 CI/CD | ci-cd-and-automation | | ✅ 已命中 |
| 并行调研几个技术方案 | agent-reach | 并行调研,批量调研 | dense=? vs plan-workflow |

## 当前基准结果（P2+F，2026-07-11）

```
61条正式集:  T1=54/60 (90.0%)  T3=57/60 (95.0%)
17条harder: T1=12/17 (70.6%)  T3=16/17 (94.1%)
```

### 正式集 6 条 remain
- 调试一下报错信息 → fault-troubleshooting（dense=1 无法翻盘）
- 同步配置文件到 base config → framework-loader（dense 问题）
- 装一个服务到 ubuntu → system-admin（dense 问题）
- 帮我排错 → fault-troubleshooting（同上）
- changelog 更新了啥 → evolution-rules（同上）
- 开闭原则怎么落地 → repo-publishing-workflow（dense 问题）

### harder remain（dense-rank-1 压制，无法通过 sparse 解决）
- 帮我部署一下这个服务 → system-admin（dense=3 vs shipping=?）
- 排查一下为什么报错 → fault-troubleshooting（dense=1 vs debug=9）
- 配置一下这个环境 → hermes-agent（dense=1）
- 框架的加载规则是什么样的 → source-driven（dense=2 vs framework-loader=?）
- 帮我看看这个技能怎么创建 → autoload-vdb（dense=2 vs skill-authoring=?）
- 并行调研几个技术方案 → plan-workflow（待查 dense）