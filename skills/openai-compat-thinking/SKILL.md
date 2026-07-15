---
name: openai-compat-thinking
description: 'Enable reasoning/thinking/CoT on OpenAI-compatible chat completion gateways
  (NVIDIA Integrate, vLLM OpenAI compat, Groq, Together, OpenRouter) through Hermes.
  Each provider routes the thinking switch differently — never assume OpenAI''s `reasoning_effort`
  works; locate the actual field on the provider''s model card, and inject it through
  the only config path Hermes 12.x honors: `providers.<name>.extra_body`. Trigger
  when a user says ''开思考模式'' / ''enable thinking'' / ''把 reasoning_effort 调高'' / ''让
  NVIDIA MiniMax-M3 出 reasoning_content'' / ''thinking mode 不生效'' / ''verbose 不显示''
  / ''OpenAI 字段静默丢'', or when configuring a non-OpenAI reasoning model behind an OpenAI-compatible
  endpoint.'
version: 1.0.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags:
      trigger:
      - 推理
      - 思考
      - cot
      - reasoning
      - 思维链
      - o1推理
      - CoT思考
      - chain-of-thought
      disable:
      - cli_only
      - read_only
    related_skills:
    - hermes-agent
    - ai-conv-style-discipline
platforms:
- linux
- macos
---
-

# OpenAI-compat thinking — Hermes-side routing

OpenAI-compatible endpoints (NVIDIA Integrate, vLLM, Groq, Together, OpenRouter
and the like) speak the `/v1/chat/completions` schema but each one **routes the
reasoning/thinking toggle through a different field name and a different layer**
in the request body. Hermes 12.x exposes exactly one config knob for these
fields: `providers.<name>.extra_body` — and it is silently ignored if placed
under `model.extra_body`. This skill is the playbook for getting thinking
*actually turned on* through Hermes without burning an afternoon on silent
drops.

## When to use

  - A user says "开思考模式" / "enable thinking" / "reasoning_effort 调高" /
    "verbose 显示推理过程" against a non-OpenAI endpoint.
  - An assistant turned on `agent.reasoning_effort: xhigh` and the user
    reports "根本没起作用" / "看不到 CoT" / "API 回包没有 reasoning_content".
  - A new reasoning model (NVIDIA MiniMax-M*、DeepSeek R1、Qwen3-Thinking、
    Kimi K2 Thinking etc.) needs to be wired into Hermes behind a custom
    provider.
  - Someone changed `model.extra_body.*` and wonders why nothing changed.

Skip when:

  - The endpoint is the real OpenAI Responses API (`/v1/responses`) — that
    path takes `reasoning_effort` natively and this skill does not apply.
  - The reasoning model is already running and `reasoning_content` is
    visible — no config surgery needed.

## Iron law

For reasoning/thinking to **actually fire end-to-end**, all four must hold:

  1. The provider accepts the thinking field at all (top-level vs
     `chat_template_kwargs` vs `extra_body` — they differ).
  2. Hermes sends it in the request body. Hermes 12.x does this **only** via
     `providers.<name>.extra_body` (the named-provider table). Configuration
     under `model.extra_body`, `agent.extra_body`, or `display.*` does not
     reach the request.
  3. The model card's default for thinking actually turns it on. Most
     reasoning models default to **off** with `defaultEnabled: false` — set
     explicitly.
  4. Some non-required toggles (Hugging Face TGI, llama.cpp) take effect
     server-side, not via request knobs. Those need a server reload, not
     Hermes config.

If you skip any of these and report "thinking is on", you have not verified
the chain — go run a probe (see `scripts/probe_thinking_fields.py`).

## Per-provider field map (verified, not guessed)

The same idea ("turn on reasoning") maps to **different request keys** per
provider. Treat any deviation in a fresh provider's docs as the source of
truth — this table is the snapshot of confirmations across real probes.

| Provider / model              | Switch field                                                                | Where in body                | Returns reasoning trace at            |
| ----------------------------- | --------------------------------------------------------------------------- | ---------------------------- | ------------------------------------- |
| NVIDIA Integrate MiniMax-M3   | `chat_template_kwargs.enable_thinking` (`true`/`false`)                     | inside `extra_body`         | `message.reasoning_content`           |
| vLLM Qwen3-thinking           | `chat_template_kwargs.enable_thinking`                                      | inside `extra_body`         | `message.reasoning_content`           |
| DeepSeek-R1 (NIM/vLLM)        | `thinking` (`{"type":"enabled"}`) — NOT `enable_thinking`                   | inside `extra_body`         | `message.reasoning_content`           |
| Moonshot Kimi K2              | top-level `reasoning_effort`                                                 | top level                   | `message.reasoning_content`           |
| OpenRouter                    | `reasoning.effort` (per-model enumerated)                                    | inside `extra_body`         | `message.reasoning` or summary fields |
| OpenAI Responses API          | top-level `reasoning_effort` (`low`/`medium`/`high`/`xhigh`)                | top level                   | `output[*].summary` (when verbose)    |
| xAI Grok (reasoning variant)  | top-level `reasoning_effort`                                                 | top level                   | `message.reasoning_content`           |
| llama.cpp / Ollama / TGI      | **server-side** — `--reasoning` / `think` flag at launch, model template    | not a request field          | varies (`thinking` block or content)  |

**Common mistakes:**

  - Sending `reasoning_effort: xhigh` to NVIDIA Integrate, vLLM Qwen3, or
    DeepSeek-R1: silently dropped — gateway does not reject and not warn.
    Only Kimi / OpenAI Responses / OpenRouter honor it cleanly.
  - Sending `reasoning_effort: xhigh` to a provider that does support it,
    but placing it under `chat_template_kwargs.reasoning_effort` instead of
    top-level: also silently dropped.
  - Sending top-level `thinking_mode` / `enable_thinking` to NVIDIA: HTTP 400
    Validation error. Must nest under `chat_template_kwargs`.

