---
name: hermes-agent-skill-authoring
description: 'Author in-repo and user-local SKILL.md: frontmatter, validator, structure,
  writing-quality principles, craft methodology (leading words, failure modes, progressive disclosure).'
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
      - 写技能
      - skill开发
      - hermes技能
      - 创建skill
      - 创建技能
      - 技能创建
      - skill authoring
      - 创建新规则
      - 新增约束
      - 写SKILL.md
      - 技能模板
      - NEW_SKILL_TEMPLATE
      - skill规范
      disable:
      - cli_only
      - read_only
      - 普通任务
    related_skills:
    - plan
    - requesting-code-review
---
# Authoring Hermes-Agent Skills (in-repo)

## Overview

There are two places a SKILL.md can live:

1. **User-local:** `~/.hermes/skills/<maybe-category>/<name>/SKILL.md` — personal, not shared. Created via `skill_manage(action='create')`.
2. **In-repo (this skill is about this case):** `/home/bb/hermes-agent/skills/<category>/<name>/SKILL.md` — committed, shipped with the package. Use `write_file` + `git add`. `skill_manage(action='create')` does NOT target this tree.

## When to Use

- User asks you to add a skill "in this branch / repo / commit"
- You're committing a reusable workflow that should ship with hermes-agent
- You're editing an existing skill under `/home/bb/hermes-agent/skills/` (use `patch` for small edits, `write_file` for rewrites; `skill_manage` still works for patch on in-repo skills, but not for `create`)

## Required Frontmatter

Source of truth: `tools/skill_manager_tool.py::_validate_frontmatter`. Hard requirements:

- Starts with `---` as the first bytes (no leading blank line).
- Closes with `\n---\n` before the body.
- Parses as a YAML mapping.
- `name` field present.
- `description` field present, ≤ **1024 chars** (`MAX_DESCRIPTION_LENGTH`).
- Non-empty body after the closing `---`.

Peer-matched shape used by every skill under `skills/software-development/`:

```yaml
---
name: my-skill-name               # lowercase, hyphens, ≤64 chars (MAX_NAME_LENGTH)
description: Use when <trigger>. <one-line behavior>.
version: 1.1.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [short, descriptive, tags]
    related_skills: [other-skill, another-skill]
---
```

`version` / `author` / `license` / `metadata` are NOT enforced by the validator, but every peer has them — omit and your skill sticks out.

## Size Limits

- Description: ≤ 1024 chars (enforced).
- Full SKILL.md: ≤ 100,000 chars (enforced as `MAX_SKILL_CONTENT_CHARS`, ~36k tokens).
- Peer skills in `software-development/` sit at **8-14k chars**. Aim for that range. If you're pushing past 20k, split into `references/*.md` and reference them from SKILL.md.

## Writing Quality Principles

A skill exists to make the agent's process more predictable. Predictability does **not** mean identical output every run; it means the agent reliably follows the same useful discipline.

Use these quality checks when writing or editing any skill:

1. **Optimize for process predictability.** Ask: what behavior should change when this skill loads? If a line does not change behavior, cut it.
2. **Choose the right context load.** A model-invoked Hermes skill pays for its description every turn. Keep descriptions focused on trigger classes and the skill's distinctive behavior. Put details in the body or linked references.
3. **Use an information hierarchy.** Put always-needed steps in `SKILL.md`; put branch-specific or bulky reference material in `references/`, `templates/`, or `scripts/` and point to it only when needed.
4. **End steps with completion criteria.** Each ordered step should say how the agent knows it is done. Good criteria are checkable and, when it matters, exhaustive: "every modified file accounted for" beats "summarize changes."
5. **Co-locate rules with the concept they govern.** Avoid scattering one idea across the file. Keep definition, caveats, examples, and verification near each other.
6. **Use strong leading words.** Prefer compact concepts the model already knows — e.g. "tight loop," "tracer bullet," "root cause," "regression test" — over long repeated explanations. A good leading word saves tokens and anchors behavior.
7. **Prune duplication and no-ops.** Keep each meaning in one source of truth. Sentence by sentence, ask whether the sentence changes agent behavior versus the default. If not, delete it rather than polishing it.
8. **Watch for premature completion.** If agents tend to rush a step, first sharpen that step's completion criterion. Split the sequence only when later steps distract from doing the current step well.

