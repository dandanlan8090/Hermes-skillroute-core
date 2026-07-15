---
name: hermes-publish-workflow
description: Publier ssh/hermes-micro-framework风格行动到 GitHub 仓库前必须照走的全流程。包含本机仓 vs 远端仓查明、脱敏扫描、多文件复制/补加、frontmatter
  合规验证、push 后清理。
platforms:
- linux
- macos
version: 1.0.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags:
      trigger:
      - 推送 micro-framework
      - 发布 hermes
      - GitHub push workflow
      - 脱敏扫描
      - 本机仓检查
      - frontend 合规
      - 上传前验证
      disable:
      - 不适用场景
      - 无关任务
---
-

# Hermes Micro-Framework 发布工作流

## 关键差异（与“本地仓直接 git push” 区别)

**本机 `~/.hermes/` git仓 ≠ github.com/dandanlan8090/hermes-micro-framework 仓**

两个仓是独立 init 出来的根 commit（RTF2026-07-14 撞上后验证）。直接 `git push origin` 会非 fast-forward，拽 10+ 远程独有 commit。

下次发布路径不从 `~/.hermes` 起步，从 GitHub clone 出干净工作区起步。

## Trigger criterion

什么场景调取本 skill:
- 「推送到 github.com/dandanlan8090/...”
- 「发布微框架」
- 「公众号 ... 同步」
- 「某仓 push」
- 「用户明确说推」

什么场景不动:
- 私有 `~/.hermes` 本地 commit (不在远端推送路径上)
- 任何「跨仓」、「非发布」类 git push (走 repo-publishing-workflow skill)

## Workflow

### Step 0: 验证本机仓 vs GitHub 实际状态

```bash
cd ~/.hermes
git remote -v
# 如果是空的 = 本地仓走得是「本地备份」模式、不是发布路径——不要从这里推
```

### Step 1: 从 GitHub 克隆一个干净工作区

```bash
mkdir -p /tmp/hermes-publish-wt
cd /tmp/
gh repo clone dandanlan8090/hermes-micro-framework hermes-publish-wt
cd hermes-publish-wt
git remote -v   # 验证 origin
```

### Step 2: 验证本机底仓

本机 `~/.hermes/.git` host 本地仓，可以查到应收改动的 commit/howmany，又一次别推。

```bash
git fetch origin
git log origin/main --oneline -5       # 远端 last5
git log HEAD --oneline -5               # 本地 last5
```

### Step 3: 复制脱敏后清单

从「验证收集到的脱敏处于原样生成」「本会话什么实现了推进」两者交集后推。
**不是从本机 git commit 该走别人、是手动 copy 改过文件**。

### Step 4: Status/Commit/Push

```bash
cd /tmp/hermes-publish-wt
git status --short
git add -A                            # 仅选验证过的文件, 不 git add *
git commit -m "feat: <description>"
git remote set-url origin "https://$(gh auth token)@github.com/dandanlan8090/hermes-micro-framework.git"
git push
git remote set-url origin "https://github.com/dandanlan8090/hermes-micro-framework.git"
```

## 脱敏 同扫集合（不只 ~…）

- ~, [HOSTNAME], Hermes, hermes → `~`, [HOSTNAME], Hermes
- 个人信息: dandanlan@ → 脱漏写也别入仓
- 云主机IP: 149.88.*.*、192.168.*.* → <proxy-host> / <internal-ip>
- **用户自定义/自部署的代理模型名（<main-model>、自己起的会失效的名字）→ `<main-model>`**
- 司任开固名文件: → `~/<化名>.pdf`
- author 字段: `Hermes + 老黎` → `Hermes Agent`

## Pre-push 必须验证项

- [ ] Skill frontmatter 都合规: name, description, version(0+.+), author, license, platforms, trigger≥7, disable≥2
- [ ] 不入库: .env、*.db、memory/MEMORY.md、.usage.json、chroma/、.venv/
- [ ] worktree在 tmp/, 不污染主仓
- [ ] gh auth token 已准备好且涌进后被还原
- [ ] git log --oneline origin/main..HEAD 是本次 commit 列表, 验证后 push

## Pitfalls (从 2026-07-14 撞上出会补)

- **撞 10+ commit 区别时不要随意 force-push**: 反而会扰动公开 hash. 走 clone 干净工作区。
- **home/hermes 状态中 MEMORY.md 被改** → reset HEAD 它，依 .gitignore 决定
- **乱加 graphify-out/、缓存** → 补 gitignore '**'/*.  之后 add 可选
- **frontmatter trigger <7** → 会跳过合并等等... 补够 2+ 个机制专名
