---
name: hermes-micro-framework
description: Hermes Micro Framework 仓库维护技能——记录 repo 推送规则、脱敏标准、目录结构和更新工作流。当需要向 github.com/dandanlan8090/hermes-micro-framework 推送内容时使用。
version: 1.1.0
author: Hermes Agent
license: MIT
platforms:
- linux
- macos
metadata:
  hermes:
    tags:
      trigger:
      - hermes-micro-framework
      - 推送 micro-framework
      - 更新 micro-framework
      - micro-framework repo
      - 同步微框架
      - 发布 micro-framework
      - 脱敏检查
      - 技能合规验证
      disable:
      - 普通 git push
      - 非 Hermes 配置
      - 私有 MEMORY.md
      - 不发布到开源
    skill_type: workflow
    priority: high
    related_skills:
    - hermes-base-config-sync
    - repo-publishing-workflow
    - hermes-agent-skill-authoring
---
# Hermes Micro Framework Repo Sync

## Overview

本 skill 用于维护 `dandanlan8090/Hermes-skillroute-core` 仓库（2026-07-15 由 `hermes-micro-framework` 重建而来，旧库归档为 `hermes-micro-framework-archived`）。该仓库是 Hermes 微内核架构的配置模板仓库，包含极致拆解后的 SOUL.md、按分类组织的技能集和 vdb 检索工具链。

核心原则：**内容必须脱敏、结构必须合规、每次推送必须用户明确授权。**

**架构分界（成熟 Agent 框架标准）**：代码（`vdb/*.py`, `scripts/*`）+ 元数据（`skills/**` 的 frontmatter 是框架元数据资产）入库；索引（Chroma）+ 运行时状态（`.venv`, `.env`）由 `install.sh` 在用户本地就地生成，**不入仓库**。

---

## 本地 ver 备份（无 remote，纯本地记录 + 回滚）

适用：私有 `~/.hermes/` 下的引擎/脚本（如 `vdb/`、`scripts/`）需版本化但不推送到公开
repo。与上文"推送到 github.com/dandanlan8090/hermes-micro-framework"是**两条独立路径**：
本地备份默认不 push；公开发布仍需上文 Step 1-7 + 用户明确授权。

### 初始化（真实验证过的步骤，2026-07-12）
```bash
cd ~/.hermes
git init                                   # 本地仓库, 无 remote
# .gitignore 用白名单法: 先整体忽略大目录, 再 ! 反向加回需跟踪的源码
printf 'message_tags.db\nvdb/chroma/\nvdb/.venv/\n.env\n*.db\n' >> .gitignore
```
白名单范式（避免 `vdb/` 整目录忽略后源码也丢）：
```
vdb/                 # 先整体忽略
!vdb/               # 反向加回目录遍历
!vdb/*.py           # 跟踪源码
!vdb/eval/
!vdb/eval/*.py
!vdb/idf_map.json   # 元数据(重建可生成, 但留备份便于回滚到已知好状态)
!vdb/vdb_state.json
vdb/chroma/         # 再忽略运行时(向量库大)
vdb/.venv/          # 虚拟环境
vdb/__pycache__/
```
- **运行时/敏感一律忽略**：`*.db`（state.db/message_tags.db 等）、`config.yaml`、`cache/`、`logs/`、
  `cron/`、`pastes/`、`sessions/`、`auth.json`、`.env.bak*`、`*.lock`/`*.pid`/`*.shm`/`*.wal`、
  `skills/.usage.json`（vdb 自动维护的使用统计）、`hermes-agent/`（核心源码仓库不混入库）。
- **已跟踪文件要忽略**需 `git rm --cached <file>`（仅加 .gitignore 对已跟踪文件不生效）。

### 纳入 + 提交
```bash
git add scripts/ skills/ SOUL.md          # 按用户指定范围, 不越界加 vdb/
git add vdb/ .gitignore                    # 后续补 vdb 时单列(白名单已生效)
git commit -m "feat: ..."
```

### 打版本 tag（回滚纪律）
```bash
git tag -a "vdb-v2.1-context-routing" -m "版本说明 + 回滚命令: git checkout <tag>"
```
- tag message 写明回滚命令，便于一键回到已知好状态。
- `git log --oneline --decorate` 确认 tag 挂在正确 commit。

### Pitfalls（本会话实测踩过）
- **`git add skills/` 会首次批量收进全部 skill**——含 `.usage.json` 等运行时文件。
  要么提交前用 `git add -n` dry-run 检查，要么先写 .gitignore 再 add。
