# Hermes cron → 飞书投递机制（实测摘录）

> 来源：`~/.hermes/hermes-agent/cron/scheduler.py` 与 `cron/jobs.py` 源码查实（2026-07-14）。
> 用途：任何想让 Hermes cron 定时任务把输出推到飞书的场景，先读本节，避免重蹈 webhook 假设 / deliver 标识错配的坑。

## 1. 投递平台标识 = `feishu`（不是 `hermes-feishu`）

- cron 的 `deliver` 接受字符串或列表；字符串会被拆成单元素列表（`cron.py:136-137`）。
- 合法平台集合在 `cron/scheduler.py:_KNOWN_DELIVERY_PLATFORMS`（scheduler.py:205）：
  `telegram, discord, slack, whatsapp, signal, matrix, mattermost, homeassistant, dingtalk, feishu, wecom, wecom_callback, weixin, sms, email, webhook, bluebubbles, qqbot, yuanbao`
- 飞书对应的 home target 环境变量：`FEISHU_HOME_CHANNEL`（`_HOME_TARGET_ENV_VARS`，scheduler.py:214）。
- ⚠ **`hermes-feishu` 是 toolset 名，不是 cron deliver 标识。** 填 `deliver='hermes-feishu'` 会报 `no delivery target resolved`。
- 实测对照：
  - `deliver='hermes-feishu'` → `last_delivery_error="no delivery target resolved"`
  - `deliver='feishu'` → `last_delivery_error=null`，且飞书真收到消息。

## 2. no_agent 模式：stdout 每次都被原样投递

- `cron/jobs.py` 注释（~1069）：`With no_agent=True the script IS the job — its stdout is delivered verbatim.`
- 含义：**只要脚本有 stdout 输出，cron 每次运行都会投递**——没有"无偏差就不报"的隐式静默。
- 推论（心跳模式）：想每周固定收到状态摘要，只需让脚本**总是 `print()` 人类可读内容**即可，无需任何静默/抑制逻辑。
- 本项目 `index_mode_monitor.sh` 即采用此范式：无偏差打印 `✓` 状态，超阈值打印回滚建议，cron 原样投飞书。

## 3. `[SILENT]` 可抑制投递（反向开关）

- `cron/scheduler.py:_CRON_SILENCE_TOKENS` = `{[SILENT], SILENT, NO_REPLY, NO REPLY}`。
- 当 cron 最终输出整段等于/首行/末行为这些标记时，投递被抑制（仅本地存盘）。
- 心跳任务**绝不能**输出这些标记；告警任务如需"无变化不骚扰"可用 `[SILENT]`。

## 4. 投递前提：gateway 已连 + home target 已配

- `cron_delivery_targets()` 只收录 `get_connected_platforms()` 中已连接 **且** `_is_known_delivery_platform()` 通过的平台。
- 验证通道连通：`~/.hermes/gateway_state.json` → `platforms.feishu.state == "connected"`。
- 若只连了 gateway 但没设 `FEISHU_HOME_CHANNEL`，投递目标仍解析不出（home target 未配）。

## 5. 不要假设的 webhook 死路

- 本环境 `.env` **没有** `FEISHU_WEBHOOK_URL`；飞书是 Hermes 原生 gateway（websocket 模式），不是群机器人 webhook。
- 因此**不要**写 `notify.py` 去 POST 群机器人 webhook——那是死路。改用 cron `deliver='feishu'`，框架经 gateway 送达，不碰凭证。
- 同理，lark-cli 虽有 bot 身份（`appId cli_aad883552478dcc7`），但 cron 投递走 gateway，不是 lark-cli 直发。

## 6. 本项目的落地清单（index_mode 监控）

- 监控脚本：`references/monitor_index_mode.py`（`--check` 默认人类可读；`--json` 给程序；`--dry` 仅建议不回滚；`--update-baseline` 重建基线）
- 薄壳：`scripts/index_mode_monitor.sh`（切 vdb `.venv`，跑 `monitor --check`，退出码非 0 时透传错误）
- cron：`cronjob ece8c80f7016`，`deliver='feishu'`，每周一 09:00 UTC，心跳 + 超阈值告警
- 验证命令：`hermes cron` 查 job；`gateway_state.json` 查 `platforms.feishu.state`
