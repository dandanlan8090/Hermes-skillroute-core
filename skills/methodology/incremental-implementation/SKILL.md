---
name: incremental-implementation
description: >
  Incremental implementation: build features in small, verifiable vertical slices. Use when a feature is complex, has multiple layers (db→api→ui), or needs parallel work across team members.
  Not for trivial single-file changes or throwaway scripts.
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
      - 增量实现
      - incremental
      - 增量交付
      - 分期交付
      - 分步实现
      - 分阶段
      - vertical slice
      - 垂直切片
      - MVP
      - 最小可行
      - 渐进式
      - 分批
      - 逐步
      disable:
      - 单文件改动
      - 临时脚本
      - 用户已给出精确步骤
    skill_type: methodology
    priority: normal
    related_skills:
    - plan
    - spec-driven-development
    - hermes-plan-workflow
prerequisites:
  commands:
  - terminal
  - read_file
  - write_file
---
# Incremental Implementation

## Overview

Build features in small, verifiable, vertical slices. Each slice delivers working, testable functionality end-to-end. This reduces risk, makes progress visible, and enables course-correction after each slice.

**Horizontal slicing (bad):** Build all DB → all API → all UI → connect
**Vertical slicing (good):** User can create account (DB+API+UI) → User can log in → User can create task → ...

## When to Use

- Complex features spanning multiple layers
- Work across multiple team members or agents
- Requirements are partially known (iterate per slice)
- You need to ship something quickly

**When NOT to use:** Single-file changes with obvious scope.

## The Incremental Process

### Step 1: Map Dependency Graph

```
Database schema → API models → API endpoints → Frontend client → UI
```

Implementation follows the graph bottom-up: build foundations first.

### Step 2: Slice Vertically

Instead of building all layers horizontally, build one complete feature path per slice. Each slice:

- Delivers a user-visible outcome
- Is independently testable
- Can be shipped independently
- Has clear scope boundaries

### Step 3: Write Slice Tasks

Each slice task:
1. Short description of the slice
2. Acceptance criteria (at most 3-5 per slice)
3. Verification steps
4. Dependencies on other slices

### Step 4: Implement One Slice at a Time

- Do not mix work across slices
- Complete and verify before moving to next
- Run full test suite after each slice
- Commit each slice separately

## Verification Checklist

- [ ] Dependency graph mapped
- [ ] Slices are vertical (not horizontal)
- [ ] Each slice has acceptance criteria
- [ ] Each slice is independently testable
- [ ] Slices implemented one at a time
- [ ] Full test suite passes after each slice

---

**Reference:** https://github.com/addyosmani/agent-skills
