# Repo 对 Hermes 配置的依赖关系

## 设计原则

repo **不要求用户修改 config 任何设置**。开箱即用 = 默认的 Hermes config.yaml 能跑。
以下依赖是"功能完整度"层面的，不是"能不能装"层面的。

## 功能依赖链

### 1. `agent.tool_use_enforcement`（默认 `auto`）

- `auto`（默认）→ 只在 GPT/Codex 模型注入工具调用提示
- `always` → 所有模型都注入
- 影响：AGENTS.md §0.5 写"禁用 available_skills 手动匹配。始终用 `from matcher import search`"
  在 `auto` 下，Claude / Gemini / 本地模型可能忽略这条指令，fallback 到内置 skill 列表
- **repo 行为**：install.sh + AGENTS.md 正常工作，vdb 工具链就绪，但 agent 是否实际走 vdb 路径取决于模型
- **建议**：新用户先跑默认配置，如果发现 agent 不用 vdb 再切 `always`

### 2. `command_allowlist`（默认空）

Hermes 安全框架默认拦截：
- `cp` 写入 homedir 配置文件
- heredoc 脚本执行
- `sudo with privilege flag`
- `overwrite project env/config file`
- `copy/move file into system config path`

install.sh 和 init-vdb.sh 用到以上所有操作。**无 allowlist 则安装脚本弹窗确认后仍可执行**（用户手动批准），
但非交互式终端（TUI / 远程）会直接失败。

- **repo 行为**：install.sh 提示用户手动批准弹窗；非交互场景需预先配置 allowlist
- **建议**：新装机在 CLI 交互式运行 install.sh，弹窗口按 y 放行即可

### 3. `auxiliary.skills_hub.provider`（默认 `auto`）

repo vdb 的 embedding API 走 SiliconFlow（写在 `vdb/embed.py` 常量和 `.env` 中），
不使用 Hermes 的 `auxiliary.skills_hub` 配置。两者独立互不干扰。

如果用户想用 vdb 之外的 Hermes 原生 skill hub 功能，这个配置才有影响。

## 无关的常见差异

以下用户在会话中设了非默认值，但对 repo 功能**完全无影响**：

| 配置项 | 当前值 | 默认值 | 原因 |
|--------|--------|--------|------|
| `agent.verbose: true` | true | 无（false） | 仅输出量 |
| `agent.yolo: true` | true | 无（false） | 危险操作许可 |
| `agent.max_turns: 150` | 150 | 90 | 轮次上限 |
| `agent.gateway_timeout: 3600` | 3600 | 1800 | 超时偏好 |
| `agent.clarify_timeout: 300` | 300 | 3600 | 等待偏好 |
| `agent.environment_probe: false` | false | true | 探测开关 |
| `agent.verify_on_stop: false` | false | auto | 验证开关 |
| `memory.provider: holographic` | holographic | memory | 记忆引擎 |
| `browser.allow_private_urls: true` | true | false | 安全偏好 |
| `delegation.max_spawn_depth: 2` | 2 | 1 | 子 agent 深度 |
| `display.language: zh-CN` | zh-CN | en | 语言偏好 |

## 红线：repo 不管理 config

- install.sh 不写入 config.yaml
- 不要求用户改任何设置
- 不依赖任何非默认配置项的"必须存在"
- 用户通过 `hermes setup` 或手动编辑 config.yaml 完成个性化配置