- **已跟踪文件忽略失效**——`git rm --cached` 才能从索引移除（磁盘保留）。
- **`.env` 写保护**——`.env` 被 Hermes 保护，不要 `git add .env`；用 `.env.example` 占位。
- **`vdb/chroma/` 必忽略**——133 文件向量库，入仓会爆体积且重建可生成。

---

## Canonical Repo Layout

```
hermes-micro-framework/
├── install.sh                 # 一键部署（新装全量 / 存量补充 / --profile）
├── README.md                  # 开发者文档
├── LICENSE
├── TROUBLESHOOTING.md         # 故障排查指南
│
├── SOUL.md                    # → ~/.hermes/SOUL.md（存量不覆盖）
├── .env.example               # → ~/.hermes/.env（如果不存在）
│
├── memories/
│   ├── USER.md                # 用户画像模板（存量不覆盖）
│   └── FRAMEWORK_EVOLUTION.md # 框架演进钩子文件
│
├── vdb/                       # 技能检索工具链
│   ├── sparse.py              # 词法权重（纯 Python）
│   ├── embed.py               # SiliconFlow BGE-M3 云端嵌入
│   ├── indexer.py             # Chroma 索引构建
│   ├── matcher.py             # RRF(K=60) + trigger 加法加成(+0.010) 混合检索
│   └── __init__.py
│
├── scripts/
│   ├── init-vdb.sh            # .venv + pip + build_index
│   └── vdb-autoload.py        # 预热 + 索引过期检测 + 自动重建
│
└── skills/                    # 元数据资产（全量同步本地真实结构）
    ├── core/                  # 铁律细则
    ├── workflow/              # 高频工作流
    ├── methodology/           # 思维框架
    ├── infrastructure/        # 框架机制
    ├── integration/           # 外部集成
    ├── media/ research/ mlops/ smart-home/ social-media/ email/ apple/
    │   ...                    # 外部吸收的领域技能（按主题目录）
    └── templates/             # NEW_SKILL_TEMPLATE.md
```

**分类职责：**

| 分类 | 加载特点 | Token |
|------|---------|-------|
| `core/` | 检测到铁律违规时触发对应微技能 | 150-200 |
| `workflow/` | 用户触发场景关键词时加载 | 400-800 |
| `methodology/` | vdb 语义匹配或用户明确要求 | 300-600 |
| `infrastructure/` | 框架故障排查时低频加载 | 300-600 |
| `integration/` | 涉及外部系统交互时加载 | 400-800 |
| `templates/` | 创建新技能时人工查阅 | — |

---

## 源文件映射

| Repo 路径 | ~/.hermes/ 目标 | 备注 |
|-----------|----------------|------|
| `SOUL.md` | `~/.hermes/SOUL.md` | 存量用户不自动覆盖 |
| `memories/USER.md` | `~/.hermes/memories/USER.md` | 模板，存量不覆盖 |
| `.env.example` | `~/.hermes/.env` | 仅当目标不存在时复制 |
| `vdb/*.py` | `~/.hermes/vdb/*.py` | 安全覆盖 |
| `scripts/init-vdb.sh` | `~/.hermes/scripts/init-vdb.sh` | 全量覆盖 |
| `skills/*` | `~/.hermes/skills/` | 存量只补充不覆盖 |

**不发布：**
- `~/.hermes/memories/MEMORY.md`（隐私）
- 任何含个人路径、用户名、token、hostname 的内容

---

## Workflow

### Step 1: 确定变更范围

| 变更类型 | 影响范围 |
|----------|---------|
| 新增 skill | SOUL.md 路由表 + skills/ + README.md |
| 修改 SOUL.md 铁律 | SOUL.md + README.md + core/ 对应 skill |
| 修改路由表 | SOUL.md §技能路由表 |
| 框架演进变更 | FRAMEWORK_EVOLUTION.md + 对应 skill |
| 修复 bug | 对应文件 + TROUBLESHOOTING.md |

### Step 2（补充）：外部技能吸收

从外部仓库（如 addyosmani/agent-skills）吸收 skill 时：

1. 对比分析：识别重叠（吸收精华）和缺失（新增）的技能
2. 格式转换：补全 Hermes metadata（trigger ≥7, disable ≥2-3, skill_type, priority）
3. 分类放置：按 core/workflow/methodology/infrastructure/integration 放入正确目录
4. 路由表注册：SOUL.md §技能路由表 新增对应行
5. README 更新：技能全集表同步新增
6. SOUL.md 技能索引：末尾分类速览同步更新数量
7. 去重清理：原 repo 的 SVN.md 不要混入（仅吸收 SKILL.md 内容）
8. 参考文档：每次吸收建立 `references/<repo>-absorption.md` 记录范围和方法

