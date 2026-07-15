---
name: hermes-todo-progress
description: 'TODO 进度展示规范：每次 todo 工具更新后必须在回复中同步列出全部步骤的内容和状态。
  Use when tracking multi-step tasks with the todo tool, reporting progress, or updating task status.
  禁用：单步任务、无需 todo 的一次性查询。'
version: 1.0.0
author: Hermes
license: MIT
platforms:
- linux
- macos
- windows
metadata:
  hermes:
    tags:
      trigger:
      - TODO
      - 进度
      - 任务跟踪
      - 步骤状态
      - 任务进度
      - 进行中
      - 待办
      - 完成进度
      - progress
      - track task
      disable:
      - 单步任务
      - 一次性查询
      - 纯文本回答
    skill_type: workflow
    priority: normal
---
# TODO 进度展示规范

## 核心规则

每次 `todo` 工具更新后，必须在回复中用显式列表同步展示**全部步骤**的内容和状态。

## 展示格式

```
📋 任务进度
1. ✅ 完成 — [步骤 1 内容]
2. ▶ 进行中 — [步骤 2 内容]
3. ⏳ 待办 — [步骤 3 内容]
```

## 格式要求

- 编号 + 状态图标 + 步骤原文（至少前几个字符明确表意）
- 禁止仅输出紧凑进度编号（如 `📋 plan update 2/4 ✓`）而不展示步骤内容

## 例外

仅当步骤列表已在同会话中刚展示过且未产生新变化时，可简化为「同上步进度」。

## 状态图标

- ✅ completed — 已完成
- ▶ in_progress — 进行中
- ⏳ pending — 待办
- ❌ cancelled — 已取消
