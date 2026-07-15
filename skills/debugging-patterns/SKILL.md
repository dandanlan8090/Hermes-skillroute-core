---
name: debugging-patterns
description: >
  Interactive code debugging — Python (pdb/debugpy) and Node.js (inspect/CDP). Systematic 5-step debugging process: Reproduce → Localize → Reduce → Fix Root Cause → Guard. Also covers flaky test diagnosis and git bisect.
  Not for pure ops failures (see hermes-fault-troubleshooting) or code review without debugging.
version: 1.2.0
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
      - 调试
      - debug
      - 错误排查
      - 排错
      - 排查
      - 代码不工作
      - pdb
      - 报错
      - exception
      - traceback
      - 异常
      - 定位问题
      - 代码报错
      - 断点调试
      - git bisect
      - 复现bug
      - 性能问题排查
      - flaky test
      disable:
      - 运维故障
      - 服务挂了
      - 配置错误
      - 网络问题
      - 纯文档审查
      - 部署问题
    skill_type: methodology
    priority: high
    related_skills:
    - hermes-fault-troubleshooting
    - source-driven-development
    - hermes-tdd-workflow
prerequisites:
  commands:
  - terminal
  - read_file
---
# Systematic Debugging

## Iron Law
Never fix without finding root cause. Symptom fixes = failure.

## The 5-Step Debugging Process

### Step 1: Reproduce (Replicate the Failure)

Before diagnosing, confirm you can reproduce the failure reliably:

- Run the failing command/code again — is it consistent?
- Note exact error message, stack trace, and input
- Save reproduction log: `command 2>&1 | tee /tmp/repro.log`
- For flaky failures, run 3-5 times to gauge frequency

**Flaky failures** (intermittent, non-deterministic):

```
Flaky checklist:
├── Race condition?  → Check shared state, async ordering
├── Environment-dependent? → Compare versions, OS, env vars
├── State-dependent? → Check leaked state, global variables
└── Truly random?    → Defensive logging, document conditions
```

**For flaky test failures:**
```bash
npm test -- --grep "test name"          # Run specific test
npm test -- --runInBand                  # Run in isolation (rules out test pollution)
```

### Step 2: Localize (Narrow Down Location)

Identify which layer is failing:

```
├── UI/Frontend     → Console, DOM, network tab
├── API/Backend     → Server logs, request/response
├── Database        → Queries, schema, data integrity
├── Build tooling   → Config, dependencies, environment
└── External service → Connectivity, API changes, rate limits
```

**Use git bisect for regression bugs:**
```bash
git bisect start
git bisect bad                    # Current commit is broken
git bisect good <known-good-sha>  # This commit worked
git bisect run npm test -- --grep "failing test"
```

### Step 3: Reduce (Create Minimal Reproduction)

Remove unrelated code/config until only the bug remains:

- Simplify input to smallest example that triggers the failure
- Strip to bare minimum that reproduces the issue
- A minimal reproduction makes root cause obvious

### Step 4: Fix the Root Cause (Not the Symptom)

```
Symptom: "User list shows duplicate entries"

Symptom fix (bad): Deduplicate in UI: [...new Set(users)]
Root cause fix (good): The API JOIN produces duplicates → fix query, add DISTINCT
```

Ask "Why?" until you reach the actual cause, not just where it manifests.

### Step 5: Guard Against Recurrence

Write a test that catches this specific failure. Integration test > unit test > manual check.

---

## Python Debugging (pdb / debugpy)

```bash
# pdb
python -m pdb script.py

# debugpy
python -m debugpy --listen 5678 --wait-for-client script.py
```

**Workflow:**
1. Set breakpoint: `breakpoint()` or `import pdb; pdb.set_trace()`
2. Run until breakpoint
3. Inspect: `p variable`, `locals()`, `dir(obj)`
4. Step: `n` (next), `s` (step into), `c` (continue)

**Conditional breakpoints:**
```python
breakpoint() if condition else None
# In pdb:  b 42, x > 10
```

## Node.js Debugging (inspect / CDP)

```bash
node --inspect script.js
node --inspect-brk script.js  # Pause at start
```

## Tool Selection

| Situation | Tool |
|-----------|------|
| Quick script | pdb |
| Complex app, remote | debugpy |
| Node.js backend | inspect / CDP |
| CI/debugging tests | pytest --pdb or --trace |
| Post-mortem | python -m pdb -c c core.dump |
| Regression search | git bisect |

## 3-Strike Rule

Same issue fails to fix 3 times → Stop. Ask if architecture is wrong, if module should be rewritten, if YAGNI was violated.

---

**Reference:** https://github.com/addyosmani/agent-skills
