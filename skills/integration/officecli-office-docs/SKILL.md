---
name: officecli-office-docs
description: 使用 officecli 单二进制 CLI 创建/读取/修改/校验 Word(.docx)/Excel(.xlsx)/PowerPoint(.pptx)。无需安装
  Office、零依赖、自带高保真 HTML 渲染引擎（render→look→fix 闭环）。当用户要生成报告/报表/PPT、从文档抽取结构化数据、批量改样式、做模板合并、或需要在
  CI/无显示环境里自动化 Office 文档时使用。
version: 1.0.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags:
      trigger:
      - office 文档 自动化
      - 生成 pptx
      - 生成 docx
      - 生成 xlsx
      - 批量改 word 样式
      - 模板合并 merge
      - 抽取文档结构化数据
      - officecli
      - 生成 ppt 报告
      - excel 图表报表
      disable:
      - 不适用场景
      - 无关任务
platforms:
- linux
- macos
---
--
-

# officecli — AI 友好的 Office 文档 CLI

单二进制（`~/.local/bin/officecli`），内嵌 .NET 运行时，**无需装 Office、零依赖**。
自带从零实现的高保真 HTML 渲染引擎，可把 .docx/.xlsx/.pptx 渲染成 HTML/PNG，
让 agent 能"看见"渲染结果而非盲猜 DOM —— 这是它和 python-docx/openpyxl 最大的区别。

版本：v1.0.135（2026-07-13 装于 [HOSTNAME]，x86_64 glibc）。
二进制发布在 GitHub Releases，手动下载并 SHA256 校验后放到 `~/.local/bin/`，
**不要**跑官方 `install.sh`（它会自动往 `~/.hermes/skills/officecli/` 塞官方 SKILL.md，
污染本框架受控 skill 体系，且默认开启外网后台自动更新）。本 skill 即受控替代。

## 安装 / 升级（受控流程，非官方 install.sh）

```bash
# 解析最新 tag 并下载 x64 gnu 二进制 + SHA256SUMS，校验后装到 ~/.local/bin
VER=$(curl -fsSL -o /dev/null -w '%{url_effective}' https://github.com/iOfficeAI/OfficeCLI/releases/latest | sed -E 's#.*/tag/##')
cd /tmp
curl -fsSL -o officecli "https://github.com/iOfficeAI/OfficeCLI/releases/download/$VER/officecli-linux-x64"
curl -fsSL -o SUMS     "https://github.com/iOfficeAI/OfficeCLI/releases/download/$VER/SHA256SUMS"
EXP=$(awk -v a=officecli-linux-x64 '$2==a{print $1;exit}' SUMS)
ACT=$(sha256sum officecli | awk '{print $1}')
[ "$EXP" = "$ACT" ] && cp officecli ~/.local/bin/officecli && chmod +x ~/.local/bin/officecli
officecli --version
```
arm64 机器把 asset 换成 `officecli-linux-arm64`（CM4 等）。musl(Alpine) 用 `officecli-linux-alpine-x64`。

## 三层架构（始终优先用高层）

| 层 | 用途 | 命令 |
|----|------|------|
| L1 读 | 语义化视图 | `view`(outline/text/annotated/stats/issues/html/screenshot/svg) |
| L2 DOM | 结构化元素操作 | `get` `query` `set` `add` `remove` `move` `swap` |
| L3 原始 XML | XPath 直改（万能兜底） | `raw` `raw-set` `add-part` `validate` |

拿不准属性名/值格式/语法时，**先跑 help 别猜**：
`officecli help` / `officecli help docx` / `officecli help docx paragraph` / `officecli help docx set paragraph` / `--json`

## 工作流：用前先找模板（render→look→fix 前置）

本 skill 自带 curated 参考模板库 `examples/`（官方 OfficeCLI examples 子集，Apache-2.0，
含成品文档 + 生成脚本 + 说明三件套）。**做任何文档前先搜模板**，比凭空猜属性名快且稳：

