---
name: deprecation-and-migration
description: >
  Deprecation and migration: removing old systems, APIs, or features while safely migrating users. Use when replacing legacy systems, sunsetting features, consolidating duplicates, or removing dead code.
  Not for routine refactoring or simple feature removal.
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
      - 废弃
      - deprecate
      - 迁移
      - migration
      - 下架
      - 移除旧代码
      - sunset
      - 遗留系统
      - 淘汰
      - 重构替换
      - 版本升级
      - consolidate
      disable:
      - 日常重构
      - 简单删除死代码
      - 用户未提及废弃
    skill_type: methodology
    priority: normal
    related_skills:
    - code-simplification
    - code-review-and-audit
prerequisites:
  commands:
  - terminal
  - read_file
---
# Deprecation and Migration

## Overview

Code is a liability, not an asset. Every line has ongoing maintenance cost — bugs, dependency updates, security patches, mental overhead. Deprecation is the discipline of removing code that no longer earns its keep, and migration is the process of moving users safely from old to new.

**Core Principles:**

- **Code is a liability** — when same functionality needs less code, old code should go
- **Hyrum's Law** — with enough users, every observable behavior becomes depended on (including bugs)
- **Deprecation planning starts at design time** — systems with clean interfaces are easier to deprecate

## When to Use

- Replacing an old system, API, or library with a new one
- Sunsetting a feature that's no longer needed
- Consolidating duplicate implementations
- Removing dead code
- Planning lifecycle of a new system

## The Deprecation Decision

```
1. Does this system still provide unique value? → Yes: maintain. No: proceed.
2. How many users/consumers depend on it? → Quantify migration scope.
3. Does a replacement exist? → If no, build replacement first.
4. What's migration cost per consumer? → Weigh against maintenance cost.
5. What's cost of NOT deprecating? → Security risk, engineer time.
```

## The Migration Process

### Phase 1: Announce

- Set clear timeline (deprecation date + removal date)
- Document exactly what's changing and how to migrate
- Provide migration guide, examples, and codemods if possible

### Phase 2: Parallel Run

- Both old and new run simultaneously
- Route a percentage of traffic to new (canary)
- Monitor errors, latency, and correctness
- Have rollback plan ready

### Phase 3: Deprecate

- Mark old as deprecated in docs and code
- Add runtime warnings for direct consumers
- Stop maintaining old — no new features, only critical security fixes

### Phase 4: Remove

- Remove old code, API endpoints, or feature flags
- Archive related docs
- Update dependencies that referenced old
- Celebrate with a metrics review (response time, error rate, maintenance cost)

## Verification Checklist

- [ ] Migration timeline defined and announced
- [ ] All consumers identified and migrated
- [ ] Rollback plan exists
- [ ] Old code fully removed (no dead branches/endpoints)
- [ ] Legacy docs archived
- [ ] Metrics confirm improvement post-migration

---

**Reference:** https://github.com/addyosmani/agent-skills
