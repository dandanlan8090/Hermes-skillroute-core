---
name: repo-publishing-workflow
description: Hermes 配置/技能发布到开源社区的标准工作流：脱敏检查 → 技能合规验证 → git 操作 → 推送。触发：任何发布/同步/分享到社区的操作。禁用：纯本地使用/内网同步。
version: 1.1.0
author: Hermes Agent
license: MIT
platforms:
- linux
- macos
- windows
metadata:
  hermes:
    tags:
      trigger:
      - 发布
      - repo
      - 开源
      - 同步到 github
      - 分享
      - publish
      - push to remote
      - 脱敏
      - sanitize
      disable:
      - 纯本地使用
      - 内网同步
      - 个人备份
    skill_type: workflow
    priority: high
    related_skills:
    - new-skill-template
    - ai-conv-style-discipline
prerequisites:
  commands:
  - grep
  - gh
---
# Repo Publishing Workflow（发布工作流）

## 概述

将 Hermes 配置或技能发布到开源社区前，必须完整执行：脱敏扫描 → 技能合规验证 → Git 操作 → 推送。

**本 skill 不适用于**：纯本地使用、内网同步、个人备份。

## 触发条件

以下任一场景必须走完整流程：
- 推送到任何 remote 仓库
- 将文件分享给他人
- 创建或更新开源 repo
- 将本地修改同步到其他机器（rsync 跨设备也建议执行）

## 完整流程（六步）

### Step 0：用户授权（最高优先级，红线）

**禁止任何自动推送。** Agent 不得在未获用户明确指令的情况下执行 `git push`。
即便检测到待提交的变更，也必须先通知用户并等待确认。

- 每次推送前必须等待用户明确说"推"或"push"（一次性临时授权，不允许"以后都可以推"的持久授权）
- 禁用所有自动触发推送到 remote 的逻辑（cron job、文件变更钩子、watcher.py 等）
- 例外：脱敏扫描和本地 commit 不需要授权，仅 push 到 remote 需要
- 如果用户在之前会话中明确拒绝过推送，则之后也不应推送
- **绝不能以"已经为这个项目做过 XX 次提交"为由推断用户授权了推送** — 每次 push 独立授权
- **绝不能因为本地 commit 成功就擅自 push** — commit ≠ push

### Step 0.5：公开发布项目的内容校验（新增红线，2026-07）

如果 repo 是**公开项目**（`github.com/<username>/<repo>` 对所有人可见），每次 push 前**必须**逐项验证：

1. **没有真实路径/用户名/主机名泄露**
   ```bash
   # 扫所有待提交文件
   git diff --cached --name-only | xargs grep -l "/home/[a-z]\+\|C:\\\\Users\\\\\|[HOSTNAME]" 2>/dev/null
   # 期望输出为空
   ```

2. **没有 API key / token / 凭证泄露**
   ```bash
   git diff --cached | grep -E "ghp_|gho_|ghu_|ghs_|sk-|xox[baprs]|nvapi-|BEGIN.*PRIVATE" || echo "OK: no secrets"
   ```

3. **skill 内部文档不含个人信息**
   - 排查 frontmatter 中 `author:` 字段是否包含个人标识
   - 排查 example 中的 placeholder 是否用了 `[YOUR_USERNAME]` 而非实际账号

4. **README / 文档中的 clone URL 已脱敏**
   - 必须是 `github.com/YOUR_USERNAME/<repo>` 形式，不含真实账号

5. **执行完整 run 验证**
   - 不接受"看起来对"的检查，必须实际运行 grep/扫描命令并看到 0 行匹配

**对于公开 repo，发布前主动询问用户**：
> "本次 commit + push 到公开 repo `github.com/<user>/<repo>`，涉及 3 个文件变更。是否确认推送？"

**如果用户拒绝或未回应**：
- 完成本地 commit 后**立即停止**
- 不再尝试 push
- 在下次 session 重新询问，**不要记忆上次的拒绝**——用户可能改变主意

### Step 0.6：agent 作者署名规范

skill 的 `author:` 字段在公开 repo 中**必须使用通用名**，不得使用 `Hermes` 等内部代号：
- ✅ `author: Hermes Agent`
- ❌ `author: Hermes`
- ❌ `author: dandanlan8090`

脱敏时一并替换：本地 `Hermes` → repo `Hermes Agent`。

### Step 0.7：运行环境凭据不可发布门禁（2026-07-12）

