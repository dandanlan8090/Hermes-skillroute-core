#!/bin/bash
# check-delegation-health.sh — Hermes delegation 健康检查脚本
# 
# 用途：检测并报告卡住的子 Agent 会话 (无心跳超过阈值)
# 来源：2026-06-27 deleg_090439bc 故障排查经验
# 作者：Hermes
#
# 使用: ~/scripts/check-delegation-health.sh

set -e

DB_PATH="$HOME/.hermes/state.db"
LOG_PATH="$HOME/.hermes/logs/agent.log"

# 阈值配置 (秒)
WARN_THRESHOLD=${WARN_THRESHOLD:-300}    # 5 分钟无心跳 → 警告
CRIT_THRESHOLD=${CRIT_THRESHOLD:-1800}   # 30 分钟无结束 → 临界

echo "=== Hermes Delegation Health Check ==="
echo "Database: $DB_PATH"
echo "Thresholds: WARN=${WARN_THRESHOLD}s (${WARN_THRESHOLD}m), CRIT=${CRIT_THRESHOLD}s (${CRIT_THRESHOLD}m)"
echo ""

# 检查数据库是否存在
if [ ! -f "$DB_PATH" ]; then
    echo "❌ 数据库文件不存在：$DB_PATH"
    exit 1
fi

# 查询未正常结束的会话 (按持续时间降序)
echo "📊 运行中的会话 (按持续时间排序):"
echo ""

sqlite3 -header -column "$DB_PATH" "
SELECT 
  id as SessionID,
  strftime('%Y-%m-%d %H:%M:%S', started_at, 'unixepoch', 'localtime') as StartedAt,
  CAST(strftime('%s','now') - started_at AS INTEGER) as Duration_s,
  CASE 
    WHEN (strftime('%s','now') - started_at) > $CRIT_THRESHOLD THEN '🔴 CRIT'
    WHEN (strftime('%s','now') - started_at) > $WARN_THRESHOLD THEN '🟡 WARN'
    ELSE '🟢 OK'
  END as Status
FROM sessions 
WHERE ended_at IS NULL
ORDER BY Duration_s DESC
LIMIT 10;
"

echo ""

# 统计临界状态
crit_count=$(sqlite3 "$DB_PATH" "
  SELECT COUNT(*) FROM sessions 
  WHERE ended_at IS NULL AND (strftime('%s','now') - started_at) > $CRIT_THRESHOLD;
")

warn_count=$(sqlite3 "$DB_PATH" "
  SELECT COUNT(*) FROM sessions 
  WHERE ended_at IS NULL AND (strftime('%s','now') - started_at) > $WARN_THRESHOLD 
    AND (strftime('%s','now') - started_at) <= $CRIT_THRESHOLD;
")

running_count=$(sqlite3 "$DB_PATH" "
  SELECT COUNT(*) FROM sessions WHERE ended_at IS NULL;
")

echo "=== Summary ==="
echo "运行中：$running_count"
echo "警告 (> ${WARN_THRESHOLD}s): $warn_count"
echo "临界 (> ${CRIT_THRESHOLD}s): $crit_count"
echo ""

# 如果有临界会话，输出清理建议
if [ "$crit_count" -gt 0 ]; then
    echo "⚠️  发现 $crit_count 个临界会话 (超过 ${CRIT_THRESHOLD}s 未结束)"
    echo ""
    echo "建议操作:"
    echo ""
    echo "1. 查看最近日志确认是否卡住:"
    echo "   tail -200 $LOG_PATH | grep -E '(stale|timeout|deleg_|20260627)'"
    echo ""
    echo "2. 手动结束卡住的会话 (替换 <session_id>):"
    echo "   sqlite3 $DB_PATH \"UPDATE sessions SET ended_at=strftime('%s','now'), end_reason='manual_kill' WHERE id='<session_id>';\""
    echo ""
    echo "3. 强制重启 Hermes (如多个会话卡住):"
    echo "   pkill -f hermes-agent && sleep 2 && hermes"
    echo ""
    exit 1
fi

if [ "$warn_count" -gt 0 ]; then
    echo "⚠️  发现 $warn_count 个警告会话 (超过 ${WARN_THRESHOLD}s 未结束)"
    echo "   建议持续监控，如继续增长需手动干预"
    echo ""
    exit 0
fi

echo "✅ 所有 delegation 会话健康"
exit 0