### Step 3: 脱敏扫描 + 清洗

```bash
cd /tmp/hermes-micro-framework
# 扫描
grep -rnE "/home/[a-z]+|[HOSTNAME]|dandanlan|Hermes|hermes" \
  --include="*.md" --include="*.py" --include="*.sh" . | grep -v ".git/" || echo "CLEAN"
# 批量清洗个人标识符（仅扫描不够：历史 reference 报告含 ~、[HOSTNAME]、Hermes）
python3 - <<'PY'
from pathlib import Path
repl = [("~","~"),("[HOSTNAME]","[HOSTNAME]"),("Hermes","Hermes"),("hermes","hermes")]
for p in Path("skills").rglob("**/*.md"):
    t = p.read_text()
    for o,n in repl: t = t.replace(o,n)
    p.write_text(t)
PY
```
> 注：`dandanlan8090`（repo 路径）、`<gh-token>xx...xxxx`/`sk-xxx...xxxx`（文档占位符）是公开/示例值，非隐私，保留。
>
> ⚠️ **脱敏清单必须含「私人模型名 + 代理端点」(2026-07-15 用户抓出)** — 这是最容易漏的一类：
> - 私人搭建的模型名（如 `<main-model>`、你配的 custom provider 名）→ 替换为 `<main-model>` 或「你的模型名」。公开 repo 里出现私人模型名 = 暴露你这台代理叫什么。
> - 代理/端点 host:port（如 `<proxy-host>:6327`、`<lan-ip>`）→ 替换为 `<proxy-host>:6327`。host:port 比纯 hostname 更敏感（直接暴露可达地址）。
> - 扫描正则必须同时覆盖这两类，且**发布前用 execute_code 跑三遍迭代**（路径 → IP/host:port → 模型名），每遍修完立即复扫。
> - 误区：只 grep `~|[HOSTNAME]|token` 不算 CLEAN——私人模型名不在传统 PII 词表里，但同样是「不该出现在公开 repo 的私有标识符」。

### Step 4: 合规验证

```bash
# Frontmatter 验证（全部 skill）
python3 - <<'PY'
import pathlib, re, sys, yaml
root = pathlib.Path('/tmp/hermes-micro-framework/skills')
errors = []
for p in sorted(root.glob('**/SKILL.md')):
    text = p.read_text(encoding='utf-8')
    if not text.startswith('---'): errors.append(f'{p}: missing frontmatter')
    m = re.search(r'\n---\s*\n', text[3:])
    if not m: errors.append(f'{p}: missing frontmatter end')
    fm = yaml.safe_load(text[3:m.start()+3]) or {}
    for key in ['name','description','version','author','license','platforms']:
        if key not in fm: errors.append(f'{p}: missing {key}')
    h = (fm.get('metadata') or {}).get('hermes') or {}
    tags = h.get('tags') or {}
    if len(tags.get('trigger') or []) < 7: errors.append(f'{p}: trigger < 7')
    if len(tags.get('disable') or []) < 2: errors.append(f'{p}: disable < 2')
if errors: print('\n'.join(errors)); sys.exit(1)
print('frontmatter OK')
PY
```

### Step 5: 验证目录结构与文件完整性

```bash
# 确认关键顶层文件
ls -la SOUL.md install.sh README.md CONTRIBUTING.md LICENSE .env.example
# 确认 vdb/ 源文件（不含 chroma/ 索引、__pycache__）
ls vdb/*.py
# 确认 scripts/
ls scripts/*.sh scripts/*.py
# 确认 memories/ 模板
ls memories/USER.md memories/FRAMEWORK_EVOLUTION.md

# skills/ 数量核对（v1.0：62 个 SKILL.md，47 个顶层目录，结构为扁平+子目录混合）
echo "skills 数量: $(find skills -name 'SKILL.md' | wc -l)"
```

> skills/ 结构是**全量同步本地真实结构**（扁平 + 子目录混合：core/、workflow/、media/、research/、mlops/、smart-home/、email/ 等 47 个目录），**不重组**为固定两级分类。验证时只数 SKILL.md 总数，不校验特定分类是否存在。

### Step 6: 预览变更

```bash
cd /tmp/hermes-micro-framework
git status --short
git diff --cached --stat
```

