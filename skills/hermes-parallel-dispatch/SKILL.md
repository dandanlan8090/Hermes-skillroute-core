---
name: hermes-parallel-dispatch
description: '并行 Agent 派发：多个独立失败的并发调查策略。触发条件包括≥2个独立失败、无共享状态、调查彼此无依赖。
  Use when debugging multiple failures in different files/subsystems, investigating unrelated errors,
  or running parallel analyses on independent components.
  禁用：失败之间可能关联、需要全局系统状态理解、同一分支的并发改动。'
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
      - 并行
      - 同时跑
      - 批量检查
      - dispatch
      - 并发调查
      - 多任务
      - 同时排查
      - 并行分析
      - 多个失败
      - parallel
      disable:
      - 单任务
      - 简单查询
      - 失败可能关联
      - 需要全局理解
      - 调研
    skill_type: methodology
    priority: normal
---
# 并行 Agent 派发

## 触发条件（缺一不可）

- ≥ 2 个独立失败（不同文件/不同子系统）
- 无共享状态
- 调查彼此无依赖

## 不触发

- 失败之间可能互相关联
- 需要全局系统状态理解
- 同一分支上的并发改动

## 实现细节

- 当前 delegate_task 走 background，分发后不阻塞主会话
- 多个 delegate_task 在同一 turn 同 batch 发出 = 并行
- 串序：每个 turn 一个 dispatch
- 不要先串完两次再切并行，浪费 round-trip

## 返回格式约束

每个 subagent prompt 必须包含：

- 具体 scope（哪个文件/子系统）
- 成功率定义（"all tests in <file> pass"）
- 约束（"不要碰 X 之外"）
- 期望输出（一段 summary，含哪些改动）
