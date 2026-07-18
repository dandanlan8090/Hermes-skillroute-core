# Agnes AI API Reference (verified)

Condensed, authoritative API surface. Verified 2026-07-16 against:
- Official gateway + catalog: https://github.com/AgnesAI-Labs/AgnesAI-Models (catalog `2026.06.28`)
- Dev skill (CLI): https://github.com/Yacey/agnes-ai-generation-skill (branch `master`, 2026-06-21)
- Live calls made during this session (image + video + chat).

## Base URLs & auth
- OpenAI-compatible (chat/image): `https://apihub.agnes-ai.com/v1`
- Video task root: `https://apihub.agnes-ai.com`
- Auth: `Authorization: Bearer $AGNES_API_KEY` (read from `~/.hermes/.env`)

## Models (verified names)
- text/agent: `agnes-2.0-flash` (256K ctx; coding, reasoning, vision, tool-calling), `agnes-1.5-flash`
- image: `agnes-image-2.1-flash` (editing, flexible sizes — preferred), `agnes-image-2.0-flash` (fast)
- video: `agnes-video-v2.0`

## Endpoints
- chat: `POST /v1/chat/completions` (OpenAI-compatible; used for prompt optimization)
- image: `POST /v1/images/generations`
- video create: `POST /v1/videos`
- video poll: `GET /agnesapi?video_id=<id>`  (legacy: `GET /v1/videos/{task_id}` — less stable)

## Image — request
```json
{
  "model": "agnes-image-2.1-flash",
  "prompt": "<english>",
  "size": "1024x768",
  "extra_body": { "response_format": "url", "image": ["<public url>"] }
}
```
- `image` (img2img) MUST be in `extra_body` as a **list** of public URLs. Local paths → `400 invalid input image`.

## Image — response (verified)
```json
{ "created": 1784200621, "data": [ { "url": "https://platform-outputs.agnes-ai.space/images/t2i/....png", "b64_json": null, "revised_prompt": null } ], "usage": { "total_tokens": 0 } }
```

## Video — request
```json
{
  "model": "agnes-video-v2.0",
  "prompt": "<english>",
  "height": 704, "width": 1280, "num_frames": 121, "frame_rate": 24,
  "image": "<public url>"
}
```
- img2vid: `image` is a **top-level string** (NOT `extra_body`, NOT an array). Putting it in `extra_body` → `429`.
- Optional: `mode` (`ti2vid`/`keyframes`), `negative_prompt`, `seed`, `num_inference_steps`, `extra_body.image` (multi-image / keyframe array).
- `num_frames` MUST be `8n+1` (81=4s, 121=5s, 209=8s, 441=17s max).

## Video — create response (verified)
```json
{ "id": "task_...", "video_id": "task_...", "task_id": "task_...", "object": "video", "model": "agnes-video-v2.0", "status": "queued", "progress": 0, "created_at": 1784200654, "seconds": "3.4", "size": "1280x704" }
```
Poll with `video_id` (preferred over `task_id`).

## Video — poll response (verified)
```json
{ "status": "completed", "progress": 100, "video_url": "https://....mp4", "size": "...", "seconds": "...", "usage": { "duration_seconds": ... } }
```
- URL may appear in `video_url`, `url`, `output_url`, or `remixed_from_video_id` — check in that order.
- Status set: `queued`, `in_progress`, `succeeded|success|completed|done`, `failed|error|cancelled`.
- **Live response used `completed`, not `done`** — accept both.

## Rate limits (Free/default; catalog `2026.06.28`, reference values)
- Image RPM @1K: public 30 / exec 20; @2K: 10; @4K: 1
- Video RPM: public 2 / exec **1** (Token Plan → 5)
- Quota (Starter $4): image 4000/day, video 500 sec/day

## Error codes (key ones)
- `400` `content_policy_violation` → prompt tripped filter; rephrase (avoid flagged wording) + retry
- `400` other → bad params / `response_format` placement / inaccessible image URL
- `401` → bad/expired key; `402` → balance/quota; `403` → this key lacks model access
- `404` → wrong base URL / model name / duplicate `/v1`
- `429` → rate limit
- `500/502/503/504/520/522/524` → transient upstream; exponential backoff (`503` = service busy)
- Retry transient set `{408,429,500,502,503,504,520,522,524}` with exponential backoff.
