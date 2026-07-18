# Agnes Video API — notes

Endpoint base: `https://apihub.agnes-ai.com`

## Create task
`POST /v1/videos`
```json
{ "model": "agnes-video-v2.0", "prompt": "<en>", "height": 704, "width": 1280, "num_frames": 121, "frame_rate": 24 }
```
- img2vid adds top-level `"image": "<public url>"` (NOT in extra_body, NOT a list).

## Poll
`GET /agnesapi?video_id=<id>` — preferred. Legacy `GET /v1/videos/{task_id}` works but less stable.
`GET /v1/videos/{video_id}` → returns `task_not_exist`, do NOT use.

## State mapping
- in-progress: `queued`, `processing`, `running`
- success: `succeeded` / `success` / `completed` / `done`
- failure: `failed` / `error` / `cancelled`

## URL extraction priority
`url` → `video_url` → `output_url` → `remixed_from_video_id`

## Pitfalls
- `num_frames` must be `8n + 1` (81 / 121 / 209 / 441).
- Tasks may stall in `queued` >15 min — abort and retry.
- First create may 503 (Service busy) — retry.
- Free tier: 500 sec / day.