### Step 7: Commit + Push

**先 worktree 隔离**（不要在 `~/.hermes/` 上直接 push — 它带 MEMORY.md / .env
之类隐私文件，且本地 commit 链路会污染私人备份）：

```bash
WORK=/tmp/hermes-micro-framework-publish
rm -rf "$WORK"
git clone --depth 1 https://github.com/dandanlan8090/hermes-micro-framework.git "$WORK"
cd "$WORK"
git checkout -b auto/publish-<date>
```

然后**只复制改动文件进 worktree**（不复制整个 ~/.hermes/）：

```bash
# 已脱敏的文件（按本会话 git diff --cached --name-only 列举 + 已清洗到 ~）
for f in SOUL.md .gitignore \
         skills/codebase-memory-first/SKILL.md \
         skills/codebase-memory-mcp/SKILL.md \
         skills/graphify/ skills/infrastructure/hermes-mcp-server-setup/references/graphify-mcp-setup.md \
         skills/methodology/web-tools-usage-spec/SKILL.md \
         ...; do
    cp -v "~/.hermes/$f" "$WORK/$f"
done
```

**严禁拷贝**：任何含 `~/.hermes/memories/MEMORY.md`、`.env`、`config.yaml`、
`hermes-agent/source/`、`*.db`、`skills/.usage.json`、`scripts/graphify-out/`、
`skills/graphify-out/`、`~` 个人路径的，都不入发布 worktree。

最后 commit + push：

```bash
cd "$WORK"
git add -A
git diff --cached --stat     # 预览；含个人路径或大文件立刻 abort
git commit -m "type: subject"
# Token 注入推送，推完立即还原 remote URL
git remote set-url origin "https://$(gh auth token)@github.com/dandanlan8090/hermes-micro-framework.git"
git push -u origin HEAD      # 新分支：可能 gh 提示 PR
git remote set-url origin "https://github.com/dandanlan8090/hermes-micro-framework.git"
```

---

## Iron Rule: 每次推送必须用户明确授权

**绝对禁止在用户未明确指令的情况下向 `github.com/dandanlan8090/hermes-micro-framework` 推送任何内容。**

- 每次 push 需要本轮对话中单独的、明确的指令（"推"、"push"、"发布"）
- commit ≠ push。本地 commit 完成不等于可以发 remote
- "上轮说过推"不构成当前轮的授权
- 违反 = 侵蚀用户对公开项目的可控性

---

## Common Pitfalls

1. **Blind copy SOUL.md** — 本地 SOUL.md 可能含个性化修改，发布前检查
2. **Publishing MEMORY.md** — 永远不发布
3. **skills/ 目录结构不一致** — 框架核心放 core/workflow/methodology/infrastructure/integration；外部吸收领域技能放 media/research/mlops/smart-home/social-media/email/apple 等。全量同步时**以本地 `skills/` 真实结构为准**，不要强行套固定两级分类（v1.0 实为 47 个顶层目录、62 技能，多为"分类/技能名"一对一）
4. **路由表未同步** — 新增 skill 后忘记在 SOUL.md §技能路由表 加一行
4b. **门禁未注册（重型文档类技能）** — 若新 skill 是"框架/系统说明文档"类型
   （SKILL.md > 3,000 字符，描述框架本身而非解决业务问题），必须同步在
   `vdb/routing.py` 登记门禁——否则业务 query（如"重构函数"）会经 dense
   语义相似度 + sparse 单字切分误命中、瞬间注入数千 token。
   两种登记方式任选其一：
   a) **静态**（保守）：在 `routing.py` 的 `STATIC_GATED_SKILLS` 字典加一行
      `"<skill_name>": FRAMEWORK_GATE_KEYWORDS`（或新建专属门禁词集）。
   b) **声明式**（推荐，去中心化）：在新 skill 的 SKILL.md frontmatter 里加：
      ```yaml
      metadata:
        hermes:
          gate:
            enabled: true
            keywords: [SOUL.md, 铁律, vdb, 框架专名1, ...]
      ```
      routing.py 启动时会自动扫描并注册，**默认安全**——未声明的技能永远不受门禁影响。
   门禁词必须是业务 query 不会出现的专名（SOUL.md/vdb/铁律/微内核等），
   **禁止**用裸词 "hermes"——会误伤"hermes怎么配置"等日常 query（实测证实）。
   详见 `vdb/routing.py` 模块顶部 docstring。
