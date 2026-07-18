#!/usr/bin/env python3
"""Agnes AI t2i / img2img / img2vid — backoff-wrapped, no hand-typed POST loop.

Usage:
  # text-to-image
  python3 agnes_generate.py t2i "拟人化小猫抓蝴蝶" --size 1024x768

  # image-to-image (edit an existing public image URL)
  python3 agnes_generate.py img2img "蝴蝶改成逃走的样子" --image <URL> --size 1024x768

  # image-to-video (animate a public image URL), 5s @ 24fps
  python3 agnes_generate.py img2vid "小猫跳起抓蝴蝶，蝴蝶飞远" --image <URL> --seconds 5

Outputs:
  Images -> ~/.hermes/images/<slug>_<ts>.png
  Videos -> ~/.hermes/videos/<slug>_<ts>.mp4

Key facts baked in from verified calls (2026-07-16):
  - Prompt MUST be English; we route the user text through agnes-2.0-flash first.
  - img2img: input image goes in extra_body["image"] as a LIST of URLs.
  - img2vid: input image is a TOP-LEVEL string URL (NOT in extra_body, NOT a list).
  - 503 "image queue is full" hits BOTH image and video POSTs -> exponential backoff.
  - Video num_frames must be 8n+1 (81=4s,121=5s,209=8s,441=17s max) @ frame_rate 24.
  - Poll via GET /agnesapi?video_id=... ; extract URL from url/video_url/output_url/remixed_from_video_id.
"""
import os, sys, time, argparse, urllib.request, requests

API = "https://apihub.agnes-ai.com"
API_V1 = API + "/v1"

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

def call_with_backoff(fn, max_retries=6, base=5):
    delay = base
    for attempt in range(max_retries):
        try:
            return fn()
        except requests.HTTPError as e:
            code = e.response.status_code if e.response is not None else 0
            transient = code in {408, 429, 500, 502, 503, 504, 520, 522, 524}
            if not transient or attempt == max_retries - 1:
                raise
            print(f"[backoff] HTTP {code}, retry {attempt+1} after {delay}s")
            time.sleep(delay)
            delay *= 2
    raise RuntimeError("exhausted retries")

def optimize(text, kind):
    key = agnes_key()
    sys_prompt = (
        "You are an expert AI image-prompt engineer. "
        if kind == "image" else
        "You are an expert AI video-prompt engineer. The user supplies a source image "
        "and wants to animate it. Describe the MOTION only. "
    ) + (
        "Turn the user's description into a detailed English prompt with subject, style, "
        "atmosphere, lighting, quality tags. For video also include subject action, "
        "environmental dynamics, camera movement. Avoid content-safety flag wording. "
        "Output ONLY the prompt, no explanation, no quotes."
    )
    H = {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}
    r = requests.post(f"{API_V1}/chat/completions", json={
        "model": "agnes-2.0-flash",
        "messages": [{"role": "system", "content": sys_prompt},
                     {"role": "user", "content": text}],
        "temperature": 0.7,
    }, headers=H, timeout=120)
    r.raise_for_status()
    return r.json()["choices"][0]["message"]["content"].strip()

def download(url, out_path):
    urllib.request.urlretrieve(url, out_path)
    if os.path.getsize(out_path) == 0:
        raise RuntimeError(f"downloaded empty file: {out_path}")
    return out_path

def gen_image(text, image_url=None, size="1024x768"):
    key = agnes_key()
    H = {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}
    prompt = optimize(text, "image")
    print("PROMPT:", prompt)
    extra = {"response_format": "url"}
    if image_url:
        extra["image"] = [image_url]          # img2img: list inside extra_body
    payload = {"model": "agnes-image-2.1-flash", "prompt": prompt,
               "size": size, "extra_body": extra}
    resp = call_with_backoff(lambda: requests.post(f"{API_V1}/images/generations",
        json=payload, headers=H, timeout=120))
    resp.raise_for_status()
    url = resp.json()["data"][0]["url"]
    out = os.path.expanduser(f"~/.hermes/images/agnes_{int(time.time())}.png")
    return download(url, out)

def gen_video(text, image_url, seconds=5):
    key = agnes_key()
    H = {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}
    prompt = optimize(text, "video")
    print("PROMPT:", prompt)
    num_frames = {4: 81, 5: 121, 8: 209, 17: 441}.get(seconds, 121)
    payload = {"model": "agnes-video-v2.0", "prompt": prompt,
               "image": image_url,                 # img2vid: TOP-LEVEL string
               "height": 720, "width": 1280,
               "num_frames": num_frames, "frame_rate": 24}
    resp = call_with_backoff(lambda: requests.post(f"{API}/v1/videos",
        json=payload, headers=H, timeout=120))
    resp.raise_for_status()
    data = resp.json()
    video_id = data.get("video_id") or data.get("id") or data.get("task_id")
    print("VIDEO_ID:", video_id)
    params = {"video_id": video_id}
    vid_url = None
    for _ in range(120):
        time.sleep(5)
        r = requests.get(f"{API}/agnesapi", params=params,
                         headers={"Authorization": f"Bearer {key}"}, timeout=30)
        result = r.json()
        status = str(result.get("status", "")).lower()
        print("poll:", status)
        if status in {"succeeded", "success", "completed", "done"}:
            vid_url = (result.get("url") or result.get("video_url")
                       or result.get("output_url") or result.get("remixed_from_video_id"))
            break
        elif status in {"failed", "error", "cancelled"}:
            raise RuntimeError(f"video failed: {result}")
    if not vid_url:
        raise RuntimeError("no video url after polling")
    out = os.path.expanduser(f"~/.hermes/videos/agnes_{int(time.time())}.mp4")
    return download(vid_url, out)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("mode", choices=["t2i", "img2img", "img2vid"])
    ap.add_argument("text")
    ap.add_argument("--image", help="public image URL for img2img/img2vid")
    ap.add_argument("--size", default="1024x768")
    ap.add_argument("--seconds", type=int, default=5, choices=[4, 5, 8, 17])
    args = ap.parse_args()

    if args.mode in ("img2img", "img2vid") and not args.image:
        ap.error(f"{args.mode} requires --image <public URL>")

    os.makedirs(os.path.expanduser("~/.hermes/images"), exist_ok=True)
    os.makedirs(os.path.expanduser("~/.hermes/videos"), exist_ok=True)

    if args.mode == "t2i":
        out = gen_image(args.text, size=args.size)
    elif args.mode == "img2img":
        out = gen_image(args.text, image_url=args.image, size=args.size)
    else:
        out = gen_video(args.text, args.image, seconds=args.seconds)
    print("SAVED:", out, os.path.getsize(out), "bytes")

if __name__ == "__main__":
    main()
