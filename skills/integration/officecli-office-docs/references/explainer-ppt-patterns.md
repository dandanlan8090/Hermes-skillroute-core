# 讲解视频类 PPT 构建范式（render→look→fix 闭环）

会话实战沉淀：构建 6 页「Hermes Micro Framework 讲解」PPT，officecli v1.0.135 + 视觉校验通过。
参考成品：`hermes-micro-framework-讲解.pptx`（需用户 OK 后才正式入 examples/）。
参考脚本：`scripts/hermes-explain-build.sh`（改内容即可复用）。

## 视觉范式（"讲解视频类"风格 = 深色 + 几何 + 卡片 + 大标题）

- **背景**：每页 `<p:bg>` prepend 深色三段渐变（`0D1B2A → 1B2838 → 0A1628`，lin ang=5400000）。
  辅助/分隔页用单色实底（`0D1B2A`）。
- **装饰圆**：右上 + 左下两个半透明大圆（`ellipse` prst，`alpha=6000-8000`），青/紫各一；
  增强"视频感"不抢视觉。
- **卡片**：圆角矩形 `roundRect`（`adj=8000`），深底 `152238`，彩色 1px 描边（青/紫/黄/绿/粉/紫各色轮换）。
- **字体**：中文 `Microsoft YaHei`（latin + cs 都设），标题 `sz=2000-3200 b=1`，正文 `sz=1100-1200`。

## 关键函数（bash helper，复制到构建脚本即可）

```bash
# 文本框（多行用 | 分隔）
textbox() { local slide="$1" id="$2" x="$3" y="$4" cx="$5" cy="$6" sz="$7" color="$8" txt="$9"
  IFS='|' read -ra LINES <<< "$txt"; local body=""
  for line in "${LINES[@]}"; do
    body+="<a:p><a:pPr algn=\"l\"/><a:r><a:rPr lang=\"zh-CN\" sz=\"$sz\" b=\"1\" dirty=\"0\"><a:solidFill><a:srgbClr val=\"$color\"/></a:solidFill><a:latin typeface=\"Microsoft YaHei\"/><a:cs typeface=\"Microsoft YaHei\"/></a:rPr><a:t>$line</a:t></a:r></a:p>"
  done
  officecli raw-set "$OUT" "$slide" --xpath "//p:cSld/p:spTree" --action append --xml "
<p:sp><p:nvSpPr><p:cNvPr id=\"$id\" name=\"TB$id\"/><p:cNvSpPr txBox=\"1\"/><p:nvPr/></p:nvSpPr>
<p:spPr><a:xfrm><a:off x=\"$x\" y=\"$y\"/><a:ext cx=\"$cx\" cy=\"$cy\"/></a:xfrm><a:prstGeom prst=\"rect\"><a:avLst/></a:prstGeom><a:noFill/><a:ln><a:noFill/></a:ln></p:spPr>
<p:txBody><a:bodyPr wrap=\"square\" anchor=\"t\"/><a:lstStyle/>$body</p:txBody></p:sp>" ; }

# 卡片（高度压缩、内容垂直居中）
card() { ...; # cx=3200000, cy=1400000-2600000 EMU
  # 关键：bodyPr anchor="ctr"（不是 "t"！否则内容贴顶留白）
  # tIns/bIns=182880（比 lIns/rIns=228600 略小，省垂直空间）
}

# 全宽页脚（替代孤立角落 subtext）
footnote() { # y=6480000, cy=300000, algn=ctr, 浅灰 8B95A2
  # 比 subtext 居左 + 限定 y 坐标更协调，避免在多卡页"飘"在角落
}

# 装饰圆
deco() { # ellipse + alpha，半透明，alpha=6000-8000
  # ⚠️ p:nvSpPr 必须完整：<p:cNvPr/><p:cNvSpPr/><p:nvPr/></p:nvSpPr>
  # 缺 <p:nvPr/> 会报 schema warning（不致命但污染日志）
}
```

## 布局避坑（render→look→fix 实测得出）

| 坑 | 错误做法 | 正确做法 | 验证 |
|----|---------|---------|------|
| **卡片过高留白** | `cy=4000000` (2 行内容撑 4M) | `cy=1400000-2600000` (按内容行数) | vision 看：底部 ~60% 空白 = 失败 |
| **卡片内容贴顶** | `bodyPr anchor="t"` + `tIns=228600` | `bodyPr anchor="ctr"` + `tIns=182880` | vision 看：内容是否垂直居中 |
- **页脚孤立角落** | `subtext` 放在角落、限定 y | `footnote` 全宽居中 `y=6420000` | vision 看：是否在底部居中、与其他页一致 |
| **N 个卡片排成 N×1 行列不均** | 7 卡按 4 列 x 排 → 4+3 不对称 | 7 卡按 3+3+1 排（最后单独居中） | 数行：每行卡片数 × 行数 = N 整齐 |
| **装饰圆遮挡文字** | 大圆放文字区 | 圆放四角空白区 + `alpha≤8000` | vision 看：标题/卡片边界是否被切 |
| **nvSpPr 缺 nvPr** | 漏写 `<p:nvPr/>` | 完整三件套 `<p:cNvPr/><p:cNvSpPr/><p:nvPr/></p:nvSpPr>` | 看 officecli stderr：incomplete content warning |

## 闭环工作流（每步都有产出物）

1. **写构建脚本**（bash + officecli raw-set）→ 跑出 .pptx
2. **逐页渲染截图**：
   ```bash
   for p in 1 2 3 4 5 6; do
     officecli view out.pptx screenshot -o /tmp/p$p.png --page $p
   done
   ```