5. **Token 残留 remote URL** — 推完立即 `git remote set-url origin https://github.com/...`
6. **vdb 未重建** — 新增/修改 skill 后必须 `build_index(force=True)`
7. **install.sh 未适配新结构** — 如果改了 skills/ 目录结构，同步更新 install.sh
8. **外部技能未做格式转换** — 从 addyosmani/agent-skills 等外部仓库吸收技能时，需补 Hermes metadata（trigger/disable tags）并放入正确分类目录；对比分析见 `references/addyosmani-absorption.md`

**脱敏替换映射与清洗脚本**：见 `references/sanitize-patterns.md`。
9. **SOUL.md 技能索引未同步** — 全量同步 skills/ 后，SOUL.md 末尾 §技能索引（数量+列表）必须同步到实际技能数（v1.0=62）。skills/ 才是元数据真源，索引描述必须与之一致
10. **铁律#0 加固后 README 未更新** — 修改铁律#0 触发条件后需同步更新 README.md 的铁律说明表
11. **脱敏只扫不换** — 仅 grep 扫描不够，历史 reference 报告（如 `agent-collaboration-workflow/references/*.md`）含 `~`、`[HOSTNAME]`、`Hermes` 需批量替换。替换映射见 Step 3 的清洗脚本
12. **execute_code 批量改 frontmatter 把内容写到 `---` 关闭符之外** — 用 execute_code 字符串拼接插入 trigger/disable 时，若插入位置计算错，新行会落在 body 而非 frontmatter 内 → YAML 解析仍是旧值。symptom：`_get_collection()` 读到旧 trigger 数、grep frontmatter 看不到新 trigger。fix：批量改完立即用 `yaml.safe_load(text.split('---')[1])` 校验 frontmatter 内 trigger 数是否真增加；不一致就改用 `patch` 工具逐文件精确替换 trigger 段。优先用 `patch` 工具而非 execute_code 做 frontmatter 编辑
13. **install.sh 的 bash 布尔变量误用（2026-07-12 实测必崩）** — `if $IS_NEW` / `if $DRY` 把字符串 `"true"`/`"false"` 当命令执行：`if $DRY`（DRY="false"）执行 `false` 命令返回 0 → 永远进 DRY 分支然后 `return`，导致零文件复制、脚本静默退出（只看到某步标题，实际更早步骤已因 set -e 退出）。fix：一律写 `if [ "$IS_NEW" = true ]`、`if [ "$DRY" = true ]`。复现与修法见 `references/install-sh-pitfalls.md`。
14. **`set -e` 在非原子安装脚本中过脆** — 任何非致命命令（cp 已存在文件、find|wc 在 pipefail 下）失败即全退，输出缓冲让你只看到某步标题、实际更早的步骤已崩。fix：去掉 `set -e`（保留 `set -u`），do_cp 用 `cp -rn` 防冲突；或关键步骤加 `|| true`。
15. **`REPO_DIR` 用 `cd "$(dirname "$0")"` 依赖调用时 cwd** — `$0` 为相对路径 `install.sh` 时 `dirname` 得 `.`，若调用前 cwd 非仓库根则 REPO_DIR 错（实测报 `cannot stat '/tmp/.env.example'`）。fix：`SCRIPT_PATH="$(readlink -f "$0" 2>/dev/null || realpath "$0")"; REPO_DIR="$(cd "$(dirname "$SCRIPT_PATH")" && pwd)"`。
16. **测试写 ~/.hermes 的脚本必须用真实 profile，禁止 `HOME=/tmp/xxx` 模拟**（用户 2026-07-12 明确纠正："你的模拟方案本身存在差异化，你可以新建profile测试，完成后删除就行了，而不是额外目录"）。
    - 假 HOME 引入路径假设偏差：REPO_DIR 解析、`--profile` 检测、profile 目录判断都依赖真实 HOME 结构，测出的"bug"可能是模拟本身造成的而非真 bug（本会话正是因此误判了 install.sh 的 REPO_DIR 问题）。
    - 正确做法：`bash install.sh --profile installtest` → 装到 `~/.hermes/profiles/installtest/` → 验证完 `rm -rf ~/.hermes/profiles/installtest`。零污染、零路径偏差。
    - 通用原则：任何写 `~/.hermes/` 的脚本（install.sh / init-vdb.sh / vdb-autoload.py 等）的安全测试都适用此纪律。
    - 调试 install.sh 的实战复现与逐层定位命令见 `references/install-sh-debugging.md`。