Common quality failures:

- **Premature completion** — the skill lets the agent move on before the work is genuinely done.
- **Duplication** — the same rule appears in multiple places and drifts.
- **Sediment** — stale lines remain because adding felt safer than deleting.
- **Sprawl** — too much always-visible material; push branch-specific reference behind pointers.
- **No-op prose** — generic advice the agent would already follow without the skill.

## Skill Writing Methodology (Craft)

The following methodology section complements the mechanical procedure above. It covers the *craft* of writing — what makes a skill effective, how to structure it for an LLM reader, and which failure modes to guard against.

### Description 三段式

The `description` field is the only text always loaded. Write it in three parts:

```
前 30 字符：{leading word} + 触发场景条件
中间 60 字符：核心动作 + 产出
末尾：分支条件（"Use when X / Use when Y"）+ 禁用场景（"禁用：Z"）
```

Example:
```
description: "Root-Cause：交互式调试与根因排查。Use when 报错/异常/traceback/服务不可用。禁用：纯配置变更/仅查看日志"
```

Leading word guide: pick a compact concept the model already knows (`tracer bullet`, `root cause`, `gate`, `dispatch`, `tight loop`). A strong leading word saves tokens and anchors behavior better than 10 sentences of explanation.

### SKILL.md 四段式

```
# 标题 (leading word)

## 第一性原理 (First Principles)
3-5 条，每条一行：定义 + 为什么重要 + 怎么识别违反

## 工作流 (Workflow)
编号步骤，每步一个 completion criterion（可验证）

## 规则 (Rules)
- 约束条件
- 禁用场景
- 常用命令模板

## 失败模式 (Failure Modes)
每个一行：tell（怎么识别）+ fix（怎么修）
```

### 九种常见失败模式

在写任何 skill 时，对照审查初稿：

| 模式 | tell（怎么识别） | fix（怎么修） |
|------|-----------------|-------------|
| **Premature Completion** | agent 在一个消息里完成了多个步骤；跳过命令直接说结果 | 加固 completion criterion；分割步骤到独立文件 |
| **Embargo** | agent 发现了重要信息但没有在恰当的时机披露 | 加 escape valve："顺序决定展示，不决定披露" |
| **Lucky Pass** | 验证通过只因世界或用户恰好在正确时间输入了关键信息 | 把 eliciting probe 编码为显式步骤 |
| **Duplication** | 同一含义出现在两处 | 合并到一个 source of truth |
| **Sediment** | 旧规则积累，新加不删旧 | 加新规则时找旧等价规则删除 |
| **War Story** | 例子写的是"我们当时改了 X 和 Y 参数"——值/某次修复的流水账 | 删具体值，只写 smell（怎么识别）+ signal（怎么确认） |
| **Implementation Index** | skill 指着今天源码的特定行号/函数名 | 删行号，让 agent grep 找当前 owner |
| **Sprawl** | SKILL.md 超过 100 行（不含 frontmatter） | 推 references/ scripts/ templates/ |
| **No-op** | "be thorough" / "be careful" / "使用最佳实践" | 全句删 |

### Leading Word 选用原则

1. 从模型已有概念库中选（如 "root cause"、"tracer bullet"、"regression"）
2. 不在前 30 字符 = 选错了位置，不是选错了词
3. 自定义新词必须注册到 SOUL.md §词汇库

### 编写原则

- **教问题，不教答案**：例子里写 smell + signal，不写"我们改了 X 和 Y"
- **渐进披露**：SKILL.md 只放必须始终可见的内容；分支/例子/长 schema 推 references/
- **< 100 行原则**：SKILL.md 超 100 行（不含 frontmatter）必须拆
- **改进优先于新增**：加新规则前，找旧等价规则删掉

## Peer-Matched Structure

Every in-repo skill follows roughly:

```
# <Title>

## Overview
One or two paragraphs: what and why.

## When to Use
- Bulleted triggers
- "Don't use for:" counter-triggers

## <Topic sections specific to the skill>
- Quick-reference tables are common
- Code blocks with exact commands
- Hermes-specific recipes (tests via scripts/run_tests.sh, ui-tui paths, etc.)

## Common Pitfalls
Numbered list of mistakes and their fixes.

## Verification Checklist
- [ ] Checkbox list of post-action verifications

## One-Shot Recipes (optional)
Named scenarios → concrete command sequences.
```