3. **逐页 vision 校验**（专查：文字溢出 / 卡片留白 / 重叠 / 布局不对称 / 圆遮挡）
4. **发现问题改脚本坐标/尺寸/anchor** → 重跑 → 再 vision
5. **最终 validate**：`officecli validate out.pptx` 应 `no errors found`
6. **交付用户**（飞书/IM/文件）→ **等用户显式 OK** → 才执行反向沉淀（见 SKILL.md §反向沉淀铁律）

## 数值经验（EMU，slide 默认 16:9 = 12192000 × 6858000）

- 标题区：`y=400000, cy=700000-900000`
- 副标题：`y=1150000, cy=400000`
- 第一行卡片起点：`y=1950000-2000000`
- 卡片列 x 偏移：`x=700000 / 4150000 / 7600000`（三列，等距 3450000）
- 卡片宽：`cx=3200000-3300000`
- 卡片高：内容 1 行=`1400000`，2 行=`2100000-2600000`，3 行=`3000000-3600000`
- 行间距：`y` 间隔 ≥ 200000
- **页脚**：`y=6420000, cy=300000`（底边留 ~438000 EMU，贴底边风险消除）
- 装饰圆大：`cx=cy=3200000-4800000`，alpha 6000-8000

## 高级布局辅助函数

除 textbox/card/footnote/deco 外，多页场景推荐这些（已内置 `scripts/hermes-explain-build.sh`）：

| 函数 | 用途 | 参数 | 示例 |
|------|------|------|------|
| `row` | 检索结果/数据表格行 | slide id x y cx cy label val color | `row /slide[3] 210 700k 2150k 10.5M 700k "#1 shipping-verification" "0.0428" 00B4D8` |
| `bar` | 占比条形（模拟饼图） | slide id x y cy pct color | `bar /slide[5] 210 800k 2350k 750k 25 06D6A0` |
| `compare_col` | 两栏对比块 | slide id x y cx cy title body accent | 适合"痛点引入"/"适用场景"页 |
| `PARTTAG` | 部分标签徽章 | slide id "第一部分 · 标签" | 每部分第一页标色块 |
| `HDR` | 标题+副标题快捷 | slide "标题" "副标题" | 综合 textbox+subtext |

### row 函数关键

```bash
row /slide[7] 210 700000 2150000 10550000 700000 "#1 技能名" "0.0428" 00B4D8
```
- 每行两个 `<p:sp>`：左半圆角矩形（标签）+ 右对齐数值（盖在上层）
- 行高 `cy=700000`，行间 `y` 步长 `+770000`（cy + 70000 gap）
- 5 行到底 ~6000000，留白给 footnote

### bar 函数关键

- 宽度按 `pct` 百分比 × 9000000 EMU（~10.5M 页面可用宽）自动计算
- 两根上下排列时 y 错开（隔 ~850000 EMU），下方 banner 卡片不重叠

## 15 页 PPT 构建避坑（本会话 2026-07-13 实战记录）

以下坑专属于 10+ 页批量构建，小脚本（≤6 页）不易暴露：

### 🛑 Resident 模式多 slide 塌陷（优先级最高）
- **症状**：`officecli open out.pptx` 后连续 `add ... / --type slide` 15 次，跑完显示 DONE，但 `zipfile` 数 slide 只有 5。
- **根因**：resident 复用会话下 `add` 的 index 计数错乱，后续 add 插到错误位置或被静默跳过。
- **修复**：构建脚本**不要** `officecli open`/`close`。每条命令独立执行（无 resident，每条自行开/关文件）。实测 15 页全部正确生成，耗时 ~16s 可接受。
- **单条交互式编辑**（改一处属性）可享 resident 便利；multi-add 批量构建一律非 resident。
- **构建前务必** `officecli close out.pptx 2>/dev/null` 清理残留 resident（本机实现，非死循环）。

### 🧨 `set -u` 下 `$7 unbound variable`
- **症状**：script 静默退出到 Slide 5/8/接近尾声处，只生成前半段页。
- **根因**：`bar` `row` `compare_col` 等 7+ 参数函数调用时参数个数不对。例如 `bar` 定义 expects 7 个（`slide id x y cy pct color`），调用只传 6 个（cy 与 color 之间缺 pct）→ `$7` 未定义。
- **修复**：`set -u` 下每个调用必须严格按定义顺序和个数传参。新增/改函数后同步所有调用点。不在 `set -u` 下运行助手脚本也可（函数内部 `local` 变量不受 `set -u` 影响），非 `set -u` 时 `$7` 只返回空字符串，不崩，但隐蔽性高更难查。

### 多卡页布局对称性
- 7 张卡片按 **3+3+1**（三列、两行、最后一卡居中）比 4+3 对称。
- 行高：`cy=1400000`（内容 1 行）~ `2100000`（内容 2 行）——压扁卡片减少死区，同时省垂直空间给第三行。
- 三列 x：`700k / 4150k / 7600k`（等距 3450k EMU）。
- 二列（两栏对比）：两列 x=800k（4200k宽），x=4650k（4200k宽）。

## 反向沉淀（必走闸门）

完整流程 + 自检清单见 `../../SKILL.md` §反向沉淀。**铁律：用户没显式 OK = 不沉淀**。
一键脚本：`bash scripts/sediment_template.sh --confirmed <成品> ppt <场景名>`（缺 `--confirmed` 直接 exit 2）。