17. **patch 编号 markdown 列表引发重编号级联（2026-07-13 实测踩过，3 次才修对）** — 用 `patch` 往有序列表（如本节 Common Pitfalls）中间插一条时，若 `old_string` 只匹配「插入点那一行」，patch 会把新内容插在其后、**但不会自动重排后续编号** → 出现重复编号（本会话插门禁条目后出现两个 `5.`、两个 `8.`）。逐个 renumber 又会撞上文件下方已存在的同号项，越改越乱。
    - **首选修法**：用字母后缀插入（如在 `4.` 后插 `4b.`），完全不触动后续编号序列——最小侵入，一次到位。
    - **次选修法**：若必须用纯数字，`old_string` 要**连续包含插入点到下一个稳定锚点之间的所有编号行**，在 `new_string` 里一次性重排全部受影响编号，避免分次 patch 撞号。
    - 通用原则：改有序/自动编号结构（markdown 列表、脚注、步骤号）时，先想「会不会扰动后续序号」，能用非编号锚点（字母后缀/子项）就别动主序号。
18. **用户贴代码字面 vs 改写（2026-07-14 实测踩过，安全护栏拦下）** — 用户给的快速 template（如"P0-1 在项目根添加 .graphifyrc.json + npm pkg set"）常常基于一个**与你环境不同的生态**（今天的事件：graphify 是 Python PyPI 包，不是 Node CLI，**npm 不存在**、也没有 `.graphifyrc.json` 这种 INI 文件格式）。
    - **误读征兆**：处理这类「立即执行」型指令，若代码是 Node/npm/Cargo/Composer 等与你环境不匹配的语言，初次尝试会被 Hermes 的"高危/错误路径检测"拦下；或者跑完后产生垃圾文件。建议先核对生态匹配再下手。
    - **首选做法**：扔掉生态隐含假设（Node 包管=JS；pyproject.toml=Python；graphify 系列=Python；lark-cli / larkty-* 一律=Go+binary），把"本质动作"抽出来用**对应生态的等效形态**落地；落地前给用户 show diff preview，请其确认后再写入。
    - **次优做法**：直接照搬但用户能接受执行结果无效——任何"新建配置文件 + 中文路径 + 与本机语言栈不匹配"几乎一定是占位无效的，不要接受。
    - 与**铁律#1 信息真实性**配合：发现前提假设与现状不符时**先声称**问题、不要带"先作、为后面 success 报告打过去"——会产生用户原话"抱歉刚才走开、重新授权"的反复拉锯。

19. **两个独立 git 历史树 → 不要硬 merge/rebase，归档旧库重建最干净（2026-07-15 实测+用户决策）** — 本机 `~/.hermes` 是手动 `git init` 起的本地备份仓，GitHub `origin/main` 是另一条独立历史（root commit 不同）。`git push` 会报 non-fast-forward（两边差 ~10 commit）。选项：
    - ❌ `git rebase origin/main` → 改写本机历史，force-push 后 GitHub 上所有 SHA 都变，等于重塑历史，且仍要 force。
    - ❌ `git merge origin/main` → 产生跨期 merge commit，公开 repo 历史脏。
    - ✅ **用户决策：归档旧库 + 建新库一步到位** — `gh repo rename <old> -R <owner>/<old> --yes` 归档旧库（保留可查），`gh repo create <new> --public` 建空库，然后 `git remote add publish <new-url>` + `git push publish main`。无冲突、无历史纠缠、一步到位。
    - **判断原则**：当本地仓和远程仓 root commit 不同（不是同一 ancestor 派生），就是两个独立项目历史，merge/rebase 都会造垃圾——直接归档重建比费力调和更干净。
    - 注意：本机 `~/.hermes` 的 git 默认**无 remote**（纯本地备份模式），首次 push 需先 `git remote add`。

---

## Verification Checklist

- [ ] 用户在本轮明确说"推"/"push"
- [ ] 脱敏扫描无个人路径/hostname/token（注意 `**/*.md` 全递归，`.` 或 `ls` 可能漏深层文件）
- [ ] 所有 skill frontmatter 合规（trigger ≥7, disable ≥2）
- [ ] SOUL.md 路由表与 skills/ 目录一致
- [ ] SOUL.md 末尾技能索引（数量+列表）已同步
- [ ] README.md 已同步更新（技能列表、目录结构、铁律说明）
- [ ] install.sh 已适配（如果改了目录结构）
- [ ] vdb 已重建（`build_index(force=True)`）
- [ ] Git remote 不含 token
- [ ] `git log --oneline -1` 确认预期 commit
