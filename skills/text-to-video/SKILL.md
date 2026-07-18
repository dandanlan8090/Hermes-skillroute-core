---
name: text-to-video
description: 使用 Agnes AI Video V2.0 API 进行文生视频和图生视频。支持异步任务创建、轮询查询、结果下载。飞书会话中必须发送源 URL 供用户查看。触发词：生成视频、文生视频、图生视频、video generation、ai video。
version: 1.1.0
author: Hermes-cm211 + 老黎
updated: 2026-07-16
verified_against:
  official_repo: https://github.com/AgnesAI-Labs/AgnesAI-Models
  catalog_version: 2026.06.28
license: MIT
platforms:
- linux
metadata:
  hermes:
    tags:
      trigger:
      - 文生视频
      - 图生视频
      - 生成视频
      - text-to-video
      - video generation
      - agnes video
      - 视频生成
      - img2vid
    disable:
    - 音乐
    - 运维
    - shell脚本
    - 数据库
    - LLM训练
category: creative
related_skills:
  - agnes-image-generation
---

# Agnes AI Video V2.0 — 文生视频 & 图生视频

> **版本与核验声明**
> - 本技能于 `2026-07-16` 对照官方仓库 [`AgnesAI-Labs/AgnesAI-Models`](https://github.com/AgnesAI-Labs/AgnesAI-Models)（catalog `2026.06.28`）及开发者 skill [`Yacey/agnes-ai-generation-skill`](https://github.com/Yacey/agnes-ai-generation-skill) 实测核验。
> - **Agnes 官方可能随时调整调用要求**（端点、模型名、字段名、限流、内容审核）。遇非预期错误先回官方 `MODEL_CATALOG.md` / `docs/ERROR_CODES.md` / `examples/` 核对，再判断用法问题还是上游已变更。
> - 全部为**直接 HTTP 请求**，零额外依赖（仅 `python3` + `urllib`），不打包上游脚本，避免上游改动导致技能静默失效。
> - API key 仅从 `~/.hermes/.env` 的 `AGNES_API_KEY` 读取。

使用 Agnes AI Video V2.0 异步 API 生成视频。API key 从 `~/.hermes/.env` 的 `AGNES_API_KEY` 读取。
Base URL：`https://apihub.agnes-ai.com`。

## 触发条件

用户提到"生成视频"、"文生视频"、"图生视频"、"video generation"、"ai video" 等关键词时加载。

## 前置检查

1. 确认 `AGNES_API_KEY` 存在于 `~/.hermes/.env`
2. 创建保存目录 `~/.hermes/videos/`

```bash
grep -q AGNES_API_KEY ~/.hermes/.env && echo "OK" || echo "MISSING"
mkdir -p ~/.hermes/videos
```

### API key 读取（每步复用）

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

## 执行步骤

### Step 1: 构建请求并创建任务

```python
import os, json, urllib.request

API_KEY = agnes_key()
base_url = "https://apihub.agnes-ai.com"
headers = {
    "Authorization": f"Bearer {API_KEY}",
    "Content-Type": "application/json",
}

# 文生视频
payload = {
    "model": "agnes-video-v2.0",
    "prompt": "<英文提示词，越详细越好>",
    "height": 768,
    "width": 1152,
    "num_frames": 121,   # 8n+1: 121=5s, 441=20s, 最大441
    "frame_rate": 24,
}

# 图生视频：'image' 是顶层字符串 URL（不是 extra_body，不是数组）
# payload["image"] = "<图片URL>"

data = json.dumps(payload).encode("utf-8")
req = urllib.request.Request(f"{base_url}/v1/videos", data=data, headers=headers, method="POST")
with urllib.request.urlopen(req, timeout=120) as resp:
    result = json.loads(resp.read().decode("utf-8"))
    print(json.dumps(result, indent=2))

video_id = result.get("video_id") or result.get("id") or result.get("task_id")
```

### Step 2: 轮询等待完成

```python
import time
poll_url = f"{base_url}/agnesapi?video_id={video_id}"

video_url = None
while True:
    time.sleep(15)
    req = urllib.request.Request(poll_url, headers=headers, method="GET")
    with urllib.request.urlopen(req, timeout=30) as resp:
        status = json.loads(resp.read().decode("utf-8"))
    s = str(status.get("status", "")).lower()
    print(f"Status: {s} | Progress: {status.get('progress')}")

    if s in ("succeeded", "success", "completed", "done"):
        for field in ["video_url", "url", "output_url", "remixed_from_video_id"]:
            if status.get(field):
                video_url = status[field]
                break
        break
    elif s in ("failed", "error"):
        print(f"Failed: {status}")
        break
```

### Step 3: 下载并发送

```python
import urllib.request

output_dir = os.path.expanduser("~/.hermes/videos/")
os.makedirs(output_dir, exist_ok=True)
ts = int(time.time())
path = os.path.join(output_dir, f"video_{ts}.mp4")

urllib.request.urlretrieve(video_url, path)
print(f"MEDIA:{path}")
print(f"\n源网址: {video_url}")
```

## Step 0: 提示词优化（先走主模型）

中文或其他非英文提示词，**先通过主模型 `agnes-2.0-flash` 优化成英文**再发起请求（英文更稳定，且主模型能补全动作/镜头/光影细节）。

```python
import os, requests

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

def optimize_video_prompt(user_prompt: str) -> str:
    sys = ("You are an expert AI video-prompt engineer. Turn the user's description into a "
           "detailed English video prompt: subject action, environmental dynamics, camera "
           "movement, style consistency. Avoid wording that could trip a content-safety filter. "
           "Output ONLY the prompt.")
    r = requests.post("https://apihub.agnes-ai.com/v1/chat/completions", json={
        "model": "agnes-2.0-flash",
        "messages": [{"role": "system", "content": sys},
                     {"role": "user", "content": user_prompt}],
        "temperature": 0.7,
    }, headers={"Authorization": f"Bearer {agnes_key()}", "Content-Type": "application/json"}, timeout=120)
    r.raise_for_status()
    return r.json()["choices"][0]["message"]["content"].strip()

# prompt = optimize_video_prompt("<用户原始描述>")
```

- 仅当提示词含非 ASCII 字符（`any(ord(ch) > 127 for ch in p)`）时才需要翻译；纯英文且已详细可跳过。
- 若生图/生视频返回 `400 content_policy_violation`，让主模型换掉触发词重试。

## 错误处理与限流

- 先读真实 HTTP 状态码再判断：
  - `400 content_policy_violation` → 提示词触发审核，换词重试
  - `401` → 检查 `AGNES_API_KEY`；`402` → 余额/配额不足；`403` → 该 key 无模型权限
  - `429` → 限流（免费档视频可执行 RPM=1），退避重试
  - `500/502/503/504/520/522/524` → 临时故障，指数退避重试（`503`=service busy）
- 免费档配额：视频 500 秒/天；视频 RPM 公开 2 / 可执行 **1**。
- 重试对 `408,429,500,502,503,504,520,522,524` 做指数退避。

## 注意事项

- **提示词先用主模型优化成英文**，中文需先翻译（见 Step 0）
- `num_frames` 必须符合 `8n+1` 公式（121=5秒, 441=20秒, 最大441）
- 帧率推荐 24fps（支持范围 1-60）
- 首次创建可能返回 503（Service busy），退避重试即可
- 视频默认 5 秒（121帧/24fps）
- 免费账户每日配额 500 秒
- **飞书会话中必须发送源 URL 供用户查看确认**
- 图生视频时 `image` 字段为顶层字符串，非 `extra_body`、非数组
- 轮询用 `GET /agnesapi?video_id=...`，不要用 `GET /v1/videos/{video_id}`（返回 task_not_exist）
- 可选参数：`mode`(ti2vid/keyframes)、`negative_prompt`、`seed`、`num_inference_steps`、`extra_body.image`(多图/关键帧数组)
