---
name: hermes-tdd-workflow
description: >
  TDD 工作流：先写 failing test 验证失败 → 写实现 → 验证通过。Covers RED/GREEN/REFACTOR cycle, Prove-It Pattern for bugs, Test Pyramid guidance.
  Use when implementing new features, fixing bugs, adding edge cases, or modifying existing functionality.
  Not for pure config changes, documentation updates, or static content.
version: 1.1.0
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
      - TDD
      - 测试驱动
      - 单元测试
      - pytest
      - unittest
      - 先写测试
      - 测试先行
      - 写测试
      - 自动化测试
      - test-driven
      - red-green-refactor
      - bug fix
      - 复现bug
      - regression
      - prove-it pattern
      disable:
      - 纯配置变更
      - 文档更新
      - 静态内容
      - 单行脚本
      - 一次性探查
    skill_type: methodology
    priority: normal
    related_skills:
    - debugging-patterns
    - source-driven-development
    - code-review-and-audit
prerequisites:
  commands:
  - terminal
  - read_file
  - patch
---
# Test-Driven Development (TDD)

## Overview

Write a failing test before writing the code that makes it pass. For bug fixes, reproduce the bug with a test before attempting a fix. Tests are proof — "seems right" is not done.

## When to Use

- Implementing any new logic or behavior
- Fixing any bug (the Prove-It Pattern)
- Modifying existing functionality
- Adding edge case handling
- Any change that could break existing behavior

**When NOT to use:** Pure configuration changes, documentation updates, or static content changes with no behavioral impact. One-line throwaway scripts.

---

## The TDD Cycle

```
    RED                GREEN              REFACTOR
 Write a test    Write minimal code    Clean up the
 that fails  ──→  to make it pass  ──→  implementation  ──→  (repeat)
      │                  │                    │
      ▼                  ▼                    ▼
   Test FAILS        Test PASSES         Tests still PASS
```

### Step 1: RED — Write a Failing Test

Write the test first. It must fail. A test that passes immediately proves nothing.

```python
# RED: This test fails because create_task doesn't exist yet
def test_create_task():
    task = task_service.create_task(title="Buy groceries")
    assert task.id is not None
    assert task.title == "Buy groceries"
    assert task.status == "pending"
```

### Step 2: GREEN — Make It Pass

Write the minimum code to make the test pass:

```python
# GREEN: Minimal implementation
def create_task(title: str) -> Task:
    return Task(id=generate_id(), title=title, status="pending", created_at=datetime.now())
```

### Step 3: REFACTOR — Clean Up

With tests green, improve the code without changing behavior: extract shared logic, improve naming, remove duplication. Run tests after every refactor step.

---

## The Prove-It Pattern (Bug Fixes)

Bug reported → Write reproduction test → Test FAILS (bug confirmed) → Fix → Test PASSES (fix proven) → Full suite (no regressions).

```python
# Bug: "Completing task doesn't set completedAt"
# Step 1: Reproduction test (FAILS)
def test_completed_task_has_timestamp():
    completed = task_service.complete_task("test-id")
    assert completed.completed_at is not None  # Fails → bug confirmed

# Step 2: Fix
def complete_task(id: str) -> Task:
    return db.tasks.update(id, {"status": "completed", "completed_at": datetime.now()})

# Step 3: Test PASSES → fixed, guarded
```

---

## The Test Pyramid

```
          /\           E2E (~5%) — Full user flows
         /  \
        /────\
       /      \       Integration (~15%) — API boundaries
      /────────\
     /          \     Unit (~80%) — Pure logic, milliseconds
    /────────────\
```

### Test Sizes

| Size | Constraints | Speed |
|------|------------|-------|
| Small | Single process, no I/O | ms |
| Medium | localhost only | s |
| Large | External services | min |

---

## Framework Detection

| Condition | Framework |
|-----------|-----------|
| `pyproject.toml` | pytest |
| `package.json` | npm test |
| `go.mod` | go test |
| `Cargo.toml` | cargo test |

---

## Sunk Cost Red Rule

Code without tests → delete, rewrite. Do not keep as reference.

---

**Reference:** https://github.com/addyosmani/agent-skills
