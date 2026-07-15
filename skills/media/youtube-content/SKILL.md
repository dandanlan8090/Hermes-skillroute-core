---
name: youtube-content
description: YouTube transcripts to summaries, threads, blogs.
platforms:
- linux
- macos
- windows
metadata:
  hermes:
    tags:
      trigger:
      - youtube
      - 视频
      - 字幕
      - 内容总结
      - youtube
      - YouTube摘要
      - 视频总结
      - 字幕提取
      disable:
      - 直播
      - 下载视频
license: MIT
author: Hermes Agent
version: 1.0.0
---
--
# YouTube Content Tool

## When to use

Use when the user shares a YouTube URL or video link, asks to summarize a video, requests a transcript, or wants to extract and reformat content from any YouTube video. Transforms transcripts into structured content (chapters, summaries, threads, blog posts).

Extract transcripts from YouTube videos and convert them into useful formats.

## Setup

Use `uv` so the dependency is installed into the same Hermes-managed environment
that runs the helper script:

```bash
uv pip install youtube-transcript-api
```

## Helper Script

`SKILL_DIR` is the directory containing this SKILL.md file. The script accepts any standard YouTube URL format, short links (youtu.be), shorts, embeds, live links, or a raw 11-character video ID.

```bash
# JSON output with metadata
uv run python3 SKILL_DIR/scripts/fetch_transcript.py "https://youtube.com/watch?v=VIDEO_ID"

# Plain text (good for piping into further processing)
uv run python3 SKILL_DIR/scripts/fetch_transcript.py "URL" --text-only

# With timestamps
uv run python3 SKILL_DIR/scripts/fetch_transcript.py "URL" --timestamps

# Specific language with fallback chain
uv run python3 SKILL_DIR/scripts/fetch_transcript.py "URL" --language tr,en
```

## Output Formats

After fetching the transcript, format it based on what the user asks for:

- **Chapters**: Group by topic shifts, output timestamped chapter list
- **Summary**: Concise 5-10 sentence overview of the entire video
- **Chapter summaries**: Chapters with a short paragraph summary for each
- **Thread**: Twitter/X thread format — numbered posts, each under 280 chars
- **Blog post**: Full article with title, sections, and key takeaways
- **Quotes**: Notable quotes with timestamps

### Example — Chapters Output

```
00:00 Introduction — host opens with the problem statement
03:45 Background — prior work and why existing solutions fall short
12:20 Core method — walkthrough of the proposed approach
24:10 Results — benchmark comparisons and key takeaways
31:55 Q&A — audience questions on scalability and next steps
```

## Workflow

1. **Fetch** the transcript using the helper script with `--text-only --timestamps` via `uv run python3`.
2. **Validate**: confirm the output is non-empty and in the expected language. If empty, retry without `--language` to get any available transcript. If still empty, tell the user the video likely has transcripts disabled.
3. **Chunk if needed**: if the transcript exceeds ~50K characters, split into overlapping chunks (~40K with 2K overlap) and summarize each chunk before merging.
4. **Transform** into the requested output format. If the user did not specify a format, default to a summary.
5. **Verify**: re-read the transformed output to check for coherence, correct timestamps, and completeness before presenting.

## Error Handling

- **Transcript disabled**: tell the user; suggest they check if subtitles are available on the video page.
- **Private/unavailable video**: relay the error and ask the user to verify the URL.
- **No matching language**: retry without `--language` to fetch any available transcript, then note the actual language to the user.
- **Dependency missing**: run `uv pip install youtube-transcript-api` and retry.

## Video Scripting (Technical Explainers)

For producing Chinese-language technical explainer video scripts about open-source projects (opposite direction — creating content, not consuming it): see the absorbed `content-creation/technical-video-script` guide in `templates/technical-video-script-reference.md`.

Key patterns:
- GitHub repo reconnaissance: source-of-truth is `git clone --depth 1`, `gh repo view`, `npm view` — never README badges alone.
- Video structure: 10-12 min B站 format with hook → positioning → pain points → 3-4 features → demo → fit check → wrap-up.
- Demo commands must be annotated with filming notes (what to show, what to mask, what could fail).
- Cover copy: 5 title candidates + cover text + image source path.
- Fact-verification checklist before delivery (stars via `gh`, version via `npm view`, commands via `--help`).
- B站/YouTube script starting template: `templates/script-template.md`.

## Related Skills

- `templates/technical-video-script-reference.md` — full video-script production guide (absorbed from `content-creation/technical-video-script`)
- `references/output-formats.md` — extended output format specs for transcripts

      - YouTube摘要
      - 视频总结
      - 字幕提取
