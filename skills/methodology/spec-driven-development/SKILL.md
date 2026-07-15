---
name: spec-driven-development
description: >
  Spec-Driven Development: write structured specifications before writing code. Covers the SPECIFY→PLAN→TASKS→IMPLEMENT gated workflow. Use when starting new features, requirements are ambiguous, or the change touches multiple modules.
  Not for single-line fixes, typo corrections, or trivial changes.
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
      - spec
      - 规范先行
      - 需求分析
      - 设计文档
      - 技术方案
      - specification
      - 需求文档
      - 架构设计
      - 方案评审
      - 功能定义
      - feature spec
      - PRD
      - 功能设计
      - 模块设计
      - 功能方案
      - 设计实现
      - system design
      disable:
      - 单行改动
      - typo修复
      - 临时脚本
      - 用户已提供完整spec
    skill_type: methodology
    priority: normal
    related_skills:
    - plan
    - source-driven-development
    - hermes-plan-workflow
prerequisites:
  commands:
  - terminal
  - read_file
  - write_file
---
# Spec-Driven Development

## Overview

Write a structured specification before writing any code. The spec is the shared source of truth — it defines what we're building, why, and how we'll know it's done. Code without a spec is guessing.

## When to Use

- Starting a new project or feature
- Requirements are ambiguous or incomplete
- The change touches multiple files or modules
- About to make an architectural decision
- Task takes more than 30 minutes to implement

**When NOT to use:** Single-line fixes, typo corrections, unambiguous and self-contained changes.

## The Gated Workflow

```
SPECIFY ──→ PLAN ──→ TASKS ──→ IMPLEMENT
```

Do not advance to the next phase until the current one is validated.

### Phase 1: Specify

Surface assumptions immediately before writing any spec content:

```
ASSUMPTIONS I'M MAKING:
1. This is a web application (not native mobile)
2. Authentication uses session-based cookies (not JWT)
3. Database is PostgreSQL (based on existing Prisma schema)
→ Correct me now or I'll proceed with these.
```

**Write a spec covering:**
1. **Objective** — What and why? Who is the user?
2. **Requirements** — Functional + non-functional
3. **Design** — Architecture, data model, API contracts
4. **Edge cases** — Error states, failure modes
5. **Open questions** — What's not decided yet

### Phase 2: Plan

Break the spec into implementable units. Map dependency graph.

### Phase 3: Write Tasks

Each task: Description → Acceptance Criteria → Verification → Dependencies → Files

### Phase 4: Implement

One task at a time, following the spec. Update spec if implementation reveals gaps.

## Verification Checklist

- [ ] Assumptions surfaced and validated
- [ ] Spec covers: objective, requirements, design, edge cases
- [ ] Plan maps dependency graph
- [ ] Tasks have acceptance criteria
- [ ] Implementation follows spec order
- [ ] Spec updated if gaps found during implementation

---

**Reference:** https://github.com/addyosmani/agent-skills
