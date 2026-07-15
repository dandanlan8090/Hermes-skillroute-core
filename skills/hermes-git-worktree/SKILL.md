---
name: hermes-git-worktree
description: >
  Git 工作流：worktree 隔离、commit 规范、语义版本、changelog。Use when creating features on isolated branches, writing commits, planning releases, or handling parallel work.
  Not for single-file hotfixes or docs-only changes.
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
      - worktree
      - git worktree
      - 分支隔离
      - 并行开发
      - 新建分支
      - feature branch
      - 隔离开发
      - 多分支
      - git branch
      - commit message
      - git commit
      - 提交规范
      - 版本号
      - semver
      - 语义版本
      - changelog
      - release
      - tag
      disable:
      - 单文件改动
      - hotfix直接提交
      - 文档修改
      - 无需版本控制的单次修改
    skill_type: workflow
    priority: normal
prerequisites:
  commands:
  - terminal
---
# Git Workflow & Worktree Isolation

## Overview

Disciplined version control keeps changes manageable, reviewable, and reversible. This skill covers the full lifecycle: commit hygiene, branch isolation via worktrees, semantic versioning, and changelog management.

---

## Part 1: Commit Discipline

### 1. Commit Early, Commit Often

Each successful increment gets its own commit. Don't accumulate large uncommitted changes.

```
Good:  Implement slice → Test → Verify → Commit → Next slice
Bad:   Implement everything → Hope it works → Giant commit
```

### 2. Atomic Commits

Each commit does one logical thing:

```
Good: Each commit is self-contained
  a1b2c3d Add task creation endpoint with validation
  d4e5f6g Add task creation form component
  h7i8j9k Connect form to API and add loading state

Bad: Everything mixed together
  x1y2z3a Add task feature, fix sidebar, update deps, refactor utils
```

### 3. Descriptive Messages

Commit messages explain the *why*, not just the *what*:

```
Good:
feat: add email validation to registration endpoint

Prevents invalid email formats from reaching the database.
Uses Zod schema validation at the route handler level.

Bad:
update auth.ts
```

**Format:**

```
<type>: <short description>

<optional body explaining why, not what>
```

**Types:** `feat`, `fix`, `refactor`, `test`, `docs`, `chore`

### 4. Keep Concerns Separate

Don't combine formatting changes with behavior changes. Separate refactoring from feature work — they should be in separate commits, ideally separate PRs.

### 5. Size Your Changes

Target ~100 lines per commit/PR. Changes over ~1000 lines must be split.

---

## Part 2: Branching Strategy

### Branch Naming

```
feature/<short-description>   → feature/ta<api-key>
fix/<short-description>        → fix/duplicate-tasks
chore/<short-description>      → chore/update-deps
refactor/<short-description>   → refactor/auth-module
```

### Trunk-Based Development (Recommended)

Keep `main` always deployable. Short-lived feature branches (1-3 days max). Long-lived branches are hidden costs — they diverge, create merge conflicts, and delay integration.

- Feature flags > long branches
- Release branches OK when stabilizing while main moves forward
- Delete branches after merge

---

## Part 3: Worktree Isolation

For parallel work, use `git worktree` to run multiple branches simultaneously.

### Path Priority

1. User-specified path in current message
2. `.worktrees/` or `worktrees/` if exists
3. Default: `.worktrees/`

### Pre-Check

```bash
# Verify not already inside a worktree
[ "$GIT_DIR" != "$GIT_COMMON_DIR" ] && echo "Already in worktree, reuse"
```

### Create

```bash
git worktree add ../project-feature-a feature/ta<api-key>
```

### Baseline Testing

Every worktree must pass tests before code changes:

| Project Type | Command |
|-------------|---------|
| Python | pytest |
| Node | npm test |
| Go | go test |
| Rust | cargo test |

### Cleanup

Merge complete or abandoned → clean up worktree automatically.

---

## Part 4: Semantic Versioning (SemVer)

Given a version number MAJOR.MINOR.PATCH:

| Increment | When |
|-----------|------|
| MAJOR | Incompatible API changes |
| MINOR | New functionality, backward-compatible |
| PATCH | Bug fixes, backward-compatible |

Pre-release: `1.0.0-alpha`, `1.0.0-beta.1`

**Zero major (0.x) = initial development.** API may change at any time.

## Part 5: Changelog

Maintain a `CHANGELOG.md` following [Keep a Changelog](https://keepachangelog.com/):

```markdown
# Changelog

## [1.1.0] - 2026-07-10

### Added
- New feature description (#PR)

### Fixed
- Bug fix description (#issue)

### Changed
- Behavior change description
```

---

## Verification Checklist

- [ ] Commit message follows `<type>: <desc>` format
- [ ] Single concern per commit
- [ ] Worktree tests pass before changes
- [ ] Version bumped correctly (if releasing)
- [ ] Changelog updated (if releasing)
- [ ] Branch naming follows convention
- [ ] Worktree cleaned up after merge

---

**Reference:** https://github.com/addyosmani/agent-skills