**红线：真实运行参数不得进入 repo。** 包括但不限于代理节点、服务器登录、控制台密钥、证书指纹、完整客户端配置。底层发布流程必须把它当作 push 前强制 gate，而不是依赖 agent 记忆。

**禁止提交的真实数据类型：**
- 代理节点凭据：Trojan password、SS password、VLESS/VMess UUID、Reality public/private key、shortId、订阅链接、`ss://` / `trojan://` / `vless://` URI
- 服务器接入信息：公网 IP + SSH 端口组合、root SSH 命令、真实主机名、云主机内网 IP
- 客户端配置：完整 `mihomo` / Clash / sing-box / Xray config，尤其包含 `proxies:`、`proxy-groups:`、`external-controller`、`secret` 的文件
- 证书与指纹：私钥、证书 sha256 指纹、`pinnedPeerCertSha256` 的真实值
- 本地环境：`/etc/mihomo/config.yaml`、`/usr/local/etc/xray/config.json` 的真实内容

**允许提交的内容：**
- 脱敏模板：`<IP>`、`<PORT>`、`<PASSWORD>`、`<UUID>`、`<SHA256>`、`<SSH_PORT>`
- 过程方法：如何从运行环境现取参数、如何验证、如何 rotate
- 非敏感通用命令：不含真实 IP/密码/token 的安装和验证命令

**推送前必须执行的扫描（对 staged diff + 工作树双扫）：**

优先运行随 skill 附带的门禁脚本（扫描逻辑集中维护，避免多处复制漂移）：
```bash
bash ~/.hermes/skills/repo-publishing-workflow/scripts/pre-push-runtime-secret-gate.sh
```

若脚本不可用，按以下等价检查手工执行：
```bash
echo "=== staged secret URI scan ==="
git diff --cached | grep -Ei "ss://|trojan://|vless://|vmess://|hysteria2://|tuic://" && exit 1 || echo "OK: no proxy uri"

echo "=== staged proxy credential scan ==="
git diff --cached | grep -Ei "(password|uuid|private-key|public-key|short-id|pinnedPeerCertSha256|external-controller|secret): *['\"]?[A-Za-z0-9_~@%+=:;.,/-]{8,}" && exit 1 || echo "OK: no obvious proxy credentials"

echo "=== staged runtime config path scan ==="
git diff --cached | grep -Ei "/etc/mihomo|/usr/local/etc/xray|config\.yaml|config\.json|root@|ssh -p [0-9]+" && exit 1 || echo "OK: no runtime config paths"

echo "=== working tree sensitive filenames scan ==="
git ls-files --others --exclude-standard; git ls-files | grep -Ei "(mihomo|clash|xray|sing-box).*config|config\.yaml|config\.json|server\.key|\.pem$|\.crt$" && echo "REVIEW REQUIRED: sensitive-looking file names" || echo "OK: no sensitive-looking tracked filenames"
```

**命中处理：**
1. 立即中止 commit/push。
2. 把真实值替换为占位符，或把文件移出 repo 并加入 `.gitignore`。
3. 若真实凭据已经进入 git 历史：先 rotate secret，再用 `git filter-repo` / BFG 清历史；delete/archive repo 不能替代 rotate。
4. 重新执行本 Step 0.7 与 Step 1 全量扫描，全部 OK 后才可继续。

### Step 1：脱敏扫描（最优先）

发布前必须扫描并替换所有个人标识符。对公开 repo，也扫描 `vdb/` 工具链文件（Python 脚本中可能含路径硬编码、API endpoint 地址）。

**必须检查的模式：**

| 模式 | 替换为 |
|------|--------|
| `Hermes` / `hermes` | `Hermes` |
| `YOUR_USERNAME` 或实际 GitHub 用户名 | `YOUR_USERNAME`（在 repo 中） |
| `C:\Users\<name>\AppData` | `~/.hermes/` |
| `/home/<username>/` | `~/` 或 `$HOME` |
| 实际 token、PAT、API key 字符串 | `[REDACTED]` 或留空 |
| 邮箱、手机号、具体账号 ID | `[PERSONAL_INFO]` |
| 主机名（如 `[HOSTNAME]`） | `[HOSTNAME]` |

**扫描命令：**