1. 按格式/场景在 `examples/` 检索（用 Hermes search_files，例：在 `examples/` 搜 `*.pptx` 或 `charts`）。
2. 读 `examples/INDEX.md` 看每个模板的适用场景与生成脚本路径。
3. 复用方式三选一：
   - **克隆成品**：`officecli add 新deck.pptx / --from examples/ppt/presentation.pptx`
   - **学结构**：`officecli dump examples/ppt/presentation.pptx -o /tmp/bp.json` → 改 → `officecli batch 新deck.pptx --input /tmp/bp.json`
   - **套占位符模板**：把成品 `merge` 成带 `{{key}}` 的模板，再批量填（见下"模板合并"）。
4. 自己做的**好成品反向沉淀**进 `examples/`（见文末"反向沉淀"），逐步长成本地模板仓库。

模板库路径（绝对）：`~/.hermes/skills/integration/officecli-office-docs/examples/`
索引：`~/.hermes/skills/integration/officecli-office-docs/examples/INDEX.md`

## 核心命令速查

```bash
# 创建（按扩展名判断类型）
officecli create deck.pptx
officecli create report.docx
officecli create data.xlsx

# L1 视图
officecli view deck.pptx outline            # 结构大纲
officecli view report.docx text --max-lines 50
officecli view data.xlsx issues --type format
officecli view deck.pptx html -o /tmp/d.html   # 静态 HTML 快照（同 watch 渲染器，无需服务）
officecli view deck.pptx screenshot -o /tmp/d.png   # 每页 PNG，供多模态读；--page 1-N 指定页

# L2 读
officecli get deck.pptx '/slide[1]' --depth 1 --json   # 列出某 slide 所有形状
officecli query report.docx 'paragraph[style=Normal] > run[font!=Arial]'

# L2 写
officecli add deck.pptx / --type slide --prop title="Q4 Report" --prop background=1A1A2E
officecli set report.docx '/body/p[1]' --prop bold=true --prop color=FF0000
officecli add report.docx /body --type paragraph --prop text="摘要" --prop style=Heading1
officecli set data.xlsx /Sheet1/A1 --prop value="Name" --prop bold=true
officecli remove report.docx '/body/p[4]'
officecli move report.docx /body/p[5] --to /body --index 1

# 文本查找/替换（scope 用路径控制，/ 整文档）
officecli set report.docx / --find draft --replace final
officecli set report.docx '/body/p[1]' --find '\\d+%' --prop regex=true --prop color=red

# 模板合并（{{key}} 占位符，零 token，可批量填 N 份）
officecli merge invoice-tpl.docx out-001.docx '{"client":"Acme","total":"$5,200"}'

# 往返 dump / batch（参考现有文档生成变体）
officecli dump existing.docx -o blueprint.json
officecli batch new.docx --input blueprint.json
```

## 渲染引擎（关键能力）

- `view html`：自包含 HTML 文件，浏览器可开（资产内联）。
- `view screenshot`：每页 PNG（headless 浏览器渲染），多模态 agent 直接读图。
  **实测无外网也能出图**（[HOSTNAME] 本地渲染成功，17K png），CI/容器/无显示环境可用。
- `watch`：本地 HTTP 预览服务（默认 :26315），每次 add/set/remove 自动刷新；
  Excel watch 支持内联编辑单元格、拖拽图表。浏览器可点选元素，`officecli get <file> selected` 读回选中路径。

render→look→fix 闭环：生成 → `view screenshot` 看效果 → `set` 调 → 再看，无需开 Office。

## 公式 / 透视表引擎（xlsx）

- 350+ Excel 内置函数写入即自动求值（=SUM/A1:A2 落盘即带值，无需 Office 往返）。
- 动态数组 FILTER/SORT/UNIQUE/SEQUENCE/LET/LAMBDA/MAP；VLOOKUP/XLOOKUP/INDEX/MATCH；
  财务/债券/统计/回归/日期/文本族。
