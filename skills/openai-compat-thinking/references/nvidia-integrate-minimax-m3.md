# NVIDIA Integrate — MiniMax-M3 thinking evidence (2026-06-23)

Captured during a session where the user asked Hermes to "open thinking
mode and set default effort to xhigh" against the model
`minimaxai/minimax-m3` served by `https://integrate.api.nvidia.com/v1`.

The model card was fetched at
https://build.nvidia.com/minimax/minimax-m3 (a single-page hydrated
React app). The relevant JS bundle, searched for `reasoning` / `thinking`
verbs, showed:

  - A `reasoning` object with `defaultEnabled: false`
  - A `reasoning_content` field described as "Reasoning/thinking trace
    emitted by the model in responses when thinking mode is active
    (non-OpenAI extension)."
  - A `thinking_mode` enumerator with three values: `enabled`,
    `disabled`, `adaptive`.

So the official declaration is "CoT extension exists, off by default, with
three states". The question that followed was: how do you actually flip
the switch from Hermes?

## Probe matrix and responses

All probes were sent against the same prompt, the same temperature, the
same `max_tokens=2048`.

| Variant | Field sent in request body | Gateway response | Model reasoning_content length |
| ------- | -------------------------- | ---------------- | ------------------------------ |
| A       | `reasoning_effort: "xhigh"` (top-level) | 200 OK | None (zero length) |
| B       | no thinking field | 200 OK | None (zero length) |
| C       | `chat_template_kwargs.enable_thinking: true` | 200 OK | **Non-empty** (a few hundred tokens of step-by-step CoT before the final 17 × 23 = 391 conclusion) |
| D       | `enable_thinking: true` (top-level) | 400 Bad Request — `Validation: Unsupported parameter(s): \`enable_thinking\`` |
| E       | `thinking_mode: "enabled"` (top-level) | 400 Bad Request — `Validation: Unsupported parameter(s): \`thinking_mode\`` |

Reading:

  1. **Variants A and B look identical.** The gateway accepts the
     `reasoning_effort` field (because the chat completions schema is
     permissive) but does *not* route it to the model. The model emits its
     reasoning into `content` as visible plain text, with no
     `reasoning_content` channel. From the agent's perspective, the
     "thinking" appears inline; it is not extractable as a hidden trace.
  2. **Variant C is the one true path.** Nesting
     `enable_thinking` under `chat_template_kwargs` is the only placement
     NVIDIA Integrate v1 honored for this model. It returned a full CoT
     in `message.reasoning_content` and the visible answer in
     `message.content`.
  3. **Variants D and E were rejected.** Both top-level placements 400.
     No silent drop, but no fallback either. Easy to mis-paste from a
     snippet written for vLLM or Anthropic Claude and find a hard failure.

The verbatim CoT from variant C (truncated):

> The user is asking me to calculate 17 multiplied by 23. Let me think
> step by step.
>
> 17 × 23
>
> I can break this down:
> 17 × 23 = 17 × (20 + 3) = 17 × 20 + 17 × 3 = 340 + 51 = 391
>
> Let me verify: 17 × 23 = 17 × 23 = (15 + 2) × 23 = 15 × 23 + 2 × 23
> = 345 + 46 = 391
>
> Yes, 391 is correct.

So the channel works when properly activated. The whole challenge was
naming and placing the field, not coaxing the model itself.

## Hermes config landing point (the trap)

Trying the natural shape:

```yaml
model:
  base_url: https://integrate.api.nvidia.com/v1
  default: minimaxai/minimax-m3
  provider: nvidia
  extra_body:
    chat_template_kwargs:
      enable_thinking: true
```

This **does not work** in Hermes 12.x. The
`_merge_custom_provider_extra_body` function in
`agent/agent_init.py` (around line 1444) only reads
`providers.<name>.extra_body`, not `model.extra_body`. So the YAML above
writes the dict but it never reaches the wire.

The working shape is:

```yaml
providers:
  nvidia:
    provider: nvidia
    base_url: https://integrate.api.nvidia.com/v1
    api_key: $NVIDIA_API_KEY
    model: minimaxai/minimax-m3
    extra_body:
      chat_template_kwargs:
        enable_thinking: true
```

…and `model.provider: nvidia` (or whatever routing makes the run pick
the named `nvidia` provider). Then the merge function does its job.

## Trap #2 — JSON string vs YAML dict

`hermes config set model.extra_body '{"chat_template_kwargs":{"enable_thinking":true}}'`
**looks like** it succeeded but writes the value as a quoted JSON
string. The merge function checks `isinstance(extra_body, dict)` and
silently drops non-dicts. The deep dot-path
`hermes config set providers.nvidia.extra_body.chat_template_kwargs.enable_thinking true`
is what produces a real YAML dict nested under `providers.<name>.extra_body`.

Verification step (cheap, no API call):

```bash
sed -n '1,30p' ~/.hermes/config.yaml | grep -A4 extra_body
```

Successful shape:

```yaml
  extra_body:
    chat_template_kwargs:
      enable_thinking: true
```

Failed shape (stringified):

```yaml
  extra_body: '{"chat_template_kwargs":{"enable_thinking":true}}'
```

These two are visually similar in `cat` output; the regex of the
neighbors gives it away.

## Trap #3 — Display keys cannot rescue this

`agent.reasoning_effort`, `display.verbose`, `display.display_thinking`
are read by the Hermes desktop / TUI for UI presentation. They do NOT
cause NVIDIA Integrate to flip any toggle. They are session-time UX
switches, not request-body knobs. Setting them to xhigh + true *while*
`model.extra_body` is in the wrong place is the most common wasteful
loop.

## End-to-end checklist (verified June 23)

  1. Configure named provider in `providers.nvidia.extra_body.*
     chat_template_kwargs.enable_thinking: true` via `hermes config set`
     deep dot-path.
  2. Confirm YAML is a nested dict (not a JSON string) with
     `sed -n '1,30p' ~/.hermes/config.yaml`.
  3. Set `model.provider: nvidia` and confirm the named-provider merge
     function fires.
  4. Run the probe script. Variant C returns non-empty
     `reasoning_content`. If a different variant wins, treat that as the
     source of truth and update the config accordingly.
  5. Capture one real Hermes chat turn and grep `hermes_state.py`'s
     `reasoning_content` column to confirm the value lands in the
     session DB.

## Source links

  - NVIDIA model card: https://build.nvidia.com/minimax/minimax-m3
  - Hermes config merge function:
    `~/.hermes/hermes-agent/agent/agent_init.py:_merge_custom_provider_extra_body`
  - Hermes normalized provider table:
    `~/.hermes/hermes-agent/hermes_cli/config.py:_normalize_custom_provider_entry:4195`
  - Reasoning-content echo handling:
    `~/.hermes/hermes-agent/agent/agent_runtime_helpers.py:copy_reasoning_content_for_api`
