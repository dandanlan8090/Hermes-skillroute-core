#!/bin/bash
# SwarmVault 定期编译：保持知识图谱新鲜
# 依赖：~/.hermes/.env 中的 SILICONFLOW_API_KEY / AGNES_API_KEY
# 注意：cron 独立 shell 不继承交互环境，必须显式 source .env

set -euo pipefail

cd "$HOME"

# 加载 Hermes 凭据环境（swarmvault 的 apiKeyEnv 从这里取 key）
if [ -f "$HOME/.hermes/.env" ]; then
  set -a
  source "$HOME/.hermes/.env"
  set +a
fi

LOG_DIR="$HOME/knowledge/logs"
mkdir -p "$LOG_DIR"
LOG="$LOG_DIR/compile.log"

EXIT_CODE=0

echo "[$(date -u +%Y-%m-%dT%H:%M:%SZ)] compile start" >> "$LOG"
swarmvault compile --commit >> "$LOG" 2>&1 || EXIT_CODE=$?
echo "[$(date -u +%Y-%m-%dT%H:%M:%SZ)] compile done (exit $EXIT_CODE)" >> "$LOG"

if [ $EXIT_CODE -ne 0 ]; then
  echo "[$(date -u +%Y-%m-%dT%H:%M:%SZ)] ERROR: swarmvault compile failed with exit code $EXIT_CODE" >> "$LOG"
  # 保留最近 30 行输出供排查
  tail -30 "$LOG" | head -5 >&2
fi

exit $EXIT_CODE
