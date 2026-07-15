# OfficeCLI 参考模板库（curated subset）

来源：iOfficeAI/OfficeCLI 官方 `examples/` 目录（Apache-2.0），由 Hermes 于 2026-07-13 拉取精选子集。
每类含「成品文档 + 生成脚本(.sh/.py) + 说明(.md)」三件套——脚本是**可学习的参考实现**，不是一键套用模板。

> 使用约定：干活前先在下方按格式/场景找匹配的模板，用 `officecli dump` 学结构或直接 `clone`/`merge`；
> 自己做出来的好成品，按文末「反向沉淀」流程存回本目录，逐步长成本地模板仓库。

## 目录结构

```
examples/
├── root/    # 根目录成品 pptx（完整可参考的现成 deck）
├── word/    # docx 示例（含 .sh 生成脚本 + .md 说明）
├── excel/   # xlsx 示例
└── ppt/     # pptx 示例
```

## 索引

### root/ — 成品 PPT 参考（直接当母版看结构）
| 文件 | 场景 |
|------|------|
| Alien_Guide.pptx | 图文混排科普 deck（外星人指南） |
| Cat-Secret-Life.pptx | 创意/生活类 deck |
| budget_review_v2.pptx | 预算评审汇报 deck（商务） |
| product_launch_morph.pptx | 产品发布 + Morph 动画 deck |

### word/ — Word 模板
| 文档 | 生成脚本 | 适用场景 |
|------|----------|----------|
| document-formatting.docx | document-formatting.sh | 文档排版范式（标题/段落/样式/缩进） |
| charts.docx | charts.sh | Word 内嵌图表 |
| fields.docx | fields.sh | 域（页码/交叉引用/SEQ 等） |

### excel/ — Excel 模板
| 文档 | 生成脚本 | 适用场景 |
|------|----------|----------|
| pivot-tables.xlsx | pivot-tables.sh | 透视表（多字段/聚合/showDataAs） |
| charts.xlsx | charts.sh | 图表 |
| cell-formatting.xlsx | — | 单元格格式 |
| conditional-formatting.xlsx | — | 条件格式（databar/colorscale/iconset） |

### ppt/ — PowerPoint 模板
| 文档 | 生成脚本 | 适用场景 |
|------|----------|----------|
| presentation.pptx | presentation.sh | 通用演示 deck 基线（标题/内容/形状/图表） |
| animations.pptx | animations.sh | 进入/退出/强调动画 + 多效链 |
| diagram.pptx | diagram.sh | mermaid 流程图/时序图 → 原生形状 |
| 3d-model.pptx | — | 3D 模型(.glb) 嵌入 |

## 用前检索

在 examples/ 里按格式/场景搜（命令示例，实际用 Hermes search_files）：
- 找 PPT 母版：`search_files` 在 `examples/` 搜 `*.pptx`
- 找含图表的 Word：`search_files` 在 `examples/word` 搜 `charts`
- 找透视表做法：读 `examples/excel/pivot-tables.sh`（脚本即文档）

学结构：`officecli dump examples/ppt/presentation.pptx -o /tmp/blueprint.json` → 看结构化 spec → 改 → `officecli batch 新deck.pptx --input /tmp/blueprint.json`
克隆成品：`officecli add 新deck.pptx / --from examples/ppt/presentation.pptx`

## 反向沉淀：把好成品存回本仓库

当你用 officecli 做出一个值得复用的成品（汇报 deck / 报表 / 文档），沉淀步骤：

1. 复制文档到对应子目录，命名语义化：
   ```bash
   cp 我的成果.pptx ~/.hermes/skills/integration/officecli-office-docs/examples/ppt/场景名.pptx
   ```
2. 同时 dump 出可复现蓝图（供日后 batch 改）：
   ```bash
   officecli dump 我的成果.pptx -o ~/.hermes/skills/integration/officecli-office-docs/examples/ppt/场景名.json
   ```
3. 在本 INDEX.md 对应表格追加一行（文件 / 场景 / 生成方式）。
4. 若成品含敏感数据，先 `officecli set` 脱敏或 `merge` 抽成 {{占位符}} 模板再存。

> 沉淀的模板归本框架所有，不随 officecli 升级被覆盖（独立于官方仓库）。
