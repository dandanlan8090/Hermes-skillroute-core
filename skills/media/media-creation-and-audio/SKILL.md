---
name: media-creation-and-audio
description: Music generation (Suno/heartmula), audio analysis (spectrograms, chroma,
  MFCC), generative image/3D (ComfyUI, p5js), animation (manim), ASCII art and video
  (image/video-to-ASCII), browser-based creative coding (pretext) — class-level guidance
  for creative media production.
version: 1.0.0
author: Hermes Agent (umbrella consolidation)
license: MIT
metadata:
  hermes:
    tags:
      trigger:
      - 音频
      - 音乐生成
      - 音频分析
      - 媒体创作
      - 频谱
      - 媒体生成
      - 音视频处理
      - 内容创作
      disable:
      - creative_gen
      - read_only
    related_skills:
    - songwriting-and-ai-music
    - comfyui
    - manim-video
    - ascii-art
    - ascii-video
    - p5js
    - heartmula
platforms:
- linux
- macos
---
--
# Media Creation & Audio — Class-Level Guidance

This umbrella consolidates music generation, audio analysis, generative images,
3D/animation, ASCII conversion, and browser-based creative coding.

## Subsection Map

| What you need to do | Go to |
|---|---|
| Generate songs from lyrics + music tags | [Song Generation](#1-song-generation) |
| Analyze audio (spectrograms, mel-spectra, chroma, MFCC) | [Audio Analysis](#2-audio-analysis) |
| Generate images via Stable Diffusion / SDXL / Flux (ComfyUI) | [Generative Image / 3D (ComfyUI)](#3-generative-image--3d-comfyui) |
| Animate explanations (math, algorithms, physics) | [Math / Algorithm Animation (Manim)](#4-math--algorithm-animation-manim) |
| Convert images/video to colored ASCII | [ASCII Art & Video](#5-ascii-art--video) |
| Generative art, shaders, interactive visuals in the browser | [Browser Creative Coding (p5js / pretext)](#6-browser-creative-coding-p5js--pretext) |
| Write song lyrics, craft prompts for Suno | [Songwriting & AI Music](#7-songwriting--ai-music) |

## 1. Song Generation

See absorbed skill `heartmula` (formerly `media/heartmula`) for:
- Prompting Suno-style AI music generators
- Constructing lyrics + style tags + structure tags

## 2. Audio Analysis

See absorbed skill `songsee` (formerly `media/songsee`) for:
- Spectrogram generation from audio files
- Mel-spectrogram, chroma, MFCC extraction
- CLI-based audio feature visualization

## 3. Generative Image / 3D (ComfyUI)

All ComfyUI content is re-homed into this umbrella. Navigate by support dir:

- **Setup & lifecycle**: `scripts/comfyui/comfyui_setup.sh` (auto-install), `scripts/comfyui/hardware_check.py` (decide local vs Comfy Cloud), `scripts/comfyui/check_deps.py` + `auto_fix_deps.py` (dependency resolution).
- **Workflow execution**: `scripts/comfyui/run_workflow.py` + `run_batch.py` (parameter injection, batch runs), `scripts/comfyui/ws_monitor.py` + `fetch_logs.py` (WebSocket/exec monitoring), `health_check.py`, `extract_schema.py`.
- **API reference**: `references/comfyui/official-cli.md` (comfy-cli), `references/comfyui/rest-api.md` (REST/WebSocket execution), `references/comfyui/workflow-format.md` (node-graph format), `references/comfyui/template-integrity.md`.
- **Starter workflows**: `workflows/*.json` (sd15/sdxl txt2img+img2img+inpaint, flux_dev, upscale_4x, animatediff_video, wan_video_t2v).
- **Tests**: `tests/` (pytest suite for dep/workflow scripts).

Coverage: install, launch, manage ComfyUI (local + Comfy Cloud); image / video / audio generation via SD 1.5, SDXL, Flux, SD3, AnimateDiff, Wan T2V, Hunyuan; batch execution, img2img, inpainting; hardware check + cloud fallback.

## 4. Math / Algorithm Animation (Manim)

All Manim content is re-homed into this umbrella. Navigate by support dir:

- **Reference knowledge**: `references/manim/*.md` (mobjects, animations, camera-and-3d, equations, graphs-and-data, decorations, updaters-and-trackers, scene-planning, rendering, production-quality, animation-design-thinking, paper-explainer, troubleshooting, visual-design).
- **Setup**: `scripts/manim/setup.sh`.

Coverage: mathematical, scientific, and algorithmic visual explanations; 3Blue1Brown-style production; Cairo / manim engine render pipeline.

## 4b. Browser Creative Coding (p5.js)

All p5.js content is re-homed into this umbrella. Navigate by support dir:

- **Reference knowledge**: `references/p5js/*.md` (core-api, shapes-and-geometry, color-systems, animation, interaction, typography, webgl-and-3d, visual-effects, export-pipeline, troubleshooting).
- **Scripts**: `scripts/p5js/setup.sh`, `serve.sh`, `render.sh`, `export-frames.js`.
- **Templates**: `templates/p5js/viewer.html` (starter sketch viewer).

Coverage: p5.js sketches — generative art, GLSL shaders, interactive / 3D, data-viz, audio-reactive visuals; export to HTML/PNG/GIF/MP4/SVG.

## 5. ASCII Art & Video

See sibling skills `ascii-art` and `ascii-video` (under `creative/`) for:
- Pure Python ASCII art (pyfiglet, cowsay, image-to-ASCII)
- Converting video and audio to colored ASCII MP4 / GIF

## 6. Browser Creative Coding (p5js / pretext)

See absorbed skills `p5js` and `pretext` (under `creative/`) for:
- p5.js sketches: generative art, GLSL shaders, interactive / 3D
- Pretext demos: DOM-free text measurement/layout for typographic art,
  kinetic typography, ASCII obstacle art, text-as-geometry games

## 7. Songwriting & AI Music

See absorbed skill `songwriting-and-ai-music` (formerly `creative/songwriting-and-ai-music`) for:
- Lyric writing craft, phrasing, rhyme, and structure
- Prompt engineering for AI music generation (Suno, etc.)
- Tag taxonomy, narrative arc, genre conventions
