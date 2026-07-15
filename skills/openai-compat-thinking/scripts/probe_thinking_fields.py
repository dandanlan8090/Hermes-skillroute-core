#!/usr/bin/env python3
"""Probe an OpenAI-compatible chat completions endpoint for which
reasoning/thinking field placement actually fires `reasoning_content`.

Why this exists:

  Different OpenAI-compat providers (NVIDIA Integrate, vLLM, Groq, Together,
  OpenRouter) take the same idea — "enable reasoning" — through entirely
  different request keys. Some accept unknown fields silently (Hermes-side
  configs that set `model.extra_body.reasoning_effort` to xhigh on NVIDIA
  will get HTTP 200 but no reasoning_content). Some reject unknown fields
  with HTTP 400. Some routing works only inside `chat_template_kwargs` vs
  top-level. There is no shortcut — you have to send the bytes and read
  the reply.

This probes the five common placements:

  A. top-level `reasoning_effort`
  B. no thinking field at all (baseline — what does default return?)
  C. `chat_template_kwargs.enable_thinking: true` inside extra_body
  D. top-level `enable_thinking: true`
  E. top-level `thinking_mode: "enabled"`

For each it prints:
  - HTTP status
  - the message dict keys
  - the length and a preview of `message.reasoning_content`
  - a one-line preview of `message.content`

The variant whose `reasoning_content` is non-empty is the one that the
gateway actually routes to the model's CoT. Use that as the canonical
field placement for that provider.

Usage:

  python3 probe_thinking_fields.py \\
      --base-url https://integrate.api.nvidia.com/v1 \\
      --model     minimaxai/minimax-m3 \\
      --api-key-env NVIDIA_API_KEY \\
      --question  "17 * 23 是多少? 想一下再答"

  # Optional: pick a custom prompt
  python3 probe_thinking_fields.py \\
      --base-url https://integrate.api.nvidia.com/v1 \\
      --model     minimaxai/minimax-m3 \\
      --api-key-env NVIDIA_API_KEY \\
      --question  "求 1+2+...+100, 先推理再回"

  # Optional: tighten max_tokens for faster probing
  python3 probe_thinking_fields.py \\
      --base-url https://integrate.api.nvidia.com/v1 \\
      --model     minimaxai/minimax-m3 \\
      --api-key-env NVIDIA_API_KEY \\
      --max-tokens 512

  # Optional: use an API key directly (cleaner for CI; avoid shell history)
  python3 probe_thinking_fields.py \\
      --base-url https://integrate.api.nvidia.com/v1 \\
      --model     minimaxai/minimax-m3 \\
      --api-key-env NVIDIA_API_KEY

Exit code is 0 if at least one variant returns non-empty
reasoning_content, else 1. CI-friendly.

Caveats:
  - This script reads the API key from the OS environment by default; do
    not paste tokens into command lines (history, process listings).
  - Network calls may incur cost. Use small max_tokens for probing.
  - Reasoning behavior can change between model revisions; re-probe when
    bumping model versions.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.request
from typing import Any


def _post(base_url: str, payload: dict[str, Any], api_key: str) -> tuple[int, dict[str, Any] | str]:
    """POST a payload; return (http_status, parsed_json_or_text)."""
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        base_url.rstrip("/") + "/chat/completions",
        data=data,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            body = resp.read().decode("utf-8")
            return resp.status, json.loads(body)
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        try:
            return exc.code, json.loads(body)
        except json.JSONDecodeError:
            return exc.code, body


def _variant(label: str, payload: dict[str, Any], base_url: str, api_key: str) -> dict[str, Any]:
    """Run one variant and shape the result for printing."""
    status, body = _post(base_url, payload, api_key)
    record: dict[str, Any] = {"label": label, "http": status}
    if status != 200:
        record["error"] = (
            body if isinstance(body, str) else json.dumps(body)[:400]
        )
        return record
    try:
        msg = body["choices"][0]["message"]
    except (KeyError, IndexError, TypeError):
        record["error"] = "no choices[0].message in response"
        record["raw"] = json.dumps(body)[:400]
        return record
    record["keys"] = list(msg.keys())
    rc = msg.get("reasoning_content")
    record["reasoning_content_len"] = len(rc) if isinstance(rc, str) else 0
    record["reasoning_content_preview"] = (
        (rc[:300] + "…") if isinstance(rc, str) and len(rc) > 300 else rc
    )
    content = msg.get("content")
    record["content_preview"] = (
        (content[:200] + "…") if isinstance(content, str) and len(content) > 200 else content
    )
    return record


def _print_record(rec: dict[str, Any]) -> None:
    label = rec["label"]
    http = rec["http"]
    print(f"\n=== {label} (HTTP {http}) ===")
    if "error" in rec:
        print(f"  error: {rec['error']}")
        return
    print(f"  msg keys: {rec.get('keys')}")
    print(f"  reasoning_content_len: {rec.get('reasoning_content_len')}")
    rc = rec.get("reasoning_content_preview")
    if rc:
        print(f"  reasoning_content_preview: {rc!r}")
    cp = rec.get("content_preview")
    if cp:
        print(f"  content_preview: {cp!r}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", required=True,
                        help="OpenAI-compat endpoint, e.g. https://integrate.api.nvidia.com/v1")
    parser.add_argument("--model", required=True,
                        help="Model id as the gateway expects, e.g. minimaxai/minimax-m3")
    parser.add_argument("--api-key-env", default=None,
                        help="Name of the env var holding the bearer token. "
                             "Either --api-key-env or --api-key is required.")
    parser.add_argument("--api-key", default=None,
                        help="Raw bearer token. Prefer --api-key-env to "
                             "avoid leaking the key into shell history.")
    parser.add_argument("--question", default="17 * 23 是多少? 想一下再答",
                        help="User message to send to the model.")
    parser.add_argument("--max-tokens", type=int, default=2048,
                        help="Max tokens per response (default 2048).")
    parser.add_argument("--temperature", type=float, default=0.6)
    args = parser.parse_args()

    if args.api_key:
        api_key = args.api_key
    elif args.api_key_env:
        api_key = os.environ.get(args.api_key_env)
        if not api_key:
            print(f"error: env var {args.api_key_env!r} is unset", file=sys.stderr)
            return 2
    else:
        print("error: pass --api-key-env or --api-key", file=sys.stderr)
        return 2

    common = {
        "model": args.model,
        "messages": [{"role": "user", "content": args.question}],
        "max_tokens": args.max_tokens,
        "temperature": args.temperature,
        "top_p": 0.95,
        "stream": False,
    }

    variants: list[tuple[str, dict[str, Any]]] = [
        ("A reasoning_effort top-level",
         {**common, "reasoning_effort": "xhigh"}),
        ("B no thinking fields",
         {**common}),
        ("C chat_template_kwargs.enable_thinking",
         {**common, "chat_template_kwargs": {"enable_thinking": True}}),
        ("D enable_thinking top-level",
         {**common, "enable_thinking": True}),
        ("E thinking_mode top-level",
         {**common, "thinking_mode": "enabled"}),
    ]

    any_reasoning = False
    for label, payload in variants:
        rec = _variant(label, payload, args.base_url, api_key)
        _print_record(rec)
        if rec.get("reasoning_content_len", 0) > 0:
            any_reasoning = True

    print("\n--- summary ---")
    if any_reasoning:
        print("at least one variant produced a non-empty reasoning_content.")
        print("use the first variant above whose preview is non-empty as the "
              "canonical field placement for this provider.")
        return 0
    print("no variant produced reasoning_content — provider may not expose CoT "
          "through this gateway path, or the model is non-reasoning.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
