#!/usr/bin/env bash
# index_mode vdb 检索健康看门狗 (cron no_agent 入口)
# 薄壳: 切到 vdb 独立 .venv 调用真实监控脚本, 把人类可读报告交给 cron 框架投递。
# - 无偏差时打印 ✓ 状态摘要 (每周心跳, 飞书必达)
# - 超阈值/异常时打印回滚建议 (飞书告警)
# 真实逻辑: skills/infrastructure/hermes-routing-table-index-proposal/references/monitor_index_mode.py
# 投递: cronjob deliver=hermes-feishu (经已连通的飞书 gateway)
set -euo pipefail

VDB_VENV="$HOME/.hermes/vdb/.venv/bin/python"
MON="$HOME/.hermes/skills/infrastructure/hermes-routing-table-index-proposal/references/monitor_index_mode.py"

if [[ ! -x "$VDB_VENV" ]]; then
  echo "[cron:index_mode_monitor] vdb .venv 缺失: $VDB_VENV"
  exit 1
fi

# 跑监控 (默认人类可读输出)。no_agent 模式下 stdout 由 cron 原样投递。
# 退出码非 0 = vdb 故障, 错误已进 stdout, cron 会作为告警投递。
cd "$HOME/.hermes/vdb" && "$VDB_VENV" "$MON" --check
EXIT=$?
if [[ $EXIT -ne 0 ]]; then
  echo "[cron:index_mode_monitor] monitor 退出码 $EXIT (vdb 不可用?)"
fi
exit 0
