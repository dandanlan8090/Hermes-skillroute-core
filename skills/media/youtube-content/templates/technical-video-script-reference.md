---
name: technical-video-script
description: "Research an open-source project from its GitHub repository and produce a structured Chinese-language technical explainer video script with timestamps, demo commands, cover copy, shot list, and filming pitfalls."
version: 1.0.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags:
      trigger:
        - "出一期讲解视频"
        - "出视频介绍XX项目"
        - "写视频稿"
        - "视频脚本"
        - "technical explainer video"
        - "make a video about"
        - "项目拆解视频"
        - "做一期视频讲解"
        - "讲解开源项目"
        - "出期视频介绍"
      disable:
        - "summarize video"
        - "字幕下载"
        - "视频总结"
        - "transcript"
    skill_type: "workflow"
    priority: "normal"
platforms: [linux, macos]
---

# Technical Video Script — Research-to-Script Pipeline

Produce a ready-to-film Chinese-language explainer video about an open-source project. The deliverable is a single Markdown file covering: hook, positioning, core feature breakdown (3-4 max), demo commands, cover copy, shot list, and filming pitfalls.

## When to use

User wants a video about a GitHub/OSS project. Output is a script, not a transcript of an existing video and not a visual design artifact.

## Workflow

### 1. Plan

Write a plan to `.hermes/plans/` covering research scope, video structure, and deliverables. Use the `plan` skill.

### 2. Repo Recon (source-of-truth, not README alone)

Clone the repo with `git clone --depth 1`. Then cross-verify every claim:

| Tool | What it confirms |
|------|-----------------|
| `README.md` | Project pitch, quick start, feature list |
| `package.json / Cargo.toml / pyproject.toml` | Version, deps, engine constraints, license |
| `docs/` | Architecture, routing, compression, resilience — deeper than README |
| `gh repo view <owner/repo> --json ...` | Stars, forks, description, license, last push |
| `npm view <package>` | Published version, description, install command |
| Screenshots in `docs/screenshots/` | UI visual evidence |
| `git log -1` | Most recent commit subject |

**Critical**: README badges (stars, downloads, providers) may be outdated relative to the published npm or Docker Hub version. Always cross-check `npm view` and `gh repo view`.

### 3. Extract 4-5 Core Points

From the recon, identify:

- **One-line positioning**: "What is this project in one sentence?"
- **Pain points it solves**: List 3-5 concrete frustrations
- **Killer features** (max 4): pick the ones that genuinely differentiate
- **Comparison to alternatives**: if the project has a comparison doc, use it
- **Quick start path**: the shortest path from `git clone` or `npm install` to a working demo

### 4. Design Video Structure

Standard 10-12 minute format for Chinese tech explainers (B站/YouTube):

| Segment | Duration | Content |
|---------|----------|---------|
| Hook | 0:00-0:40 | Problem statement — what hurts without this project |
| Positioning | 0:40-1:50 | One-sentence pitch, architecture diagram |
| Pain points | 1:50-3:20 | 3-5 concrete problems with before/after |
| Feature 1 | 3:20-5:20 | Deep dive on the flagship capability |
| Feature 2 | 5:20-6:50 | Second core feature |
| Feature 3 | 6:50-8:10 | Third core feature |
| Agent/dev value | 8:10-9:30 | What makes it useful for power users |
| Demo | 9:30-10:50 | Live terminal/Dashboard walkthrough |
| Fit check | 10:50-11:50 | Who it's for / not for |
| Wrap-up | 11:50-12:20 | One-line verdict |

Adjust for shorter formats (5-8 min) by merging features and truncating fit check.

### 5. Write Full Script

Per segment, write:

- **On-screen visual** — what appears on screen (screenshots, terminal, diagrams, logos)
- **On-screen text** — key subtitles (text-overlay bullets)
- **Spoken lines** — the narrator's actual words
- **The "trick"** — what makes each segment click (e.g. contrast, demo, analogy)

### 6. Produce Demo Commands

Every command the narrator will type must be:

1. Written exactly as it will appear on screen
2. Placed in a code block with the correct shell syntax
3. Annotated with a filming note (what to show, what to mask, what could fail)

API keys and tokens use placeholder `<OMNIROUTE_API_KEY>` format — never show real credentials.

### 7. Create Cover Copy

- 5 title candidates (pick the B站-appropriate one)
- Cover text: main line + subtitle line
- Cover image source path from repo (screenshots) + suggested edits

### 8. List Filming Pitfalls

Always include:

- What NOT to claim (unverified numbers, outdated stats from old README badges)
- What NOT to show (API keys, tokens, private data)
- What needs disclaimers (free-tier ToS risks, environment-specific behavior)
- What cannot be demonstrated without a running instance

### 9. Verify Every Fact

Before delivering the script, re-verify each claim against source:

- [ ] Stars/forks → checked via `gh repo view`
- [ ] Version → checked via `npm view` or `package.json`
- [ ] Provider/model numbers → found in README + docs
- [ ] Command syntax → matches README or `--help`
- [ ] Screenshot exists → `file` + `identify` on the path
- [ ] Architecture claim → supported by docs source

## Template

A reusable script template is at `templates/script-template.md`. Copy it as a starting point for any new project.

## Reference Example

The OmniRoute video script at `~/.hermes/skills/content-creation/technical-video-script/references/omniroute-example.md` shows a full output.

## Pitfalls

- **Don't inflate free-tier claims**: README "free tokens" often includes one-time signup credits and rate-limit ceilings. Distinguish steady, first-month, uncapped, and theoretical.
- **Don't claim functionality you haven't tested live**: If a demo command requires a running instance, say so. If you can't install because of dependencies, document the exact install path but don't pretend it works.
- **Don't trust README badges as fact**: `npm view` and `gh repo view` are the actual source of truth.
- **Don't make "all agents support this" claims for MCP/A2A**: Say the project exposes the protocol; client support varies.
- **Don't show real keys/tokens**: Use placeholder strings and add filming notes to mask them.

## Related Skills

- `youtube-content` — for processing transcripts FROM existing videos (opposite direction)
- `visual-design` — for creating Excalidraw/SVG diagrams and cover images
- `plan` — for the initial task plan
- `github` — for deeper GitHub API queries during research
