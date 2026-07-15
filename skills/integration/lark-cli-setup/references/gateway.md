# lark-cli (Layer A) vs Hermes Feishu gateway adapter (Layer B)

Two independent Feishu integrations. Do not confuse them.

## Layer A — lark-cli (this skill)
- **Direction:** Hermes → act on Feishu (active, outbound)
- **Mechanism:** local binary at `~/.local/bin/lark-cli`; credentials in
  `~/.lark-cli/hermes/config.json` (written by `config bind --source hermes`)
- **Identity:** OAuth user_access_token, `defaultAs: user` (user-default)
- **Entry-agnostic:** runs inside ANY session — CLI chat OR a gateway session.
  The gateway process inherits `HERMES_HOME=~/.hermes`, so it reads the
  same config and the same logged-in user. A Feishu-borne message that the
  agent routes to lark-cli behaves identically to a CLI session doing so.
- **Routing:** driven by the 27 `lark-*` skills (available_skills scan +
  keywords), NOT by the native gateway adapter.

## Layer B — Hermes `feishu` gateway platform adapter
- **Direction:** Feishu → drive Hermes (passive entry point)
- **Mechanism:** `plugins/platforms/feishu/`; the bot receives DMs / replies
  in Feishu, which become Hermes conversation turns. Also exposes native
  `feishu_doc` / `feishu_drive` tools (when registered in the build).
- **Complement, not substitute, for Layer A.**
- **NOT required** for lark-cli to work.

## How to tell what's wired
```bash
# Gateway running? Which platforms connected?
cat ~/.hermes/channel_directory.json     # {"platforms":{}} => Feishu NOT connected
cat ~/.hermes/gateway_state.json         # gateway_state / platforms keys
ps -o pid,args -p $(pgrep -f 'gateway run')   # expect HERMES_HOME=~/.hermes

# Native feishu toolsets registered in this build?
hermes tools enable feishu_doc           # "Unknown toolset" => not registered
hermes tools list | grep -i feishu      # (usually none — rely on lark-cli)
```

## Gotchas
- `channel_directory.json` with empty `platforms:{}` means Feishu is NOT yet a
  conversation entry — only the lark-cli active path is live. To enable Feishu
  DMs you must configure the gateway `feishu` adapter (event subscription /
  bot callback URL), a separate task from this skill.
- The native `feishu_doc` / `feishu_drive` toolsets are documented in
  `hermes-agent` but may be unregistered in your installed build (verified:
  `Unknown toolset 'feishu_doc'`). Treat lark-cli as the working Feishu path.
- Both layers can share the SAME Feishu app (`cli_aad883552478dcc7`) — decide
  per use case whether the gateway adapter should reuse it or use a dedicated
  app; out of scope here.
