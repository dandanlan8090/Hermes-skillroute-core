# 飞书投递 / 通知通道：真实机制与常见坑（2026-07-14 实测）

本文件是 `hermes-framework` §4「cron deliver 写 hermes-feishu」那一行的支撑细节。
用户原话「飞书是通的啊」打回了"假设 `.env` 里有 `FEISHU_WEBHOOK_URL` 自建 notify 脚本"的错误路径。

## 1. 飞书在本机的真实通道

| 维度 | 事实 |
|------|------|
| 投递方式 | **Hermes 原生 gateway**（websocket，状态在 `gateway_state.json` 的 `platforms.feishu.state=connected`） |
| 不是 | 群机器人 webhook URL（`FEISHU_WEBHOOK_URL`）。本机 `.env` **无此键** |
| 平台标识（cron 用） | **`feishu`**（不是 toolset 名 `hermes-feishu`） |
| lark-cli 身份 | 另有 bot identity ready，但那是交互式 lark 操作通道，不是 cron 通知通道 |

## 2. cron `deliver` 平台标识

- cron 的 `_KNOWN_DELIVERY_PLATFORMS` 只认 gateway 里实际连接的平台标识，对本机就是 `feishu`。
- `hermes-feishu` 是 **skill/toolset 名**，cron 不认 → 写 `deliver='hermes-feishu'` 会得到
  `no delivery target resolved for deliver=hermes-feishu`。
- 正确：`deliver='feishu'`。cron.py 会把字符串拆成单元素列表 `["feishu"]`。
- 验证当前真实标识：`grep -rn "_KNOWN_DELIVERY_PLATFORMS" ~/.hermes/hermes-agent/cron/scheduler.py`

## 3. no_agent 看门狗范式的投递行为

- `cronjob` 带 `no_agent=true` 时，**脚本的 stdout 被 verbatim 当作投递内容**（见 scheduler.py 注释 "the script IS the job — its stdout is delivered verbatim"）。
- 推论：**只要脚本有 stdout，cron 就投递**。若想"每周心跳必达"，让脚本总是打印一份人类可读摘要（无偏差也打印 ✓ 状态），而非静默退出。
- `[SILENT]` 标记可抑制投递（scheduler 检测到该标记则跳过）——反向场景（不想打扰）才用。

## 4. 标准做法（不要自建 webhook 推送）

```
1. 写监控/任务脚本，总是 stdout 输出报告（无偏差也输出 ✓ 状态）
2. 用 Hermes cronjob 调度：cronjob(action='create', deliver='feishu', no_agent=true, ...)
3. 框架自动经已连通的飞书 gateway 把 stdout 投到飞书
```
自建 `notify.py` 调群机器人 webhook 在本环境是死路（无 `FEISHU_WEBHOOK_URL`），且重复造轮子、还要自己管凭证。

## 5. 验证清单（建飞书通知前必做）

- [ ] `python3 -c "import json;print(json.load(open('~/.hermes/gateway_state.json'))['platforms']['feishu']['state'])"` → 应 `connected`
- [ ] 确认 cron `deliver` 用 `'feishu'`（非 `hermes-feishu`）
- [ ] 本地跑一次 `cronjob(action='run', job_id=...)` 看 `last_delivery_error` 是否为 null
- [ ] 飞书里实际收到一条，再宣布通道通