- 透视表一行命令生成（多字段行列/筛选/10 种聚合/showDataAs/日期分组/计算字段/topN/布局）。

```bash
officecli add data.xlsx /Sheet1 --type pivottable \
  --prop source='Data!A1:E10000' --prop rows='Region,Category' \
  --prop cols=Quarter --prop values='Revenue:sum,Units:avg' --prop showDataAs=percentOfTotal
```

## Resident 模式与落盘（避坑重点）

每条命令首次访问会**自动起一个 resident 进程**（60s 空闲回收），后续命令零文件 I/O。
officecli 自身读(get/query/view/dump)永远看到最新编辑，**中途无需 save**。
**但在非 officecli 程序读取文件前必须 flush**（python-docx/openpyxl、Word、渲染器、上传/投递）：
```bash
officecli save report.docx     # flush 但保留 resident 热
officecli close report.docx    # flush + 释放
```
长会话建议显式 `open`/`close`（12min 空闲）。空闲自动 flush（自适应 2-10s）。
流水线每步都给外部程序读：设 `OFFICECLI_RESIDENT_FLUSH=each`。
关闭自动 resident：`OFFICECLI_NO_AUTO_RESIDENT=1`。

> 🛑 **多 slide PPTX 构建：禁用 `officecli open` resident 模式！**
> 本会话实战踩坑：`officecli open deck.pptx` 后连续 `officecli add deck.pptx / --type slide`
> 会**静默塌陷**——15 次 add 只生成 5 页（add 在复用会话里 index 计数错乱，每次都插到
> 错误位置）。症状隐蔽：build 脚本跑完打印 DONE，但 zipfile 数 slide 只有 5。
> **正确做法**：构建脚本**不要** `officecli open`/`close`，每条命令独立执行
> （无 resident，每条自行开/关文件）。实测 15 页全部正确生成，耗时 ~16s 可接受。
> 仅在单条交互式编辑（改一处属性）时可享 resident 便利；multi-add 批量构建一律非 resident。
> 构建前务必 `officecli close deck.pptx 2>/dev/null` 清掉可能残留的 resident。

## batch 批量（错误默认继续，--stop-on-error 中止）

```bash
echo '[{"command":"set","path":"/Sheet1/A1","props":{"value":"Name","bold":"true"}},
      {"command":"set","path":"/Sheet1/B1","props":{"value":"Score","bold":"true"}}]' \
  | officecli batch data.xlsx --json
officecli batch data.xlsx --commands '[{"op":"set","path":"/Sheet1/A1","props":{"value":"Done"}}]'
```

## 常见坑

- 所有属性走 `--prop`，**没有** `--name`/`--title` 这类独立 flag。
- 路径 `[N]` 在 zsh/bash 里要引号：`'/slide[1]'`，否则被 glob 展开。
- PPT `shape[1]` 通常是标题占位符，内容形状用 `shape[2]+`。
- PPT 不支持 `/shape[myname]`（名称索引），用数字下标或 `@name=`（仅 PPT）。
- 拿不准属性名 → 跑 `officecli help <format> <element>`，别猜。
- shell 里 `$` 会被吞：`--prop text='$15M'` 用单引号；`\n` 换行用 `\\n` 或 heredoc batch。
- 改文件前先关掉 PowerPoint/WPS。
- 路径 1-based；`--index` 0-based（xlsx 的 add row/col 例外，1-based）。

## 与 python-docx / openpyxl 的取舍

- 要**生成即所见、渲染校验、复杂布局/图表/动画/透视表/模板合并** → officecli 更省心（闭环渲染）。
- 纯数据填表、已在用 pandas+openpyxl 的轻量流程 → 不必换。
- officecli 输出结构化 JSON(`--json`)，天然适合 agent 流水线；修改后 `validate` 做 OpenXML 模式校验。

## 反向沉淀：好成品存回模板库

用 officecli 做出可复用的成品（汇报 deck / 报表 / 文档），沉淀进 `examples/` 逐步长本地仓库。

