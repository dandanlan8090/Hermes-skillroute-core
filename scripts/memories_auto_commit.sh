#!/usr/bin/env bash
# memories_auto_commit.sh — 每周自动把框架成果 commit 进本地 git（防"备份空壳"）
# 由 Hermes cronjob memories_auto_commit 每周一 08:30 调用。
# git 根目录是 ~/.hermes（.gitignore 已排除 .env/config.yaml/chroma/*.db 等敏感/运行时文件）。
set -e
cd ~/.hermes
# 无变更则静默退出（|| true 防 commit 报错中断 cron）
if git diff --quiet && git diff --cached --quiet && [ -z "$(git ls-files --others --exclude-standard)" ]; then
  exit 0
fi
git add -A
git commit -m "auto: $(date +%Y-%m-%d) — 框架文档/代码状态自动快照" >/dev/null 2>&1 || true
