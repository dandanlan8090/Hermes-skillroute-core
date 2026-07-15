---
name: github
description: 'GitHub end-to-end: auth, issues, PR lifecycle, repo management, code
  review, source-level audits, and LOC analysis — all gh + curl fallbacks.'
version: 1.0.0
author: Hermes Agent (umbrella consolidation)
license: MIT
platforms:
- linux
- macos
- windows
metadata:
  hermes:
    tags:
      trigger:
      - github
      - git
      - 代码仓库
      - pr
      - issue
      - GitHub操作
      - PR操作
      - 代码仓库管理

      disable:
      - network_request
      - read_only
    related_skills:
    - lm-evaluation-harness
    - research-paper-writing
---
# GitHub — End-to-End Workflows

This umbrella consolidates the full GitHub skill surface under one entry point.
Load the relevant subsection for your task; each section shows the `gh` way
first, then the `git` + `curl` fallback for machines without `gh`.

## Subsection Map

| What you need to do | Go to |
|---|---|
| Set up authentication | [Authentication Setup](#1-authentication-setup) |
| Create, triage, label, assign issues | [Issue Management](#2-issue-management) |
| Branch → commit → push → create PR | [PR Lifecycle](#3-pr-lifecycle) |
| Monitor CI, fix failures, merge | [CI & Merge](#4-ci--merge) |
| Review an open PR (inline comments, approve) | [PR Code Review](#5-pr-code-review) |
| Clone, create, fork repos; manage settings | [Repo Management](#6-repo-management) |
| Source-level audits for config / defaults / deprecations | [Source-Level Repo Audit](#7-source-level-repo-audit) |
| LOC, language breakdown, code-vs-comment ratios | [Codebase Inspection](#8-codebase-inspection) |
| Releases, secrets, GitHub Actions | [Releases & Actions](#9-releases--actions) · [发布二进制系统适配性核验](references/release-binary-compat-verify.md) |
| Pre-push diff scan, baseline tests, receive feedback | [Pre-Commit & Receiving Review](#10-pre-commit--receiving-review) |
| Diff clean-up with a 3-agent parallel lens | [Simplify & Clean Up](#11-simplify--clean-up) |

## 1. Authentication Setup

See the absorbed `github-auth` skill for full details on HTTPS tokens, SSH keys,
`gh` CLI login, and credential-helper configuration.

Quick detection (paste into any shell at the start of a GitHub workflow):

```bash
AUTH="*** if command -v gh &>/dev/null && gh auth status &>/dev/null; then
  AUTH="*** 
  if [ -z "$GITHUB_TOKEN" ] && [ -f "${HERMES_HOME:-$HOME/.hermes}/.env" ] && grep -q "^GITHUB_TOKEN=*** "${HERMES_HOME:-$HOME/.hermes}/.env"; then
    GITHUB_TOKEN=$(grep "^GITHUB_TOKEN=*** "${HERMES_HOME:-$HOME/.hermes}/.env" | head -1 | cut -d= -f2 | tr -d '\n\r')
  elif grep -q "github.com" ~/.git-credentials 2>/dev/null; then
    GITHUB_TOKEN=$(grep "github.com" ~/.git-credentials 2>/dev/null | head -1 | sed 's|https://[^:]*:\([^@]*\)@.*|\1|')
  fi
fi
echo "Using: $AUTH"
```

Extracting owner/repo (needed for every `curl` call):

```bash
REMOTE_URL=$(git remote get-url origin)
OWNER_REPO=$(echo "$REMOTE_URL" | sed -E 's|.*github\.com[:/]||; s|\.git$||')
OWNER=$(echo "$OWNER_REPO" | cut -d/ -f1)
REPO=$(echo "$OWNER_REPO" | cut -d/ -f2)
```

## 2. Issue Management

See the absorbed `github-issues` skill for issue creation, triage, labeling,
assignment, bulk operations, and issue-to-PR linking.

Quick watch patterns:

```bash
# List open bugs
gh issue list --state open --label "bug"

# Create a new issue
gh issue create \
  --title "Login redirect ignores ?next=" \
  --body "## Description\n...Steps to Reproduce..." \
  --label "bug,backend" \
  --assignee "username"

# Search across the repo
gh issue list --search "authentication error" --state all
```

Bulk-close pattern (curl):

```bash
for num in $(curl -s -H "Authorization: token *** \
  "https://api.github.com/repos/$OWNER/$REPO/issues?labels=wontfix&state=open" \
  | python3 -c "import sys,json; [print(i['number']) for i in json.load(sys.stdin)]"); do
  curl -s -X PATCH -H "Authorization: token *** \
    "https://api.github.com/repos/$OWNER/$REPO/issues/$num" \
    -d '{"state": "closed", "state_reason": "not_planned"}'
done
```

## 3. PR Lifecycle

See the absorbed `github-pr-workflow` skill for branch naming, conventional
commits, pushing, and PR creation.

Quick branch + commit + PR:

```bash
git checkout -b feat/add-user-auth
# (edit files with write_file / patch)
git add src/auth.py tests/test_auth.py
git commit -m "feat: add JWT-based user authentication

- Add login/register endpoints
- Add User model with password hashing
- Add auth middleware"
git push -u origin HEAD

gh pr create \
  --title "feat: add JWT-based user authentication" \
  --body "$(cat <<'EOF'
## Summary
- Adds login and register API endpoints
- JWT token generation and validation

## Test Plan
- [ ] Unit tests pass

Closes #42
EOF
)"
```

## 4. CI & Merge

See the absorbed `github-pr-workflow` references for CI troubleshooting patterns.

Monitor CI:

```bash
gh pr checks                    # one-shot
gh pr checks --watch            # poll every 10s

# curl fallback
SHA=$(git rev-parse HEAD)
curl -s -H "Authorization: token *** \
  "https://api.github.com/repos/$OWNER/$REPO/commits/$SHA/status" \
  | python3 -c "import sys,json; print(json.load(sys.stdin)['state'])"
```

Auto-fix loop pattern:
1. Check CI → identify failures
2. Read failure logs (`gh run view <RUN_ID> --log-failed`)
3. Fix with `read_file` + `patch`, then `git add . && git commit -m "fix: ..." && git push`
4. Wait for CI → re-check
5. Repeat (max 3 attempts)

Merge:

```bash
# Squash + delete branch (cleanest)
gh pr merge --squash --delete-branch

# curl fallback
curl -s -X PUT -H "Authorization: token *** \
  "https://api.github.com/repos/$OWNER/$REPO/pulls/$PR_NUMBER/merge" \
  -d '{"merge_method": "squash", "commit_title": "feat: ... (#$PR_NUMBER)"}'
```

## 5. PR Code Review

See the absorbed `github-code-review` skill for pre-push review, PR checkout,
inline comments, formal review submission (APPROVE / REQUEST_CHANGES / COMMENT),
and the 6-category review checklist.

Local pre-push review (no API):

```bash
git diff main...HEAD --stat
git diff main...HEAD | grep -in "password\|secret\|api_key\|eval(\\|TODO"
```

PR review workflow (gh):

```bash
gh pr checkout 123
gh pr diff 123
# (review locally)
gh pr review 123 --request-changes --body "See inline comments."
```

Atomic review with inline comments (curl):

```bash
HEAD_SHA=$(curl -s -H "Authorization: token *** \
  "https://api.github.com/repos/$OWNER/$REPO/pulls/$PR_NUMBER" \
  | python3 -c "import sys,json; print(json.load(sys.stdin)['head']['sha'])")

curl -s -X POST -H "Authorization: token *** \
  "https://api.github.com/repos/$OWNER/$REPO/pulls/$PR_NUMBER/reviews" \
  -d '{
    "commit_id": "'"$HEAD_SHA"'",
    "event": "REQUEST_CHANGES",
    "body": "## Review\nFound 2 issues, 1 suggestion.",
    "comments": [
      {"path": "src/auth.py", "line": 45, "body": "SQL injection: use parameterized queries."},
      {"path": "src/models/user.py", "line": 23, "body": "Hash passwords with bcrypt."}
    ]
  }'
```

Output template reference (`references/review-output-template.md`) provides
the structured summary format (Critical / Warnings / Suggestions / Looks Good).

## 6. Repo Management

See the absorbed `github-repo-management` skill for clone, create, fork,
settings, branch protection, secrets, releases, and GitHub Actions.

Quick reference:

```bash
# Clone
gh repo clone owner/repo-name

# Create repo
gh repo create my-project --public --clone

# Fork + upstream
gh repo fork owner/repo-name --clone
git remote add upstream https://github.com/owner/repo-name.git

# Releases
gh release create v1.0.0 --generate-notes

# Branch protection
gh api repos/:owner/:repo/branches/main/protection \
  --method PUT \
  -f required_status_checks='{"strict":true,"contexts":["CI"]}' \
  -f enforce_admins=false \
  -f required_pull_request_reviews='{"required_approving_review_count":1}' \
  -f restrictions='