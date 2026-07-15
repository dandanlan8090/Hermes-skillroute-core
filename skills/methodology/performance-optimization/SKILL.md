---
name: performance-optimization
description: >
  Performance optimization: measure then optimize — frontend (Web Vitals), backend (query tuning), and database (N+1 fixes). Use when performance SLAs exist, regressions suspected, or profiling reveals bottlenecks.
  Not for premature optimization or changes without measurement.
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
      - 性能优化
      - performance
      - 慢查询
      - 前端性能
      - Core Web Vitals
      - LCP
      - 加载速度
      - 优化
      - N+1
      - 瓶颈
      - profiling
      - 延迟
      - 吞吐量
      disable:
      - 无测量依据的优化
      - 代码已清晰且性能非关键
      - 用户未要求优化
    skill_type: methodology
    priority: normal
    related_skills:
    - debugging-patterns
    - code-review-and-audit
prerequisites:
  commands:
  - terminal
  - read_file
---
# Performance Optimization

## Overview

Measure before optimizing. Performance work without measurement is guessing — and premature optimization adds complexity without improving what matters. Profile first, identify the actual bottleneck, fix it, measure again.

## When to Use

- Performance requirements exist in the spec (load time budgets, response time SLAs)
- Users or monitoring report slow behavior
- Core Web Vitals scores are below thresholds
- You suspect a change introduced a regression

**When NOT to use:** Don't optimize before you have evidence of a problem.

## The Optimization Workflow

```
1. MEASURE  → Establish baseline with real data
2. IDENTIFY → Find the actual bottleneck (not assumed)
3. FIX      → Address the specific bottleneck
4. VERIFY   → Measure again, confirm improvement
5. GUARD    → Add monitoring or tests to prevent regression
```

### Step 1: Measure

Two approaches — use both:

- **Synthetic (Lighthouse, DevTools):** Controlled conditions, reproducible. Best for CI regression detection.
- **RUM (web-vitals, CrUX):** Real user data. Validates fix actually improved UX.

### Step 2: Identify

| Area | Common Bottlenecks | Tool |
|------|-------------------|------|
| Frontend | Large bundles, render blocking, layout shift | Lighthouse, DevTools Performance |
| Backend | Slow queries, N+1, no caching | APM, slow query log |
| Database | Missing indexes, full table scans | EXPLAIN ANALYZE |
| Network | Large payloads, no compression | Network tab, HAR |

### Step 3: Fix

Target the specific bottleneck. Common fixes:

- **Frontend:** Code splitting, lazy loading, image optimization, CDN
- **Backend:** Add indexes, query optimization, caching layer, connection pooling
- **Database:** Denormalization, materialized views, read replicas

### Step 4: Verify

Measure again with the same tool and conditions. Compare before/after. If improvement < 10%, the fix may not be worth the complexity.

### Step 5: Guard

Add to CI: Lighthouse CI, bundle size check, performance regression tests.

## Verification Checklist

- [ ] Baseline measured before optimization
- [ ] Specific bottleneck identified (not guessing)
- [ ] Fix addresses root cause, not symptom
- [ ] After-fix measurement confirms improvement
- [ ] Regression guard added (CI check or monitoring)

---

**Reference:** https://github.com/addyosmani/agent-skills