> 🛑 **铁律（沉淀闸门）：成品经用户明确确认 OK 之后才能沉淀。**
> 半成品 / 未确认的交付物**绝不**预先存入 examples/。
> **正确流程**：生成 → render→look→fix 校验（每页 view screenshot 视觉过）→ `officecli validate` 通过
> → 交付用户（飞书/IM/文件）→ 用户**显式回复"OK"或"可以"等确认** → 再执行下方沉淀步骤。
> 违反 = 把未验证资产污染模板库（用户 2026-07-13 明确：
> "模板沉淀需要交付完成，成品OK才能沉淀模板"）。
>
> 即使 agent 自己看起来"完美"也不构成 OK —— 闸门是用户确认，不是 agent 自评。
> 交付前可以**预告**"沉淀待你确认后进行"，但**不可提前执行 cp / dump / 改 INDEX**。

```bash
# 一键沉淀（复制成品 + dump 蓝图 + 提示补 INDEX.md）：
bash ~/.hermes/skills/integration/officecli-office-docs/scripts/sediment_template.sh 我的成果.pptx ppt 场景名
# 或手动：
# 1) 复制成品到对应子目录（语义化命名）
cp 我的成果.pptx ~/.hermes/skills/integration/officecli-office-docs/examples/ppt/场景名.pptx
# 2) 同时 dump 可复现蓝图（日后 batch 改）
officecli dump 我的成果.pptx -o ~/.hermes/skills/integration/officecli-office-docs/examples/ppt/场景名.json
# 3) 在 examples/INDEX.md 对应表格追加一行（文件 / 场景 / 生成方式）
```
- 含敏感数据：先 `officecli set` 脱敏，或 `merge` 抽成 `{{占位符}}` 模板再存。
- 沉淀的模板归本框架所有，**独立于官方仓库**，officecli 升级不会被覆盖。
- 详细步骤见 `examples/INDEX.md` 末尾「反向沉淀」段。
- **讲解视频类 / 解说 PPT** 的构建范式与布局避坑见 `references/explainer-ppt-patterns.md`
  （卡片高度 EMU 经验值 / anchor=ctr / 7 卡 3+3+1 / nvSpPr 完整闭合 / render→look→fix 循环）；
  可直接复制的构建脚本见 `scripts/hermes-explain-build.sh`。

### 沉淀闸门自检清单

执行 `cp` 之前必须能回答"是"全部四项；任一否 = 闸门未过，禁止沉淀：

- [ ] `officecli validate 成品.pptx` 报 `no errors found`？
- [ ] 每一页都跑过 `view screenshot` + vision 视觉校验过（无溢出/重叠/留白失控）？
- [ ] 成品已交付给用户（飞书/IM/文件）？
- [ ] 用户在交付后**显式确认"OK"/"可以"等**？

## 验证

装完跑：`officecli --version` 应返回版本号。
冒烟：`officecli create /tmp/t.pptx && officecli add /tmp/t.pptx / --type slide --prop title=Hi && officecli view /tmp/t.pptx outline`
模板库：`ls ~/.hermes/skills/integration/officecli-office-docs/examples/`（root/word/excel/ppt + INDEX.md）
模板检索验证：在 examples/ 搜 `*.pptx` 应命中 root 4 个 + ppt 4 个成品。

## 讲解视频类 PPT 生成范式（render→look→fix 闭环）

做"讲解/演示类" PPT 用 raw XML 直绘（examples/ppt/presentation.sh 是官方范式）：深色渐变背景 + 几何装饰圆 + 圆角卡片 + 大标题。核心流程（本会话实战验证）：