```bash
# 扫描所有 md 文件
grep -rn "Hermes\|hermes\|/home/[a-z]\+\|C:\\\\Users\\\\\|token\|ghp_\|pat_\|sk-\|API_KEY" --include="*.md" .

# 扫描路径相关
grep -rn "dandanlan\|lan\|your_username\|[HOSTNAME]" --include="*.md" .

# 扫描 token 模式
grep -rn "ghp_\|sk-\|xox[baprs]" --include="*.md" .
```

**脱敏后验证**：

```bash
# 确认无遗漏
grep -rn "ghp_\|sk-\|xox[baprs]" --include="*.md" . || echo "OK: no tokens"
grep -rn "dandanlan\|lan\." --include="*.md" . || echo "OK: no usernames"
```

### Step 2：技能合规验证（NEW_SKILL_TEMPLATE 检查清单）

任何新创建或修改的 skill 发布前必须逐项核对：

**Frontmatter 检查：**
- [ ] `name` 是小写、连字符分隔、无空格
- [ ] `description` 是中英双语、包含触发和禁用说明
- [ ] `version` 遵循语义化版本
- [ ] `trigger` 标签至少 5 个，覆盖中文和英文
- [ ] `disable` 标签至少 3 个，明确排除场景
- [ ] `skill_type` 是预定义值之一（methodology/workflow/tool/integration）
- [ ] `priority` 是预定义值之一（highest/high/normal/low）
- [ ] `platforms` 已声明（linux/macos/windows 三选一）
- [ ] `license` 已声明（推荐 MIT）

**标签质量检查：**
- [ ] `trigger` 词汇来自用户自然语言，非技能内部术语
- [ ] `trigger` 和 `disable` 无重叠或矛盾
- [ ] `disable` 覆盖了常见误触发场景

**脱敏检查：**
- [ ] 无个人路径（`/home/name/`、`C:\Users\name\`）
- [ ] 无真实用户名、主机名
- [ ] 无 token、key、secret 字符串
- [ ] 示例中的占位符使用 `[YOUR_USERNAME]` 等标准占位符

### Step 3：目录结构合规检查

Repo 技能目录标准结构：

```
skills/
└── <skill-name>/         # 目录名 = frontmatter.name，全小写
    └── SKILL.md          # 主文件必须是 SKILL.md
```

额外顶层目录（非 skill，但属于 repo 的一部分，发布时必须同步）：

```
vdb/                    # 技能检索工具链（sparse.py / embed.py / indexer.py / matcher.py）
├── sparse.py
├── embed.py
├── indexer.py
├── matcher.py
├── __init__.py
└── .env.example
scripts/                # 初始化脚本
└── init-vdb.sh
```

> `vdb/` 包含运行时 Python 代码，发布前必须做同样的脱敏扫描（注意 `.env.example` 不含真实密钥，`embed.py` 的 API URL 只需保持通用性）。

**常见错误：**
- ❌ `NEW_SKILL_TEMPLATE.md`（单文件，应该在 `NEW_SKILL_TEMPLATE/SKILL.md`）
- ❌ `skills/new-skill-template/SKILL.md`（目录名含大写或下划线）
- ✅ `skills/plan/SKILL.md`

**检查命令：**

```bash
# 检查是否所有 skill 都在正确目录结构下
for f in skills/*/SKILL.md; do
  dir=$(basename $(dirname "$f"))
  name=$(sed -n '/^name:/{s/name: *//;s/ //g;p}' "$f")
  if [ "$dir" != "$name" ]; then
    echo "MISMATCH: dir=$dir name=$name"
  fi
