# Contributing

本仓库是 Hermes Agent 微内核架构的配置模板。贡献遵循以下规范。

## 提交规范

- `type: subject` 格式，type ∈ {feat, fix, docs, refactor, chore, diag}
- subject 用中文或英文，简洁描述变更
- 重大变更在 body 说明「为什么」

## Skill 贡献要求

新增/修改 `skills/` 下的技能必须满足：

1. **Frontmatter 合规**
   - 必备顶层字段：`name` / `description` / `version` / `author` / `license` / `platforms`
   - `metadata.hermes.tags.trigger` ≥ 7 个（含中文）
   - `metadata.hermes.tags.disable` ≥ 2 个

2. **路由表同步**
   - 新增 skill 后，在 `SOUL.md` §技能路由表加一行
   - 如果 skill 是框架/系统说明文档类型（SKILL.md > 3000 字符），必须在 `vdb/routing.py` 登记门禁（防业务 query 误注入）

3. **目录分类**
   - 核心机制 → `core/` / `infrastructure/`
   - 工作流 → `workflow/`
   - 思维框架 → `methodology/`
   - 外部集成 → `integration/`
   - 外部吸收领域技能 → `media/` `research/` `mlops/` `smart-home/` `social-media/` `email/` `apple/`
   - **全量同步本地真实结构**，不强行套固定两级分类

## 脱敏红线（必查）

提交前必须确认无以下泄漏：

- 个人路径（`/home/<user>/`）
- hostname（`fnubuntu` 等）
- IP / host:port（`149.88.x.x`、`192.168.x.x`）
- 私人模型名（`vps-chat` 等 custom provider 名）
- API key / token（`sk-xxxx`、`ghp_xxxx`）

清洗映射：

| 原值 | 替换 |
|------|------|
| `/home/lan` | `~` |
| `fnubuntu` | `[HOSTNAME]` |
| `149.88.88.236:6327` | `<proxy-host>:6327` |
| `vps-chat` | `<main-model>` |
| `sk-xxxx` / `ghp_xxxx` | `<api-key>` / `<gh-token>` |

`dandanlan8090`（repo 路径）、`<api-key>` 等占位符是公开/示例值，可保留。

## 验证清单

- [ ] `python3` frontmatter 校验脚本通过（trigger ≥7, disable ≥2）
- [ ] 脱敏扫描无个人标识符
- [ ] `SOUL.md` 路由表与 `skills/` 目录一致
- [ ] `vdb` 已重建（`build_index(force=True)`）
- [ ] 不涉及 `~/.hermes/memories/MEMORY.md` 等隐私文件