Not every section is mandatory, but `Overview` + `When to Use` + actionable body + pitfalls are the minimum for the skill to feel like a peer.

## Directory Placement

```
skills/<category>/<skill-name>/SKILL.md
```

Categories currently in repo (confirm with `ls skills/`): `autonomous-ai-agents`, `creative`, `data-science`, `devops`, `dogfood`, `email`, `gaming`, `github`, `leisure`, `mcp`, `media`, `mlops/*`, `note-taking`, `productivity`, `red-teaming`, `research`, `smart-home`, `social-media`, `software-development`.

Pick the closest existing category. Don't invent new top-level categories casually.

## 召回质量约束 (vdb recall)

Hermes 的技能检索是 **dense(BGE-M3 1024d) + sparse(IDF 增强) RRF 融合**。新技能不进索引 = 永不被召回；trigger/disable 写错 = 误召或漏召。创建/安装技能时必须遵守：

1. **trigger_tags ≥ 7 条**，全部用高频自然语言（模拟用户口语 query），不要写技能内部概念词。
   - 好：`["调试代码","报错排查","bug修复","程序崩溃","代码跑不起来"]`
   - 差：`["debugging","error-handling"]`（纯英文/内部词，中文口语 query 命中率低）
2. **disable_tags 必填**，至少 2-3 条，写"容易误召本技能、但实际该走别处"的 query 子串。
   - 例：debugging-patterns disable `["代码bug调试","性能优化","新功能开发"]`（这些是 fault/system-admin/shipping 的地盘）
   - 匹配逻辑：`disable in query`（禁用词是 query 子串则过滤），所以写"短语级"比"单字"更准。
3. **中文 description 优先**：纯英文 desc 无法进入 sparse 中文短语索引（提取正则 `[\u4e00-\u9fff]{2,}`），降低中文 query 召回。能写中文就写中文。
4. **创建/修改后必须重建索引**：`build_index` 扫描 `skills/` 全量重编。新技能/新 trigger 不重建 = 检索不到。
   - 开发期：`cd ~/.hermes/vdb && source .venv/bin/activate && python3 -c "from indexer import build_index; build_index(force=True)"`
   - 安装/开机：`python3 ~/.hermes/scripts/vdb-autoload.py --auto`（哈希检测 skills 列表，过期自动重建）
5. **边界认知（勿死磕元数据）**：dense embedding 足够强时，sparse/trigger/disable 的边际贡献趋零。若某 query 总被 dense 语义偏差抢走（如"同步配置"→source-driven、"changelog"→git-worktree），这是 BGE-M3 的天花板，不是元数据能解——除非换 embedding 模型或做 dense 侧 domain fine-tune。不要在元数据层面反复调参。

> 📌 完整写法规范 + 边界 case 表 + 自检清单：见 `autoload-vdb/references/METADATA_GUIDE.md`（本段是其流程钩子，该文件是规范源）。

## Workflow

1. **Survey peers** in the target category:
   ```
   ls skills/<category>/
   ```
   Read 2-3 peer SKILL.md files to match tone and structure.
2. **Check validator constraints** in `tools/skill_manager_tool.py` if unsure.
3. **Draft** with `write_file` to `skills/<category>/<name>/SKILL.md`.
4. **Validate locally**:
   ```python
   import yaml, re, pathlib
   content = pathlib.Path("skills/<category>/<name>/SKILL.md").read_text()
   assert content.startswith("---")
   m = re.search(r'\n---\s*\n', content[3:])
   fm = yaml.safe_load(content[3:m.start()+3])
   assert "name" in fm and "description" in fm
   assert len(fm["description"]) <= 1024
   assert len(content) <= 100_000
   ```
