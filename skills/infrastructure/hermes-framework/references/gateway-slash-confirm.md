# Gateway slash-confirm 数据流与平台适配缺口（verified against hermes-agent v0.18.2）

本文件是 `hermes-framework` §4 的支撑细节：Hermes 网关的「破坏性 slash 命令确认」
（`/new`、`/reset`、`/undo`、`/reload-mcp` 等）如何在各平台渲染三按钮确认，
以及飞书（Feishu）渠道当前为何降级为纯文本 fallback。

## 1. 数据流（一次 `/new` 确认的完整链路）

```
用户发 /new
  └─ gateway/run.py  _maybe_confirm_destructive_slash()   [run.py:14068]
       ├─ 读 config approvals.destructive_slash_confirm（默认 True，需确认）
       └─ 调 _request_slash_confirm()                      [run.py:14156]
            ├─ tools/slash_confirm.register(session_key, confirm_id, command, handler)  [slash_confirm.py:51]
            ├─ 调 adapter.send_slash_confirm(chat_id, title, message, session_key, confirm_id, metadata)  [run.py:14202]
            │     ├─ 成功且 result.success → used_buttons=True → 返回 None（按钮自解释，不发冗余文本）
            │     └─ 失败/未实现 → 降级：直接把 prompt_message 当作文本回复发出   [run.py:14221-14222]
            └─ 文本 fallback 文案含 "reply /approve, /always, /cancel"
```

按钮点击的回解路径（以 Telegram 为参照实现）：
```
平台按钮点击 → adapter 回调处理器
  ├─ Telegram: _handle_callback_query()   [telegram/adapter.py:5291]
  │     └─ data.startswith("sc:") 分支     [telegram/adapter.py:5397]
  │           ├─ _slash_confirm_state.pop(confirm_id) → session_key
  │           └─ tools.slash_confirm.resolve(session_key, confirm_id, choice)  [slash_confirm.py:99]
  │                 └─ 执行 handler(choice) → 返回的字符串作为 follow-up 消息发回原 chat
  └─ 飞书: 见 §3（缺实现）
```

`tools/slash_confirm.resolve()` 签名：
`resolve(session_key, confirm_id, choice, timeout=300) -> Optional[str]`
- `choice` ∈ {"once","always","cancel"}
- 先 pop pending 防重复点击，超时（默认 300s）返回 None
- 执行 handler，返回其字符串结果（发回用户）

## 2. Adapter 契约（来自 gateway/platforms/ADDING_A_PLATFORM.md:121）

每个支持内联按钮的平台**应当** override `send_slash_confirm`，渲染三按钮：
Approve Once / Always Approve / Cancel，按钮回调必须路由回
`tools.slash_confirm.resolve(session_key, confirm_id, choice)`。

`gateway/platforms/base.py:3086` 默认实现返回 `SendResult(success=False, error="Not supported")`，
→ gateway 收到 success=False → 自动降级文本 fallback。

已实现该方法的平台（run.py:14063 注释与源码核对）：
- Telegram：`plugins/platforms/telegram/adapter.py:4614` + 回调 `sc:` 分支 :5397
- Discord / Slack / Matrix：已实现（见各自 adapter）
- **飞书 Feishu：未实现 send_slash_confirm** ← 根因

## 3. 飞书缺口（已确认，v0.18.2）

飞书 adapter (`plugins/platforms/feishu/adapter.py`) 具备完整卡片按钮能力，
但**独缺 `send_slash_confirm`**：
- 有的卡片方法：`send_exec_approval()` :1980、`send_update_prompt()` :2082
- 卡片按钮闭环：`_on_card_action_trigger()` :2634 → `_handle_card_action_event()` :2965
  （把按钮 value 序列化为 `/card button {...}` synthetic command）
- approval 分支：`_handle_approval_card_action()` :2700（用 `_approval_state` 字典 + `_approval_counter`）
- update_prompt 分支：`_handle_update_prompt_card_action()` :2756
- 权限校验：`_is_interactive_operator_authorized()` :2690（admin/allowed 用户，空则所有人）

**后果**：`_request_slash_confirm` 调飞书 adapter.send_slash_confirm 命中 base 默认
→ `success=False` → 降级文本 fallback（即用户看到的 "reply /approve, /always, /cancel"）。
run.py:14084 注释写 "Telegram/Discord/Slack, text fallback elsewhere"，飞书被归到 elsewhere。

## 4. 对称修复模式（mirror Telegram，最小侵入）

飞书加 `send_slash_confirm()` + 一个卡片回调分支即可闭环：

1. adapter `__init__` 加 `self._slash_confirm_state: Dict[str, str] = {}`
2. 新方法 `send_slash_confirm(self, chat_id, title, message, session_key, confirm_id, metadata=None)`：
   - 复用 `send_exec_approval` 的卡片结构（`_feishu_send_with_retry(chat_id, msg_type="interactive", payload=..., ...)` at :4770）
   - 三按钮 value 带 `{"hermes_slash_confirm_id": confirm_id, "hermes_slash_confirm_choice": "once"/"always"/"cancel"}`
   - 发送成功后 `self._slash_confirm_state[confirm_id] = session_key`
   - 返回 `SendResult(success=True, message_id=...)`
3. `_on_card_action_trigger()`（:2634）加分支：识别 `hermes_slash_confirm_id` →
   走新 `_handle_slash_confirm_card_action()`：
   - 取 confirm_id/choice，pop `_slash_confirm_state`
   - 调 `tools.slash_confirm.resolve(session_key, confirm_id, choice)`
   - 若返回字符串，用 `_feishu_send_with_retry` 发回原 chat（飞书卡片无 edit-按钮语义，发 follow-up 即可）
   - 可选：回 CallBackCard 把按钮卡片换成"已确认"状态（参照 `_build_resolved_approval_card` :2118）

**注意**：此改动落在 hermes-agent 核心代码（`~/.hermes/hermes-agent`，editable 安装，改完无需重装）。
真机卡片效果需连真实飞书网关跑一次 `/new` 才能 100% 确认（无飞书 app 凭证无法自动验证）。

## 5. 关键文件/行号速查（v0.18.2）

| 位置 | 作用 |
|------|------|
| `gateway/run.py:14068` | `_maybe_confirm_destructive_slash` 门控入口 |
| `gateway/run.py:14156` | `_request_slash_confirm` 发卡片+register，失败降级文本 |
| `gateway/run.py:14202` | 调 `adapter.send_slash_confirm` |
| `gateway/platforms/base.py:3086` | 默认 `send_slash_confirm` 返回 success=False（降级源） |
| `tools/slash_confirm.py:51` | `register` |
| `tools/slash_confirm.py:99` | `resolve`（handler 执行 + 结果返回） |
| `plugins/platforms/telegram/adapter.py:4614` | Telegram `send_slash_confirm`（参照实现） |
| `plugins/platforms/telegram/adapter.py:5397` | Telegram `sc:` 回调分支 |
| `plugins/platforms/feishu/adapter.py:1980` | 飞书 `send_exec_approval`（卡片按钮结构参照） |
| `plugins/platforms/feishu/adapter.py:2634` | `_on_card_action_trigger`（加分支处） |
| `plugins/platforms/feishu/adapter.py:2690` | `_is_interactive_operator_authorized` |
| `gateway/platforms/ADDING_A_PLATFORM.md:121` | adapter 契约说明 |
