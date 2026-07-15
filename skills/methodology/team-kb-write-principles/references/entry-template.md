# 团队知识库 · 知识条目模板

> 设计原则：Hermes 自身即模板。每条知识 = 一个 mini-SKILL（结构化条目）+ 一条 MEMORY 存档纪律。
> skills 提供"可召回、带触发/禁用、有版本"的结构；memory 提供"带 verified_on、失效条件、可纠正"的时效护栏。
> 本模板是 `team-kb-write-principles` 的落地骨架，所有知识条目统一套用，防结构漂移。

---

## 一、条目头部（frontmatter 区，必填）

仿照 SKILL.md frontmatter，保证"可检索 + 可治理 + 可溯源"：

```yaml
---
id: kb-<分类>-<短名>          # 唯一标识，如 kb-lark-cli-config-bind
title: 知识条目标题
category: <分类>              # 与知识库节点树对齐，不新建顶层分类
author: <作者/签名>           # 初版作者 + 落日期
version: 1.0.0                # 语义版本，修改递增
verified_on: YYYY-MM-DD       # 上次确认为真日期（memory 纪律：时效护栏）
expires_when: <什么变化使其作废>   # 失效条件，必填
confidence: verified | documented | hearsay   # 置信度三级（team-kb 闸门）
scope:                        # 适配性闸门：部分知识仅限特定设备/环境
  source_device: <cm211电视盒 / x86 [HOSTNAME] / 飞书国内端点 / ...>
  env: <LAN内网 / 公网 / 特定OS版本 / ...>
trigger_tags:                # 检索触发词（仿 skill，≥7 条高频自然语言）
  - <用户口语 query 1>
  - <用户口语 query 2>
disable_tags:                # 易误召本条目、应走别处的 query（≥2 条）
  - <易混淆 query A>
---
```

## 二、正文结构（四段式，仿 SKILL.md）

```markdown
# <标题> (leading word)

## 第一性原理
3-5 条：定义 + 为什么重要 + 怎么识别违反。

## 工作流 / 操作步骤
编号步骤，每步带可验证的 completion criterion。
（事实类条目可改为"结论 + 验证方式"）

## 规则 / 约束
- 约束条件
- 禁用场景
- 常用命令模板（附实测输出或来源链接）

## 失败模式
每个一行：tell（怎么识别）+ fix（怎么修）
```

## 三、时效与真实性护栏（来自 memory 存档纪律）

- **编辑前备份**：改动既有条目前 `cp -p <file> <file>.bak.<日期>`（防不可恢复丢失）。
- **verified_on 必填**：每条易变事实标 `verified_on=YYYY-MM-DD` + `时效敏感: <漂移原因>; <重验触发>`。
- **过期即纠正**：发现错误/过时，立即改写为"已纠正+已验证"，**不留"待执行"标记**（陈旧记忆比没有更糟）。
- **记忆非真理**：对易变事实采取行动前，先对实时状态重验（truth-redline 延伸）。
- **改后验证**：读回/跑验证命令确认落地，相邻行未被破坏。

## 四、变更记录表（必附，签名追溯）

| 日期 | 修改人 | 版本 | 变更说明 |
|------|--------|------|----------|
| YYYY-MM-DD | <作者签名> | 1.0.0 | 初版落地 |
| YYYY-MM-DD | <修改者签名> | 1.1.0 | 追加 X；纠正 Y（原 Y 因 Z 已失效） |

> 维护约定：任何修改追加一行，不覆盖历史。修改者遵循同一四闸门与 scope 标注。

## 五、反例（踩坑警示）

❌ 缺 scope 的泛化：
> "lark-cli 用 config bind 即可"
> —— 飞书国际端点/旧版 CLI 可能不成立，且无时效、无来源。

✅ 合规条目（scope + verified_on + 来源）：
> "lark-cli 用 `config bind --source hermes --identity user-default`（飞书国内端点, verified_on=2026-07-11；升级飞书/lark-cli 须重验）。来源：实测 `lark-cli auth status` + config bind 流程。"

---

落地日期：2026-07-11 ｜ 作者：Hermes（AI Agent）｜ 本模板遵循 `team-kb-write-principles` 四闸门与 scope 纪律。