1. **起步**：克隆成品当骨架 `officecli add 新.pptx / --from examples/ppt/presentation.pptx`，或 `create` 后用 `raw-set` 逐页 `//p:cSld` prepend `<p:bg>` 深色渐变。
2. **每页结构**：`add ... / --type slide` → `raw-set` 加背景 → `raw-set` append 文本框/卡片/装饰（`<p:sp>` 必须含完整 `p:nvSpPr><p:cNvPr/><p:cNvSpPr/><p:nvPr/></p:nvSpPr>`，否则 schema 警告）。
3. **闭环校验（关键，不能跳过）**：每页 `officecli view 新.pptx screenshot -o /tmp/pN.png --page N`，用 vision 看实际渲染——专查**卡片过高留白、文字溢出、元素重叠、布局不对称**（如 7 卡排成 4+3 而非 3+3+1）。发现问题改 `raw-set` 坐标/尺寸重渲染，直到无错。
   - 经验值：卡片高度压到 1400000-2600000 EMU（原 4000000 显空）；内容垂直居中；多卡页用 footnote 全宽居中页脚替代孤立角落小字。
   - 警告：vision 会漏报轻微重叠/贴边。本会话 user 连续反馈两圆角框重叠、字体与框边重叠、超出页面边界，而 vision 却判无问题。凡 user 反馈视觉异常，不要只信 vision——用 scripts/geom_check.py 对每页 shape 的真实 x/y/cx/cy 做硬校验（超界：x+cx>12192000 或 y+cy>6858000；重叠：两两交集>容差）。详见 references/geom-check.md。
   - 16:9 画布 EMU 上限：宽 12192000、高 6858000。单卡片 cx 别超 11000000、底部 y+cy 留 ≥300000 余量。
   - 插入页导致 slide 索引偏移（必错点）：中途插入新页后，其后所有 add_slide 引用会重复同名 slide 冲突。修法：插入页后把其后全部 slide[N] 引用整体 +1 顺延，并同步改 echo 文案里的 Slide N。务必先 officecli close deck.pptx 清残留 resident 再重建。
4. **合规**：`officecli validate 新.pptx` 应 `no errors found`。

- 工具：完整可复现脚本见 `scripts/hermes-explain-build.sh`（改内容即可复用，首参为输出路径）；坐标级几何校验脚本 `scripts/geom_check.py <pptx>`（超界+重叠硬检测，按 name 前缀跳过装饰/有意叠放）；原理与真实踩坑表见 `references/geom-check.md`。
> 布局细节 + EMU 经验值 + 闭环流程见 `references/explainer-ppt-patterns.md`（source of truth）；
> 成品范例 `hermes-micro-framework-讲解.pptx`（见反向沉淀闸门）。

## 踩坑（本会话真实发生过）

- **skill 不被自动召回**：trigger 必须写嵌套 `metadata.hermes.tags.trigger`（与 examples/INDEX.md 同模式），**不能**写顶层 `trigger:`。顶层写法 indexer 读不到 → trigger 不进 sparse 索引 → 孤立短语 query 漏召。建完 skill 务必 `build_index(force=True)` 后 `matcher.search` 实测命中（见 hermes-agent-skill-authoring §召回质量约束 #3.5）。
- **不下全量仓库**：拉官方 examples 用 raw 逐个取 curated 文件，别 `git archive` 下 75M 全量再筛。用户明确选过"跳过体积估算、只拉子集"，下全量会被拦（范围膨胀违反既定窄操作）。
- **多 slide 构建禁用 resident**：见上文「Resident 模式」🛑 段——`open` + 连续 `add` 会静默把 15 页塌成 5 页。脚本构建一律非 resident，每条命令独立执行。
- **bash `set -u` 参数数纪律**：写多参数 helper 函数（textbox/card/bar/row 等）时，调用必须传齐位置参数，否则 `$7` unbound 直接中断脚本（本会话因此在 Slide 5 崩，只生成 5 页）。调用前数清参数；若函数参数顺序改了，所有调用点同步改。
- **尊重已确认的窄范围**：用户用 clarify 选定"只拉 curated 子集"后，不要自行升级成"下载全量归档再筛"——宽操作易触发拦截且违背用户明确取向。
