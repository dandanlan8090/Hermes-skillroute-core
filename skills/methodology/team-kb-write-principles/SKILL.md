---
name: team-kb-write-principles
description: '团队知识库写入与存入原则：入库前四道闸门（环境时效/适配性/真实性/正确性）与 scope 标注纪律。Use when 往知识库写文档/整理团队知识/沉淀经验/统一知识源。禁用：纯个人笔记/一次性查询/格式整理(走 hermes-knowledge-base)'
version: 1.0.0
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
      - 团队知识库
      - 知识库写入
      - 知识入库
      - 沉淀经验
      - 写知识文档
      - 整理团队知识
      - 知识统一管理
      - 团队经验沉淀
      - 知识库规范
      - 存入知识库
      disable:
      - 知识库格式
      - markdown笔记
      - 个人笔记整理
      - 文档归档格式
      - 知识检索评估
      - aaak格式
    related_skills:
    - hermes-knowledge-base
    - hermes-memory-archiving
    - hermes-truth-redline
---

# 团队知识库写入与存入原则

## 第一性原理

团队知识库的价值 = 可被信任地复用。一旦混入过期/虚假/错配环境的知识，复用反成风险源。

四条不可妥协的入库闸门（任一不过 = 不入库）：

1. **环境&时效**：知识有生命周期。不带时间戳与失效条件的知识 = 定时炸弹。
2. **适配性**：同一结论在不同环境（ARM 电视盒 / x86 VM / 飞书国内端点）可能完全不成立。
3. **真实性**：来源可溯、可重验。无出处 = 无信任。
4. **正确性**：经实测或官方文档佐证，非脑补"看起来对"。

## 设计哲学：Hermes 即模板（用户 2026-07-11 明确方向）
团队知识库不是外部 KB 工具的翻版，而是 **Hermes 自身知识架构的团队化复制**：
- **skills 本身是微型知识库**：每条知识 = 一个 mini-SKILL（frontmatter 触发/禁用/版本/作者 + 四段式正文 + 渐进披露）。
- **memory 存档提供时效护栏**：verified_on / 失效条件 / 编辑前备份 / 过期即纠正（见 `hermes-memory-archiving`）。
- **skills + memory = 本 Agent 的全部知识**，团队 KB 直接复用这一结构，而非另起炉灶或套外部工具。
- 外部工具（如 LightRAG）只作检索引擎垫底，知识模型以 Hermes 结构为准。
- 起步阶段勿过度工程化（离线镜像/同步冗余层等），先立纪律，能力到边界再谈冗余。

## 核心纪律：scope 标注（最关键）

**部分知识仅限特定设备/环境通用，不可盲目泛化。**

每条入库知识必须携带 provenance / scope 标签：

```
来源设备:    cm211电视盒 / x86 [HOSTNAME] / 飞书国内端点 / ...
适用环境:    LAN内网 / 公网 / 特定OS版本 / ...
有效期:      verified_on=YYYY-MM-DD; 失效条件=<什么变化使其作废>
置信度:      verified(实测) | documented(官方) | hearsay(待验)
```

反例："lark-cli 用 config bind" —— 缺 scope，飞书国际端点/旧版 CLI 可能不成立。
正例："lark-cli 用 config bind --source hermes（飞书国内端点, verified_on=2026-07-11；升级飞书/lark-cli 须重验）"。

## 工作流（写入前必过四闸门）

1. **识别 scope**：这条知识在哪台设备/环境跑出来的？写进标签。→ 完成标准：scope 四字段齐全。
2. **验证真实性**：出处是否可查？能否现在重验一次？→ 完成标准：附可访问来源或实测命令+输出。
3. **验证正确性**：实测/官方文档，还是推断？推断须标 `hearsay` 并注明待验。→ 完成标准：每条标 verified/documented/hearsay。
4. **标注时效**：何时有意义？何时作废？→ 完成标准：带 `verified_on` + 失效条件。
5. **评估适配性**：是否隐含"通用"假设？跨设备是否成立？→ 完成标准：非全环境通用则 scope 已显式收窄。
6. **入库**：按知识库既有结构落位（格式/组织见 `hermes-knowledge-base`），不另创结构。

## 禁用场景

- 纯个人临时笔记（走 `~/.hermes/memories/` 或会话记忆）
- 一次性查询答案（不沉淀）
- 仅是格式整理（Markdown/AAAK 排版 → 走 `hermes-knowledge-base`）
- 框架未成熟时的过度工程化（如离线镜像兜底层）—— 起步阶段先立纪律，不堆冗余

## 失败模式

| 模式 | tell | fix |
|------|------|-----|
| 盲目泛化 | 知识被当"真理"跨设备套用后失效 | 每条带 scope，注明适用边界 |
| 时效腐烂 | 库里知识过期但无人察觉 | verified_on + 失效条件，定期巡检 |
| 伪真实 | "看起来对"但无出处 | 无来源不入库，或标 hearsay 待验 |
| 结构漂移 | 每人自建分类，库变碎片 | 复用既有节点结构，不新建顶层分类 |
| 过早工程化 | 起步就上镜像/同步冗余层 | 先立纪律，能力到边界再谈冗余 |
| 无来源追溯 | 文档无作者/日期，日后不知出处、无法追责 | 每篇强制含"出处与签名"+"变更记录表" |
| lark-cli JSON 解析失败 | `wiki +node-create` / `docs +update --format json` 输出带 "Creating wiki node.../Created wiki node..." 文本前缀，直接 `json.loads(stdin)` 报 JSONDecodeError | 用 `re.search(r'\{.*\}', out, re.S)` 抽 JSON 串再解析；或管道 `tail -25` 跳过前缀 |

## 文档落位约定（强制）

每篇入库文档必须在文末携带两块，便于日后溯源与追责（用户 2026-07-11 明确要求）：

1. **出处与签名**：落地日期（YYYY-MM-DD）+ 初版作者（署名，含身份如"Hermes（AI Agent）"）。
2. **变更记录表**：列（日期 / 修改人 / 变更说明）。初版填一行；后续任何修改**追加新行，不得覆盖历史**。

> 反例：文档无签名、无日期，半年后无人知出处。
> 正例：本会话落地的飞书节点"团队知识库写入规范"（含 2026-07-11 / Hermes 首行 + 维护约定）。

写入飞书知识库的具体命令与坑见 `references/feishu-wiki-recipe.md`。

## 验证清单

- [ ] scope 四字段（来源设备/适用环境/有效期/置信度）齐全
- [ ] 真实性：有可查出处或可重验命令
- [ ] 正确性：标 verified / documented / hearsay
- [ ] 时效性：带 verified_on + 失效条件
- [ ] 适配性：未隐含错误"通用"假设
- [ ] 未落入禁用场景（个人笔记/一次性/纯格式）
- [ ] 复用既有结构，未新建分类
- [ ] 含"出处与签名"区块（落地日期 + 初版作者）
- [ ] 含"变更记录表"（初版一行；后续修改追加，不覆盖）
