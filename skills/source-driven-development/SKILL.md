---
name: source-driven-development
description: 源码驱动开发：每个框架相关实现决策必须引用官方文档。Use when building with any framework or library,
  writing boilerplate patterns, or when the user asks for verified/correct implementation.
  禁用：纯逻辑（循环/变量重命名）、用户明确要求快速完成不验证时。
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
      - 框架
      - 官方文档
      - 源码
      - 官方示例
      - best practice
      - framework
      - library
      - 文档验证
      - 源码驱动
      - implement
      - boilerplate
      - API 签名
      disable:
      - 纯逻辑实现
      - 变量重命名
      - typo 修复
      - 文件移动
      - 用户说不要验证
      - 单行脚本
    skill_type: methodology
    priority: high
    related_skills:
    - hermes-oracle-mode
    - plan
    - doubt-driven-development
prerequisites:
  commands:
  - terminal
  - web_extract
---
# Source-Driven Development（源码驱动开发）

## Overview

每个框架相关代码决策必须以官方文档为依据。不用记忆实现——先验证、再引用、让用户看到来源。

训练数据会过时，API 会废弃，最佳实践会演进。本 skill 确保用户获得的代码可信赖：每个模式都能追溯到可核查的权威来源。

## When to Use

- 用户要求代码遵循当前最佳实践
- 构建 boilerplate、起始代码、跨项目复制的模式
- 用户明确要求"有据可查"或"正确实现"
- 实现依赖框架推荐方式的特性（表单、路由、数据获取、状态管理、认证）
- 审查或改进使用框架特定模式的代码
- **即将凭记忆写框架相关代码时**

**When NOT to use**：
- 正确性不依赖特定版本（变量重命名、typo 修复、文件移动）
- 纯逻辑，所有版本通用（循环、条件、数据结构）
- 用户明确要求速度优先（"快就行"）

## 核心流程

```
DETECT ──→ FETCH ──→ IMPLEMENT ──→ CITE
  │          │           │            │
  ▼          ▼           ▼            ▼
检测堆栈    获取文档    遵循文档     展示来源
```

## Step 1：检测堆栈和版本

读取项目依赖文件确认精确版本：

| 依赖文件 | 堆栈 |
|---------|------|
| `package.json` | Node / React / Vue / Angular / Svelte |
| `composer.json` | PHP / Symfony / Laravel |
| `requirements.txt` / `pyproject.toml` | Python / Django / Flask |
| `go.mod` | Go |
| `Cargo.toml` | Rust |
| `Gemfile` | Ruby / Rails |

显式声明检测结果：

```
STACK DETECTED:
- React 19.1.0 (from package.json)
- Vite 6.2.0
- Tailwind CSS 4.0.3
→ Fetching official docs for the relevant patterns.
```

**版本缺失或模糊时，必须问用户，不要猜测。**

## Step 2：获取官方文档

获取目标特性的具体文档页。不是首页，不是全套文档，是相关页面。

**来源权威性优先级**：

| 优先级 | 来源 | 示例 |
|:---:|------|------|
| 1 | 官方文档 | react.dev, docs.djangoproject.com |
| 2 | 官方博客 / changelog | react.dev/blog, nextjs.org/blog |
| 3 | Web 标准参考 | MDN, web.dev, html.spec.whatwg.org |
| 4 | 浏览器/运行时兼容性 | caniuse.com, node.green |

**非权威来源，不得作为主要引用**：
- Stack Overflow 答案
- 博客或教程
- AI 生成的文档或摘要
- 自己的训练数据

**获取要精准**：

```
❌ 获取 React 首页
✅ 获取 react.dev/reference/react/useActionState

❌ 搜索 "django authentication best practices"
✅ 获取 docs.djangoproject.com/en/6.0/topics/auth/
```

获取后提取关键模式，标注废弃警告或迁移指引。

**官方来源之间冲突时**（如迁移指南与 API 参考矛盾），向用户呈现差异，并用检测到的版本实际验证哪个模式可用。

## Step 3：按文档模式实现

- 使用文档中的 API 签名，不用记忆
- 文档展示了新方式，用新方式
- 文档废弃了某模式，不用废弃版本
- 文档未覆盖的内容，标注为未验证

**文档与现有代码冲突时**：

```
CONFLICT DETECTED:
现有代码使用 useState 处理表单加载状态，
但 React 19 文档推荐 useActionState。

来源：react.dev/reference/react/useActionState

选项：
A) 用现代模式（useActionState）— 与当前文档一致
B) 匹配现有代码（useState）— 与代码库一致

→ 你倾向哪个方案？
```

**必须呈现冲突，不能静默选择。**

## Step 4：引用来源

每个框架特定模式必须附引用。用户必须能核查每个决策。

**代码注释引用**：

```typescript
// React 19 表单处理 with useActionState
// Source: https://react.dev/reference/react/useActionState#usage
const [state, formAction, isPending] = useActionState(submitOrder, initialState);
```

**对话中引用**：

```
使用 useActionState 而非手动 useState 处理表单提交状态。
React 19 用此 hook 替换了手动 isPending/setIsPending 模式。

来源：https://react.dev/blog/2024/12/05/react-19#actions
"useTransition now supports async functions [...] to handle
pending states automatically"
```

**引用规则**：
- 完整 URL，不缩短
- 优先带锚点的深度链接（`/useActionState#usage` 优于 `/useActionState`），锚点在文档重构后更稳定
- 引用非显而易见的决策时附上原文
- 推荐平台特性时包含浏览器/运行时支持数据
- **找不到文档的模式，必须显式声明**：

```
UNVERIFIED: 未找到该模式的官方文档。
基于训练数据，可能已过时。
生产使用前请验证。
```

对无法验证的内容诚实，比虚假置信更有价值。

## Common Rationalizations

| 常见借口 | 真相 |
|---|---|
| "我对这个 API 很有把握" | 有把握不等于有证据。训练数据中含有过时模式，看起来正确但在新版本上会坏掉。必须验证。 |
| "获取文档浪费 token" | 虚构 API 更浪费。用户花一小时 debug，最后发现函数签名已变。获取一次，防止大量返工。 |
| "文档不会有我要的东西" | 文档没覆盖本身是有价值的信息——该模式可能未被官方推荐。 |
| "提一下可能过时就行了" | 免责声明没有帮助。要么验证并引用，要么明确标注未验证。含糊其辞是最差选项。 |
| "这是简单任务，不用检查" | 简单任务中的错误模式会成为模板。用户会把这个废弃的表单处理器复制到十个组件里，才发现现代方案已存在。 |

## Red Flags

- 写框架相关代码但未检查该版本的文档
- 用"我相信"/"我觉得"描述 API 而不引用来源
- 实施某模式但不知道它适用于哪个版本
- 引用 Stack Overflow 或博客而非官方文档
- 使用因出现在训练数据中的废弃 API
- 实现前未读取 `package.json` / 依赖文件
- 交付框架相关决策的代码但无来源引用
- 获取整个文档站而非一个相关页面

## Verification Checklist

- [ ] 从依赖文件识别了框架和库版本
- [ ] 为框架特定模式获取了官方文档
- [ ] 所有来源均为官方文档，非博客或训练数据
- [ ] 代码遵循当前版本文档中的模式
- [ ] 非平凡决策包含完整 URL 来源引用
- [ ] 未使用废弃 API（已对照迁移指南检查）
- [ ] 文档与现有代码的冲突已向用户呈现
- [ ] 无法验证的内容已明确标注为未验证

---

**最后更新**: 2026-07-09
**参考来源**: https://github.com/addyosmani/agent-skills