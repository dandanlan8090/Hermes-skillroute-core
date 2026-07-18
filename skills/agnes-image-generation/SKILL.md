---
name: agnes-image-generation
description: Generate images (text-to-image, img2img) and videos (text-to-video, img2vid) using Agnes AI APIs. Use when the user asks to draw, generate pictures, 文生图, 图生图, 生图, text-to-image, image-to-image, AI绘画, or to animate / generate video (文生视频, 图生视频, img2vid, text2vid). Loads AGNES_API_KEY from ~/.hermes/.env.
version: 4.1.0
author: Hermes Agent + 老黎
updated: 2026-07-16
verified_against:
  official_repo: https://github.com/AgnesAI-Labs/AgnesAI-Models
  catalog_version: 2026.06.28
license: MIT
dependencies:
- python3
- requests
platforms:
- linux
- macos
metadata:
  hermes:
    tags:
      trigger:
      - 文生图
      - 图生图
      - 生图
      - image generation
      - agnes AI
      - 图片生成
      - text-to-image
      - image-to-image
      - AI绘画
      - 文生视频
      - 图生视频
      - 生视频
      - text-to-video
      - img2vid
    disable:
    - 音乐
    - 运维
    - shell脚本
    - 数据库
    - LLM训练
category: creative
related_skills:
  - text-to-video
---

# Agnes AI Image & Video Generation

