---
name: ci-cd-and-automation
description: >
  CI/CD pipeline setup and automation: quality gates, test runners in CI, deployment strategies. Use when setting up build/deployment pipelines, adding automated checks, or establishing release workflows.
  Not for single manual deployments or ad-hoc automation.
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
      - CI/CD
      - pipeline
      - 自动化部署
      - GitHub Actions
      - Jenkins
      - GitLab CI
      - 持续集成
      - 持续部署
      - quality gate
      - 质量门禁
      - lint
      - build
      - deploy pipeline
      - release workflow
      disable:
      - 临时手动部署
      - 单次发布
      - 纯配置无关的测试
    skill_type: workflow
    priority: normal
    related_skills:
    - hermes-shipping-verification
    - code-review-and-audit
prerequisites:
  commands:
  - terminal
  - read_file
---
# CI/CD and Automation

## Overview

Automate quality gates so that no change reaches production without passing tests, lint, type checking, and build. CI/CD catches what humans miss, consistently on every change.

**Shift Left:** Catch problems as early as possible. A bug caught in lint costs minutes; the same bug in production costs hours.

**Faster is Safer:** Smaller batches and frequent releases reduce risk. A deployment with 3 changes is easier to debug than one with 30.

## When to Use

- Setting up a new project's CI pipeline
- Adding or modifying automated checks
- Configuring deployment pipelines
- Debugging CI failures

## The Quality Gate Pipeline

```
Pull Request Opened
    │
    ▼
┌─────────────────┐
│   LINT CHECK     │  eslint, ruff, prettier
│   ↓ pass         │
│   TYPE CHECK     │  tsc --noEmit, mypy
│   ↓ pass         │
│   UNIT TESTS     │  jest, pytest
│   ↓ pass         │
│   BUILD          │  npm build, docker build
│   ↓ pass         │
│   INTEGRATION    │  API/DB tests
│   ↓ pass         │
│   SECURITY AUDIT │  npm audit, pip-audit
│   ↓ pass         │
│   BUNDLE SIZE    │  bundlesize check
└─────────────────┘
    │
    ▼
  Ready for review
```

**No gate can be skipped.** If lint fails, fix lint. If a test fails, fix the code.

## CI Configuration Patterns

### GitHub Actions — Basic CI

```yaml
name: CI
on: [pull_request]
jobs:
  quality:
    runs-on: ubuntu-latest
    steps:
    - uses: actions/checkout@v4
    - uses: actions/setup-node@v4
    - run: npm ci
    - run: npm run lint
    - run: npm run type-check
    - run: npm test
    - run: npm run build
```

### Deploy Strategy

| Strategy | Pros | Cons |
|----------|------|------|
| Blue/Green | Zero-downtime, instant rollback | Double infra cost |
| Canary | Gradual rollout, risk isolation | Complex routing |
| Rolling | No extra infra | Slow rollback |
| Feature flags | Decouple deploy from release | Flag management overhead |

## Verification Checklist

- [ ] Lint gate configured
- [ ] Type check gate configured
- [ ] Tests run in CI
- [ ] Build succeeds in CI
- [ ] Security audit runs
- [ ] Deploy is automated (no manual steps)
- [ ] Rollback procedure documented

---

**Reference:** https://github.com/addyosmani/agent-skills