5. **Git add + commit** on the active branch.
6. **Note:** the CURRENT session's skill loader is cached — `skill_view` / `skills_list` will not see the new skill until a new session. This is expected, not a bug.
7. **Rebuild the vdb index** so the new skill is recallable (see 召回质量约束 #4):
   ```bash
   cd ~/.hermes/vdb && source .venv/bin/activate && python3 -c "from indexer import build_index; build_index(force=True)"
   ```
   Skip if you only edited a `references/` file that doesn't change trigger/disable/description. Run `python3 ~/.hermes/scripts/vdb-autoload.py --check` afterwards to confirm "索引最新".

## Cross-Referencing Other Skills

`metadata.hermes.related_skills` unions both trees (`skills/` in-repo and `~/.hermes/skills/`) at load time. You CAN reference a user-local skill from an in-repo skill, but it won't resolve for other users who clone the repo fresh. Prefer referencing only in-repo skills from in-repo skills. If a frequently-referenced skill lives only in `~/.hermes/skills/`, consider promoting it to the repo.

## Editing Existing In-Repo Skills

- **Small fix (typo, added pitfall, tightened trigger):** `skill_manage(action='patch', name=..., old_string=..., new_string=...)` works fine on in-repo skills.
- **Major rewrite:** `write_file` the whole SKILL.md. `skill_manage(action='edit')` also works but requires supplying the full new content.
- **Adding supporting files:** `write_file` to `skills/<category>/<name>/references/<file>.md`, `templates/<file>`, or `scripts/<file>`. `skill_manage(action='write_file')` also works and enforces the references/templates/scripts/assets subdir allowlist.
- **Always commit** the edit — in-repo skills are source, not runtime state.

## Common Pitfalls

1. **Using `skill_manage(action='create')` for an in-repo skill.** It writes to `~/.hermes/skills/`, not the repo tree. Use `write_file` for in-repo creation.

2. **Leading whitespace before `---`.** The validator checks `content.startswith("---")`; any leading blank line or BOM fails validation.

3. **Description too generic.** Peer descriptions start with "Use when ..." and describe the *trigger class*, not the one task. "Use when debugging X" > "Debug X".

4. **Forgetting the author/license/metadata block.** Not validator-enforced, but every peer has it; omitting makes the skill look half-finished.

5. **Writing a skill that duplicates a peer.** Before creating, `ls skills/<category>/` and open 2-3 peers. Prefer extending an existing skill to creating a narrow sibling.

6. **Expecting the current session to see the new skill.** It won't. The skill loader is initialized at session start. Verify in a fresh session or via `skill_view` using the exact path.

7. **Letting skills accumulate sediment.** A skill should get shorter or sharper over time. When adding a rule, remove the old wording it replaces; don't layer advice forever.

8. **Writing no-op prose.** "Be careful," "be thorough," and "use best practices" rarely change model behavior. Replace with a checkable completion criterion or a stronger leading word.

9. **Linking to skills that don't exist in-repo.** `related_skills: [some-user-local-skill]` works for you but breaks for other clones. Prefer only in-repo links.

## Verification Checklist

- [ ] File is at `skills/<category>/<name>/SKILL.md` (not in `~/.hermes/skills/`)
- [ ] Frontmatter starts at byte 0 with `---`, closes with `\n---\n`
- [ ] `name`, `description`, `version`, `author`, `license`, `metadata.hermes.{tags, related_skills}` all present
- [ ] Name ≤ 64 chars, lowercase + hyphens
- [ ] Description ≤ 1024 chars and starts with "Use when ..."
- [ ] Total file ≤ 100,000 chars (aim for 8-15k)
- [ ] Structure: `# Title` → `## Overview` → `## When to Use` → body → `## Common Pitfalls` → `## Verification Checklist`
- [ ] Each ordered step has a checkable completion criterion
- [ ] Description is trigger-focused and avoids duplicated body content
- [ ] Bulky or branch-specific reference is progressively disclosed in linked files
- [ ] No-op prose and duplicated rules removed
- [ ] `related_skills` references resolve in-repo (or are explicitly OK to be user-local)
- [ ] `git add skills/<category>/<name>/ && git commit` completed on the intended branch
- [ ] **召回质量**：trigger_tags ≥ 7 条，全为高频自然语言（非内部概念词）
- [ ] **召回质量**：disable_tags 必填，覆盖易误召本技能的 phrase-level query
- [ ] **召回质量**：description 含中文（或确认英文 desc 的 sparse 中文覆盖率可接受）
- [ ] **召回质量**：已执行 `build_index(force=True)` 重建索引，或确认本次改动不影响 trigger/disable/desc
- [ ] 运行 `python3 ~/.hermes/scripts/vdb-autoload.py --check` 确认 "索引最新"