> **版本与核验声明（务必先读）**
> - 本技能于 `2026-07-16` 对照官方仓库 [`AgnesAI-Labs/AgnesAI-Models`](https://github.com/AgnesAI-Labs/AgnesAI-Models)（catalog 版本 `2026.06.28`）及开发者 skill [`Yacey/agnes-ai-generation-skill`](https://github.com/Yacey/agnes-ai-generation-skill) 实测核验，端点/模型名/参数均来自真实 API 调用。
> - **Agnes 官方可能随时调整调用要求**（端点路径、模型名、字段名、限流、内容审核策略）。若某次调用返回非预期错误，先回官方仓库 `MODEL_CATALOG.md` / `docs/ERROR_CODES.md` / `examples/` 核对最新要求，再决定是用法问题还是上游已变更。
> - 所有调用均为**直接 HTTP 请求**，零额外依赖（仅 `python3` + `requests`/`urllib`），不打包任何上游脚本，避免上游改动导致技能 silently 失效。
> - API key 仅从 `~/.hermes/.env` 的 `AGNES_API_KEY` 读取，不外泄、不进版本库。

Generate images (text-to-image, img2img) and videos (img2vid, text2vid) via the Agnes AI HTTP API.
API key is read from `~/.hermes/.env` (`AGNES_API_KEY`). Outputs go to `~/.hermes/images/` and `~/.hermes/videos/`.

Base URL: `https://apihub.agnes-ai.com/v1` (OpenAI-compatible chat + image; custom `/v1/videos` and `/agnesapi` for video).

## What's in this skill

| Item | Purpose |
|-|-|
| `references/video-api-notes.md` | Video API endpoint behavior, pitfalls, state mapping |
| `scripts/agnes_generate.py` | Backoff-wrapped CLI for t2i / img2img / img2vid — auto-retries `503 image queue is full` on BOTH image and video POSTs |

> **No external companion script required.** This skill is self-contained — it calls the Agnes HTTP API directly with `requests` (or `urllib` fallback). The original upstream referenced a `agnes_api.py` companion script that is NOT bundled here, so all steps below use the direct API.

## When to Use

- "draw", "generate image", "文生图", "图生图", "画图" → text-to-image or img2img
- "animate", "generate video", "图生视频", "文生视频", "img2vid" → video generation
- User provides an image URL and asks to modify it → img2img
- User provides an image URL and asks to create a video from it → img2vid

## Prerequisites

1. `AGNES_API_KEY` exists in `~/.hermes/.env`
2. Output directories exist: `~/.hermes/images/`, `~/.hermes/videos/`
3. `requests` library available (or use `urllib` as fallback)

Verify / prepare:

```bash
grep -q AGNES_API_KEY ~/.hermes/.env && echo "OK" || echo "MISSING"
mkdir -p ~/.hermes/images ~/.hermes/videos
```

### API key loader (reuse in every step)

```python
import os

def agnes_key():
    key = ""
    with open(os.path.expanduser("~/.hermes/.env"), encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line.startswith("AGNES_API_KEY="):
                key = line.split("=", 1)[1].strip().strip('"').strip("'")
                break
    if not key or key.startswith("<"):
        raise RuntimeError("AGNES_API_KEY not found / not set in ~/.hermes/.env")
    return key
```

## Workflow

### Step 1: Determine Task Type

| Input | Request | Mode |
|-|-|-|
| Prompt only, no image | Generate from text | text-to-image / text-to-video |
| Prompt + image URL | Modify existing image | img2img |
| Prompt + image URL | Animate to video | img2vid |

### Step 2: Prepare Prompt (run through the MAIN MODEL first)

**Always optimize the prompt through the main chat model (`agnes-2.0-flash`) before calling the image/video API.** English prompts are far more stable, and the main model both translates and enriches the description.

- Translation detection: only translate when the prompt contains non-ASCII chars (`any(ord(ch) > 127 for ch in prompt)`). Pure-English prompts can skip translation but still benefit from enrichment.
- **Content-safety guard (important):** instruct the main model to avoid wording that could trip Agnes's content filter (`content_policy_violation` → HTTP 400). If a generation returns 400 with `content_policy_violation`, rephrase the prompt to remove the flagged phrasing and retry.

```python
import os, requests

def agnes_key():
    # (same loader as above)
    key = ""
    with open(os.path.expanduser("~/.hermes/.env"), encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line.startswith("AGNES_API_KEY="):
                key = line.split("=", 1)[1].strip().strip('"').strip("'")
                break
    if not key or key.startswith("<"):
        raise RuntimeError("AGNES_API_KEY not found / not set in ~/.hermes/.env")
    return key

def needs_translation(prompt: str) -> bool:
    return any(ord(ch) > 127 for ch in prompt)

def optimize_prompt(user_prompt: str, kind: str = "image") -> str:
    """Send the user's description through the main model to produce a polished English prompt."""
    key = agnes_key()
    if not needs_translation(user_prompt):
        # still enrich short English prompts; skip if already detailed
        if len(user_prompt.split()) > 25:
            return user_prompt
    sys = (
        "You are an expert AI image-prompt engineer. " if kind == "image" else
        "You are an expert AI video-prompt engineer. "
    ) + (
        "Turn the user's description into a detailed, high-quality English prompt. "
        "Include subject, style, atmosphere, lighting, and quality tags. "
        "For video also include subject action, environmental dynamics, and camera movement. "
        "Avoid any wording that could trip a content-safety filter. "
        "Output ONLY the prompt, no explanation."
    )
    r = requests.post("https://apihub.agnes-ai.com/v1/chat/completions", json={
        "model": "agnes-2.0-flash",
        "messages": [{"role": "system", "content": sys},
                     {"role": "user", "content": user_prompt}],
        "temperature": 0.7,
    }, headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"}, timeout=120)
    r.raise_for_status()
    return r.json()["choices"][0]["message"]["content"].strip()

# Usage in Step 3/4/5:
#   prompt = optimize_prompt(user_text, kind="image")   # for text-to-image
#   prompt = optimize_prompt(user_text, kind="video")    # text-to-video
#   edit_prompt = optimize_prompt(edit_instruction, kind="image")  # img2img edit
```

**Image prompt structure:** Subject → Style (realistic / anime / watercolor / oil painting) → Atmosphere → Quality tags (high detail, 4k, cinematic lighting).

**Video prompt structure:** Subject action → Environmental dynamics (hair moves, fabric flows) → Camera movement → Style consistency (match original image).

### Step 3: Generate Image (text-to-image / img2img)

```python
import os, time, requests
import urllib.request

API_KEY = agnes_key()  # from loader above
BASE = "https://apihub.agnes-ai.com/v1"
headers = {"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"}

# text-to-image
payload = {
    "model": "agnes-image-2.1-flash",
    "prompt": "<optimized english prompt>",
    "size": "1024x768",
    "extra_body": {"response_format": "url"},
}
# image-to-image (edit): 'image' MUST be inside extra_body as a list of URLs
# payload["extra_body"]["image"] = ["<public input image url>"]

resp = requests.post(f"{BASE}/images/generations", json=payload, headers=headers, timeout=120)
resp.raise_for_status()
image_url = resp.json()["data"][0]["url"]  # publicly accessible HTTPS

out = os.path.expanduser(f"~/.hermes/images/t2i_{int(time.time())}.png")
urllib.request.urlretrieve(image_url, out)
print(out)
```

**Step 3 completion criteria:** response returns a valid `url` in `data[0]`; URL is a publicly accessible HTTPS.

### Step 4: Generate Video (text-to-video / img2vid)

```python
import os, time, requests
import urllib.request

API_KEY = agnes_key()
BASE = "https://apihub.agnes-ai.com"
headers = {"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"}

payload = {
    "model": "agnes-video-v2.0",
    "prompt": "<motion description in english>",
    "height": 704,
    "width": 1280,
    "num_frames": 121,   # must be 8n+1 (81=4s, 121=5s, 209=8s, 441=17s max)
    "frame_rate": 24,
}
# img2vid: 'image' is a TOP-LEVEL string URL (NOT in extra_body, NOT a list)
# payload["image"] = "<public input image url>"

resp = requests.post(f"{BASE}/v1/videos", json=payload, headers=headers, timeout=120)
resp.raise_for_status()
data = resp.json()
video_id = data.get("video_id") or data.get("id") or data.get("task_id")
```

**Poll for completion** (prefer `GET /agnesapi?video_id=<id>`):

```python
params = {"video_id": video_id}
for _ in range(120):  # up to ~10 min
    time.sleep(5)
    r = requests.get(f"{BASE}/agnesapi", params=params, headers={"Authorization": f"Bearer {API_KEY}"}, timeout=30)
    result = r.json()
    status = str(result.get("status", "")).lower()
    if status in {"succeeded", "success", "completed", "done"}:
        vid_url = (result.get("url") or result.get("video_url")
                   or result.get("output_url") or result.get("remixed_from_video_id"))
        if vid_url:
            out = os.path.expanduser(f"~/.hermes/videos/img2vid_{int(time.time())}.mp4")
            urllib.request.urlretrieve(vid_url, out)
            print(out)
        break
    elif status in {"failed", "error", "cancelled"}:
        print("Failed:", result)
        break
```

**Step 4 completion criteria:** task created with valid `video_id`; poll returns success status; file downloaded to `~/.hermes/videos/` with size > 0.

### Step 5: Output Result

- Images: `MEDIA:<path>` for display
- Videos: `MEDIA:<path>` for playback. In a Feishu chat, also send the source URL so the user can open/verify it.

## Decision Reference

| Scenario | Path | Notes |
|-|-|-|
| Simple text-to-image | Step 3 | Fastest |
| Edit existing image | Step 3 (img2img) | `image` in `extra_body` as list |
| Text-to-video | Step 4 | auto-poll via loop above |
| Image-to-video | Step 4 (img2vid) | `image` top-level string |

## Common Pitfalls

1. **Prompt language**: always translate Chinese/non-English prompts to English first.
2. **img2img `image` field**: inside `extra_body` as array `["<url>"]`, NOT top-level. URL must be publicly accessible — local paths → `invalid input image` (HTTP 400). If the user gives a local image, upload it to a public host first, or recreate via text-to-image.
3. **Video `image` field**: top-level string `"image": "<url>"`, NOT in `extra_body`, NOT a list. Putting it in `extra_body` triggers rate limit (429).
4. **Polling endpoint**: prefer `GET /agnesapi?video_id=<id>`. Legacy `GET /v1/videos/{task_id}` is less stable. Never use `GET /v1/videos/{video_id}` → `task_not_exist`.
5. **Video URL extraction**: completed response may put URL in `remixed_from_video_id` instead of `video_url`/`url`. Check in order: `url` → `video_url` → `output_url` → `remixed_from_video_id`.
6. **Frame count**: `num_frames` must be `8n + 1`. Valid: 81 (4s), 121 (5s), 209 (8s), 441 (17s max). Default 121.
7. **Video queue instability**: tasks may stall in `queued` >15 min. Abort and retry with a new task.
8. **Model versions**: `agnes-image-2.1-flash` for images, `agnes-video-v2.0` for videos.
9. **Timeout**: image ~15-60s, video creation ~1-5 min, polling up to 10 min. Set timeouts accordingly.
10. **503 `image queue is full, please retry later`** — NOT only on video create; the **images/generations** POST can also return it when the image queue is saturated. Treat as transient and retry with exponential backoff. Verified 2026-07-16: a t2i edit (img2img) call returned `503 image queue is full` on the first attempt, succeeded on retry after ~15s. Wrap the image POST in the same backoff as the video POST. The `scripts/agnes_generate.py` helper already does this.

## Verification Checklist

- [ ] `AGNES_API_KEY` set and non-empty in `~/.hermes/.env`
- [ ] Output directory exists (`~/.hermes/images/` or `~/.hermes/videos/`)
- [ ] Input image URL (if any) accessible via HEAD
- [ ] Prompt is English (translated if needed)
- [ ] Image API: `response_format` inside `extra_body`, not top-level
- [ ] Video API: `image` top-level string, not in `extra_body`
- [ ] Video `num_frames` = `8n + 1` (81 or 121 recommended)
- [ ] Polling uses `/agnesapi?video_id=...`
- [ ] Video URL extracted from all candidate fields in priority order
- [ ] Output file saved and size > 0

## Error handling (verified against official ERROR_CODES.md)

Read the real HTTP status before guessing. Notable cases:

| Status | Meaning | Action |
|-|-|-|
| `400` `content_policy_violation` | Prompt tripped content filter | Rephrase via main model (avoid flagged wording), retry |
| `400` other | Bad params / wrong `response_format` placement / inaccessible image URL | Fix payload per Common Pitfalls |
| `401` | Bad / expired key | Check `AGNES_API_KEY` in `~/.hermes/.env` |
| `402` | Balance / quota insufficient | Check Token Plan / recharge |
| `403` | Account/key lacks model access | Confirm model permission for this key |
| `404` | Wrong base URL / model name / duplicate `/v1` | Verify endpoint paths |
| `429` | Rate limit (RPM) | Backoff; Free tier video RPM = 1 exec/min |
| `500/502/503/504/520/522/524` | Transient upstream | Exponential backoff + retry; `503` = service busy. **Note:** `503 image queue is full, please retry later` appears on **both** the image and video POST paths — wrap both in the backoff below. |

**Backoff wrapper** for transient errors (`408, 429, 500, 502, 503, 504, 520, 522, 524`):

```python
import time
def call_with_backoff(fn, max_retries=6):
    delay = 5
    for attempt in range(max_retries):
        try:
            return fn()
        except requests.HTTPError as e:
            code = e.response.status_code if e.response is not None else 0
            transient = code in {408,429,500,502,503,504,520,522,524}
            if not transient or attempt == max_retries - 1:
                raise
            time.sleep(delay); delay *= 2
```

Apply `call_with_backoff` to **both** the image (`/images/generations`) and video (`/v1/videos`) POSTs — the `503 image queue is full` message is observed on both paths. A ready-to-run helper that does this end-to-end (optimize prompt via `agnes-2.0-flash`, POST with backoff, download / poll) lives at `scripts/agnes_generate.py` — prefer it over hand-typing the POST loop each time.

## Rate limits & quotas (catalog `2026.06.28`, reference values)

- Image RPM (Free/default, 1K res): public 30 / executable 20. 2K → 10, 4K → 1.
- Video RPM (Free/default): public 2 / executable **1**. Token Plan → 5.
- Quota (Free tier example — Starter $4): `agnes-image` 4,000 imgs/day, `agnes-video` 500 sec/day.

## References

- Image docs: https://agnes-ai.com/doc/agnes-image-21-flash
- Video docs: https://agnes-ai.com/doc/agnes-video-v20
- Platform: https://platform.agnes-ai.com/
- Official gateway + catalog: https://github.com/AgnesAI-Labs/AgnesAI-Models
- Dev skill (agnes_api.py CLI): https://github.com/Yacey/agnes-ai-generation-skill