done
```

### Step 4：Git 操作规范

**分支策略：**
- 主分支保护：`main` 不直接推送，通过 PR 或确认后推送
- Commit 信息规范：简洁描述，类型标注
  - `feat:` 新功能
  - `fix:` 修复
  - `sanitize:` 脱敏处理
  - `refactor:` 重构
  - `docs:` 文档

**Token 安全：**
- 推送到 remote 时，用 `git remote set-url` 先临时注入 token，推送后立即还原为无 token 的 URL
- 禁止将 token 写入 `.git/config`

```bash
# 正确的 token 注入方式
git remote set-url origin https://$(gh auth token)@github.com/OWNER/REPO.git
git push
git remote set-url origin https://github.com/OWNER/REPO.git
```

### Step 5：验证推送结果

- 推送后检查 remote URL 已还原
- 访问 GitHub 确认文件内容正确（无 personal info 残留）

## 常见问题

### 脱敏遗漏的常见来源

1. **README 中的 clone URL**：`github.com/dandanlan8090` → `github.com/YOUR_USERNAME`
2. **技能正文中的本地路径**：`~/.hermes` → `~/.hermes/`
3. **Skill 内的示例路径**：`C:\Users\lan\AppData` → `~/.hermes/`
4. **作者名和版本历史**：`author: Jesse Vincent (obra)` → `author: Hermes Agent`
- [ ] 描述文字中的账号名：正文里提到 `dandanlan8090`
- [ ] author 字段不含 `Hermes` 等内部代号（应使用 `Hermes Agent`）
- [ ] 代码示例中的 API Key 必须是占位符（如 `[YOUR_NVIDIA_API_KEY]`），不是真实值

### 公开 repo 的额外检查（Step 0.5）

如果 repo 是公开项目，**Step 0.5 的所有 grep 扫描必须实际执行**（不接受"我觉得没问题"的主观判断）：

```bash
# 完整脱敏扫描（推送前必跑）
git add -A  # 或 git add <files>
echo "=== 个人路径扫描 ==="
git diff --cached --name-only | xargs grep -lE "/home/[a-z]+|C:\\\\Users\\\\|[HOSTNAME]" 2>/dev/null || echo "OK"

echo "=== Token 扫描 ==="
git diff --cached | grep -E "ghp_|gho_|ghu_|ghs_|sk-|xox[baprs]|nvapi-|nvapi-?api-?key" || echo "OK: no tokens"

echo "=== 真实用户名扫描 ==="
git diff --cached | grep -iE "dandanlan|lan8090|你的账号" || echo "OK: no usernames"

echo "=== Hermes 代号扫描 ==="
git diff --cached | grep -iE "Hermes" || echo "OK: no internal codename"

echo "=== author 字段 ==="
git diff --cached | grep -E "author:.*Hermes" || echo "OK: author safe"
```

**任何一项非"OK"则必须中止 push，回到脱敏步骤。**

### `USER.md.md` 双后缀 bug

`.hermes/memories/USER.md` 文件在 SOUL.md 加载顺序中常被误写成 `USER.md.md`（多一个 `.md` 后缀）。实际文件名是 `USER.md`，不是 `USER.md.md`。

**检测：**
```bash
ls -la ~/.hermes/memories/USER.md*
```

## 与其他技能的关系

| 技能 | 关系 |
|------|------|
| `new-skill-template` | 提供合规检查标准，本 skill 在发布前调用其 checklist |
| `ai-conv-style-discipline` | 提供输出风格规范（简洁、无冗余），本 skill 的脱敏检查不含风格检查 |
| `hermes-shipping-verification` | 发布验证的通用版，repo 推送属于特殊场景的发布 |

---

## Config-Only Publishing 子流程

当任务是将 Hermes **配置文件本身**（SOUL.md、AGENTS.md、USER.md、skills/）发布到公开仓库时，除了主流程的通用步骤外，还需处理以下配置特有的环节：

### Config 特有的源文件读取

```bash
~/.hermes/SOUL.md
~/.hermes/memories/USER.md      # 注意：单 .md 后缀，不是 USER.md.md
~/.hermes/memories/MEMORY.md
~/.hermes/AGENTS.md
```

### MEMORY.md 策略

- 默认不发布（几乎必然包含个人信息）
- 若确实需要，从中选择性提取通用内容
- USER.md 转为**模板**（用户画像占位符），不包含真实信息

### 发布决策表

```
SOUL.md       → 直接发布（通用规则，无个人信息）
AGENTS.md     → 直接发布（方法论，无个人信息）
USER.md       → 转为模板（USER.md.template），真实配置保留本地
MEMORY.md     → 不发布
skills/       → 挑选关联 skill，逐一脱敏后发布
```

### 关联技能发现

从 SOUL.md / AGENTS.md 正文扫描所有被引用的 skill 名称：

```bash
grep -rh "skill_view\|skill:" ~/.hermes/skills --include="SKILL.md" | \
  grep -oE "name: [a-z0-9-]+" | sort -u
grep -rh "related_skills:" ~/.hermes/skills --include="SKILL.md"
```

**必须打包的 skill 类型**：
1. SOUL.md / AGENTS.md 正文明确引用的
2. `related_skills` 中声明的依赖
3. 用户在对话中明确要求的

Skill 脱敏要点：author 替换为 `Hermes Agent`，移除具体路径/版本回执/个人信息，保留 frontmatter 和核心流程。

**最后更新**: 2026-07-10