## Hermes 12.x config: where extra_body actually goes

Hermes 12.x has **two** body-merge paths:

  - `providers.<name>.extra_body` → merged into the request body for any call
    routed through that named provider. The merge function is
    `agent/agent_init.py` `_merge_custom_provider_extra_body` (around line 1444).
  - `model.extra_body` → not read anywhere in the agent runtime. Setting it
    is cosmetic; it will not reach the wire.

So the **only** correct config shape for sending request knobs is:

```yaml
providers:
  my_provider_name:
    provider: nvidia                          # or vllm, groq, etc.
    base_url: https://integrate.api.nvidia.com/v1
    api_key:  $NVIDIA_API_KEY                  # or secrets ref
    model:    minimaxai/minimax-m3
    extra_body:
      chat_template_kwargs:
        enable_thinking: true
      # or for Kimi / OpenAI Responses:
      # reasoning_effort: high
```

Then route the agent through that named provider by setting
`model.provider: my_provider_name` (and `model.base_url` / `model.default`
to match).

**Caveat — point-path writes:** `hermes config set model.extra_body.foo bar`
writes a stringified JSON, not a YAML dict. The merge function only accepts
dicts (`isinstance(extra_body, dict)` in `_normalize_custom_provider_entry`,
`config.py:4195`). The fix is to use the deep dot-path: `hermes config set
providers.nvidia.extra_body.chat_template_kwargs.enable_thinking true` —
this creates the dict correctly. Verify with `sed -n '1,15p' ~/.hermes/config.yaml`
that the YAML looks like a nested dict and not a quoted JSON string.

## Verification probe (mandatory)

After any change, **do at least one HTTP call against the gateway with the
new payload** and confirm the response shape. Never trust that "the field
was set". The provided script does the probe for you:

```bash
python3 scripts/probe_thinking_fields.py \
    --base-url 'https://integrate.api.nvidia.com/v1' \
    --model minimaxai/minimax-m3 \
    --api-key-env NVIDIA_API_KEY \
    --question "17 * 23 是多少? 想一下再答"
```

It runs five probe variants: `reasoning_effort` only, no thinking fields,
`chat_template_kwargs.enable_thinking`, top-level `enable_thinking`, and
top-level `thinking_mode`. It prints `reasoning_content` length for each.
The variant that returns a non-empty `reasoning_content` is the one that
actually works for that provider — that becomes the field to inject.

If none returns reasoning content, the provider simply doesn't expose CoT
through this gateway path. Do not invent one — fall back to "use the
`content` field's reasoning (default behavior)" or pick a different
provider routing.

## Pitfalls

  - **Silent drop is the dominant failure mode.** OpenAI-compat gateways
    often accept unknown fields and ignore them. Probe the response — don't
    trust 200 OK with empty reasoning_content.
  - **`model.extra_body` is a black hole.** Tools that auto-generate config
    (including Hermes `config set`) tend to land keys in the wrong place.
    Always check the YAML shape.
  - **Provider routing vs named provider confusion.** Setting
    `model.provider: nvidia` is *not* enough to use named-provider
    `extra_body`. The merge function only fires when `model.provider` (or
    the routing selector) resolves to a key in `providers:`. If you only
    see `providers: {}`, your extra_body is dead.
  - **DefaultEnabled false.** Several model cards explicitly set
    `defaultEnabled: false`. Without an explicit toggle, reasoning stays
    off even when the "thinking" model name suggests on.
  - **Reasoning echo trap.** After a reasoning turn, some providers require
      - o1推理
      - CoT思考
      - chain-of-thought

    the previous `reasoning_content` string echoed back. Forgetting this
    breaks follow-up turns with HTTP 400. Hermes handles this in
    `copy_reasoning_content_for_api` (`agent_runtime_helpers.py:2155`);
    custom clients without this will hit the trap.
  - **Cross-provider fallback.** If you set a fallback chain and only the
    primary provider honors `extra_body`, the fallback may silently drop
    the toggle. Test the actual fallback path, not just the primary.
  - **`xhigh` is Hermes-internal.** It is the desktop app's label "Max" but
    has no universal meaning. The OpenAI Responses API accepts it; most
    open-source compat gateways don't. Don't expose `xhigh` to the wire
    without confirming.

## Reference

  - `references/nvidia-integrate-minimax-m3.md` — captured 2026-06-23, the
    five-probe evidence chain showing exactly which field configuration
    produces `reasoning_content` and which silently drop or 400.
  - `scripts/probe_thinking_fields.py` — re-runnable probe across the five
    common field placements; print reasoning_content presence per variant.

## One-shot recipe (NVIDIA Integrate MiniMax-M3 style)

Today, end-to-end:

  1. Run the probe script, confirm variant C
     (`chat_template_kwargs.enable_thinking: true`) returns non-empty
     `reasoning_content`.
  2. `hermes config set providers.nvidia.extra_body.chat_template_kwargs.enable_thinking true`
     (use the deep dot-path so YAML is a dict, not a JSON string).
  3. Verify with `sed -n '1,15p' ~/.hermes/config.yaml` — `extra_body`
     should be a nested YAML mapping, not `'"{...}" '`.
  4. Set `model.provider: nvidia` (or whichever named provider you set up).
  5. Send one real chat through Hermes and grep the session DB for the
     `reasoning_content` cell to confirm it logged.
