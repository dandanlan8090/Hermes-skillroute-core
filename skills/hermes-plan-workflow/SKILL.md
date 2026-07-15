---
name: hermes-plan-workflow
description: 'Plan + todo 推进工作流：任何工具调用前先用 plan 规划再 todo 推进。
  Use for any task that will trigger tool calls: ops/deploy/bugfix/coding/research with 3+ steps.
  禁用：纯文本回答、一次性只读查询、单步可完成的操作。'
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
      - 计划
      - 规划
      - 拆解
      - 任务规划
      - 分步
      - 方案制定
      - 安排任务
      - 怎么做
      - 步骤
      - plan
      - 设计方案
      disable:
      - 纯文本回答
      - 只读查询
      - 单步操作
      - 分几期
      - 拆分交付
    skill_type: workflow
    priority: high
---
# Plan + Todo 推进工作流

## 核心规则

任何用户消息只要会触发工具调用（terminal / file / patch / execute_code / delegate_task / cronjob 等），
第一步就是写 markdown plan 文件 + todo 推进。

## 免 plan 的两类

- 纯文本回答（无工具调用）
- 一次性单命令查询（ls / read_file / read-only 探查）

## 执行顺序

1. 评估是否触发工具调用
2. 写 plan 文件到 `.hermes/plans/<slug>.md`（结论前置、≤2-5min 粒度）
3. todo 工具推进
4. 执行 + verification

## 决策树

```
用户消息 → 是否需要工具调用？
  ├─ 否（纯文本）→ 直接答
  └─ 是 → 写 plan → todo 推进 → 执行 → 验证
```

## Plan 文件格式

- 文件路径：`.hermes/plans/YYYY-MM-DD_HHMMSS-<slug>.md`
- 结论前置
- 每个步骤 ≤ 2-5 分钟粒度
- 不写冗长原理
