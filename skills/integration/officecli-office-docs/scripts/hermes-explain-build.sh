#!/bin/bash
# Hermes 讲解/解说类 PPT 构建骨架（深色科技风 · 复用范式）
# 用法: bash hermes-explain-build.sh <输出.pptx>
#
# 设计要点（本会话实战验证 + 已踩坑修正）:
#   1. 禁用 `officecli open` resident 模式! 多 slide 批量 add 在 resident 下会
#      静默塌陷(15→5页)。本脚本每条命令独立执行(无 open/close)。
#   2. 所有 helper 用固定位置参数; 调用必须传齐, 否则 set -u 下 N unbound 中断。
#   3. 每页用 view screenshot 渲染 → vision 检查布局 → 改坐标重跑 → 终版 validate。
#   4. 交付后等用户显式 OK 再沉淀模板。
# 依赖: officecli ~/.local/bin/officecli
set -u
OUT="${1:-~/hermes-explain.pptx}"
rm -f "$OUT"
officecli create "$OUT"

BG_DARK='<p:bg><p:bgPr><a:gradFill rotWithShape="0"><a:gsLst><a:gs pos="0"><a:srgbClr val="0D1B2A"/></a:gs><a:gs pos="50000"><a:srgbClr val="1B2838"/></a:gs><a:gs pos="100000"><a:srgbClr val="0A1628"/></a:gs></a:gsLst><a:lin ang="5400000" scaled="1"/></a:gradFill><a:effectLst/></p:bgPr></p:bg>'

# ========== Helper 函数库（EMU 坐标, 16:9 = 12192000 × 6858000）==========
add_slide() { officecli add "$OUT" / --type slide
  officecli raw-set "$OUT" "$1" --xpath "//p:cSld" --action prepend --xml "$BG_DARK"; }
textbox() { local slide="$1" id="$2" x="$3" y="$4" cx="$5" cy="$6" sz="$7" color="$8" txt="$9"
  local body=""; IFS='|' read -ra L <<< "$txt"
  for line in "${L[@]}"; do
    body+="<a:p><a:pPr algn=\"l\"/><a:r><a:rPr lang=\"zh-CN\" sz=\"$sz\" b=\"1\" dirty=\"0\"><a:solidFill><a:srgbClr val=\"$color\"/></a:solidFill><a:latin typeface=\"Microsoft YaHei\"/><a:cs typeface=\"Microsoft YaHei\"/></a:rPr><a:t>$line</a:t></a:r></a:p>"
  done
  officecli raw-set "$OUT" "$slide" --xpath "//p:cSld/p:spTree" --action append --xml "
<p:sp><p:nvSpPr><p:cNvPr id=\"$id\" name=\"TB$id\"/><p:cNvSpPr txBox=\"1\"/><p:nvPr/></p:nvSpPr>
<p:spPr><a:xfrm><a:off x=\"$x\" y=\"$y\"/><a:ext cx=\"$cx\" cy=\"$cy\"/></a:xfrm><a:prstGeom prst=\"rect\"><a:avLst/></a:prstGeom><a:noFill/><a:ln><a:noFill/></a:ln></p:spPr>
<p:txBody><a:bodyPr wrap=\"square\" anchor=\"t\"/><a:lstStyle/>$body</p:txBody></p:sp>"; }
subtext() { local slide="$1" id="$2" x="$3" y="$4" cx="$5" cy="$6" sz="$7" color="$8" txt="$9"
  officecli raw-set "$OUT" "$slide" --xpath "//p:cSld/p:spTree" --action append --xml "
<p:sp><p:nvSpPr><p:cNvPr id=\"$id\" name=\"SB$id\"/><p:cNvSpPr txBox=\"1\"/><p:nvPr/></p:nvSpPr>
<p:spPr><a:xfrm><a:off x=\"$x\" y=\"$y\"/><a:ext cx=\"$cx\" cy=\"$cy\"/></a:xfrm><a:prstGeom prst=\"rect\"><a:avLst/></a:prstGeom><a:noFill/><a:ln><a:noFill/></a:ln></p:spPr>
<p:txBody><a:bodyPr wrap=\"square\" anchor=\"t\"/><a:lstStyle/><a:p><a:pPr algn=\"l\"/><a:r><a:rPr lang=\"zh-CN\" sz=\"$sz\" dirty=\"0\"><a:solidFill><a:srgbClr val=\"$color\"/></a:solidFill><a:latin typeface=\"Microsoft YaHei\"/><a:cs typeface=\"Microsoft YaHei\"/></a:rPr><a:t>$txt</a:t></a:r></a:p></p:txBody></p:sp>"; }
card() { local slide="$1" id="$2" x="$3" y="$4" cx="$5" cy="$6" title="$7" body="$8" accent="$9"
  officecli raw-set "$OUT" "$slide" --xpath "//p:cSld/p:spTree" --action append --xml "
<p:sp><p:nvSpPr><p:cNvPr id=\"$id\" name=\"Card$id\"/><p:cNvSpPr/><p:nvPr/></p:nvSpPr>
<p:spPr><a:xfrm><a:off x=\"$x\" y=\"$y\"/><a:ext cx=\"$cx\" cy=\"$cy\"/></a:xfrm><a:prstGeom prst=\"roundRect\"><a:avLst><a:gd name=\"adj\" fmla=\"val 8000\"/></a:avLst></a:prstGeom><a:solidFill><a:srgbClr val=\"152238\"/></a:solidFill><a:ln w=\"12700\"><a:solidFill><a:srgbClr val=\"$accent\"/></a:solidFill></a:ln></p:spPr>
<p:txBody><a:bodyPr wrap=\"square\" lIns=\"228600\" tIns=\"182880\" rIns=\"228600\" bIns=\"182880\" anchor=\"ctr\"/><a:lstStyle/>
<a:p><a:pPr algn=\"ctr\"/><a:r><a:rPr lang=\"zh-CN\" sz=\"2000\" b=\"1\" dirty=\"0\"><a:solidFill><a:srgbClr val=\"$accent\"/></a:solidFill><a:latin typeface=\"Microsoft YaHei\"/><a:cs typeface=\"Microsoft YaHei\"/></a:rPr><a:t>$title</a:t></a:r></a:p>
<a:p><a:pPr algn=\"ctr\"/><a:endParaRPr lang=\"zh-CN\" sz=\"600\"/></a:p>
<a:p><a:pPr algn=\"ctr\"/><a:r><a:rPr lang=\"zh-CN\" sz=\"1100\" dirty=\"0\"><a:solidFill><a:srgbClr val=\"C7D0DB\"/></a:solidFill><a:latin typeface=\"Microsoft YaHei\"/><a:cs typeface=\"Microsoft YaHei\"/></a:rPr><a:t>$body</a:t></a:r></a:p>
</p:txBody></p:sp>"; }
footnote() { local slide="$1" id="$2" txt="$3"
  officecli raw-set "$OUT" "$slide" --xpath "//p:cSld/p:spTree" --action append --xml "
<p:sp><p:nvSpPr><p:cNvPr id=\"$id\" name=\"Foot$id\"/><p:cNvSpPr txBox=\"1\"/><p:nvPr/></p:nvSpPr>
<p:spPr><a:xfrm><a:off x=\"800000\" y=\"6420000\"/><a:ext cx=\"10592000\" cy=\"300000\"/></a:xfrm><a:prstGeom prst=\"rect\"><a:avLst/></a:prstGeom><a:noFill/><a:ln><a:noFill/></a:ln></p:spPr>
<p:txBody><a:bodyPr wrap=\"square\" anchor=\"ctr\"/><a:lstStyle/><a:p><a:pPr algn=\"ctr\"/><a:r><a:rPr lang=\"zh-CN\" sz=\"1100\" dirty=\"0\"><a:solidFill><a:srgbClr val=\"8B95A2\"/></a:solidFill><a:latin typeface=\"Microsoft YaHei\"/><a:cs typeface=\"Microsoft YaHei\"/></a:rPr><a:t>$txt</a:t></a:r></a:p></p:txBody></p:sp>"; }
deco() { local slide="$1" id="$2" x="$3" y="$4" cx="$5" cy="$6" color="$7" alpha="$8"
  officecli raw-set "$OUT" "$slide" --xpath "//p:cSld/p:spTree" --action append --xml "
<p:sp><p:nvSpPr><p:cNvPr id=\"$id\" name=\"Deco$id\"/><p:cNvSpPr/><p:nvPr/></p:nvSpPr>
<p:spPr><a:xfrm><a:off x=\"$x\" y=\"$y\"/><a:ext cx=\"$cx\" cy=\"$cy\"/></a:xfrm><a:prstGeom prst=\"ellipse\"><a:avLst/></a:prstGeom><a:solidFill><a:srgbClr val=\"$color\"><a:alpha val=\"$alpha\"/></a:srgbClr></a:solidFill><a:ln><a:noFill/></a:ln></p:spPr>
<p:txBody><a:bodyPr/><a:lstStyle/><a:p><a:endParaRPr/></a:p></p:txBody></p:sp>"; }
bar() { local slide="$1" id="$2" x="$3" y="$4" cy="$5" pct="$6" color="$7"
  local w=$(( 9000000 * pct / 100 ))
  officecli raw-set "$OUT" "$slide" --xpath "//p:cSld/p:spTree" --action append --xml "
<p:sp><p:nvSpPr><p:cNvPr id=\"$id\" name=\"Bar$id\"/><p:cNvSpPr/><p:nvPr/></p:nvSpPr>
<p:spPr><a:xfrm><a:off x=\"$x\" y=\"$y\"/><a:ext cx=\"$w\" cy=\"$cy\"/></a:xfrm><a:prstGeom prst=\"roundRect\"><a:avLst><a:gd name=\"adj\" fmla=\"val 50000\"/></a:avLst></a:prstGeom><a:solidFill><a:srgbClr val=\"$color\"/></a:solidFill><a:ln><a:noFill/></a:ln></p:spPr>
<p:txBody><a:bodyPr/><a:lstStyle/><a:p><a:endParaRPr/></a:p></p:txBody></p:sp>"; }
HDR() { local s="$1"; textbox "$s" 200 800000 950000 10592000 800000 3000 FFFFFF "$2"
  subtext "$s" 201 800000 1750000 10592000 450000 1300 8B95A2 "$3"; }
PARTTAG() { local slide="$1" id="$2" txt="$3"
  officecli raw-set "$OUT" "$slide" --xpath "//p:cSld/p:spTree" --action append --xml "
<p:sp><p:nvSpPr><p:cNvPr id=\"$id\" name=\"Part$id\"/><p:cNvSpPr txBox=\"1\"/><p:nvPr/></p:nvSpPr>
<p:spPr><a:xfrm><a:off x=\"800000\" y=\"400000\"/><a:ext cx=\"3600000\" cy=\"450000\"/></a:xfrm><a:prstGeom prst=\"roundRect\"><a:avLst><a:gd name=\"adj\" fmla=\"val 30000\"/></a:avLst></a:prstGeom><a:solidFill><a:srgbClr val=\"00B4D8\"/></a:solidFill><a:ln><a:noFill/></a:ln></p:spPr>
<p:txBody><a:bodyPr wrap=\"square\" anchor=\"ctr\"/><a:lstStyle/><a:p><a:pPr algn=\"ctr\"/><a:r><a:rPr lang=\"zh-CN\" sz=\"1200\" b=\"1\" dirty=\"0\"><a:solidFill><a:srgbClr val=\"0A1628\"/></a:solidFill><a:latin typeface=\"Microsoft YaHei\"/><a:cs typeface=\"Microsoft YaHei\"/></a:rPr><a:t>$txt</a:t></a:r></a:p></p:txBody></p:sp>"; }
row() { local slide="$1" id="$2" x="$3" y="$4" cx="$5" cy="$6" label="$7" val="$8" color="$9"
  officecli raw-set "$OUT" "$slide" --xpath "//p:cSld/p:spTree" --action append --xml "
<p:sp><p:nvSpPr><p:cNvPr id=\"$id\" name=\"Row$id\"/><p:cNvSpPr/><p:nvPr/></p:nvSpPr>
<p:spPr><a:xfrm><a:off x=\"$x\" y=\"$y\"/><a:ext cx=\"$cx\" cy=\"$cy\"/></a:xfrm><a:prstGeom prst=\"roundRect\"><a:avLst><a:gd name=\"adj\" fmla=\"val 30000\"/></a:avLst></a:prstGeom><a:solidFill><a:srgbClr val=\"13203A\"/></a:solidFill><a:ln w=\"6350\"><a:solidFill><a:srgbClr val=\"$color\"/></a:solidFill></a:ln></p:spPr>
<p:txBody><a:bodyPr wrap=\"square\" lIns=\"182880\" tIns=\"91440\" rIns=\"182880\" bIns=\"91440\" anchor=\"ctr\"/><a:lstStyle/>
<a:p><a:pPr algn=\"l\"/><a:r><a:rPr lang=\"zh-CN\" sz=\"1200\" dirty=\"0\"><a:solidFill><a:srgbClr val=\"C7D0DB\"/></a:solidFill><a:latin typeface=\"Microsoft YaHei\"/><a:cs typeface=\"Microsoft YaHei\"/></a:rPr><a:t>$label</a:t></a:r></a:p>
</p:txBody></p:sp>"
  officecli raw-set "$OUT" "$slide" --xpath "//p:cSld/p:spTree" --action append --xml "
<p:sp><p:nvSpPr><p:cNvPr id=\"$((id+500))\" name=\"Val$id\"/><p:cNvSpPr txBox=\"1\"/><p:nvPr/></p:nvSpPr>
<p:spPr><a:xfrm><a:off x=\"$((x+cx-2200000))\" y=\"$y\"/><a:ext cx=\"2000000\" cy=\"$cy\"/></a:xfrm><a:prstGeom prst=\"rect\"><a:avLst/></a:prstGeom><a:noFill/><a:ln><a:noFill/></a:ln></p:spPr>
<p:txBody><a:bodyPr wrap=\"square\" anchor=\"ctr\"/><a:lstStyle/><a:p><a:pPr algn=\"r\"/><a:r><a:rPr lang=\"zh-CN\" sz=\"1300\" b=\"1\" dirty=\"0\"><a:solidFill><a:srgbClr val=\"$color\"/></a:solidFill><a:latin typeface=\"Microsoft YaHei\"/><a:cs typeface=\"Microsoft YaHei\"/></a:rPr><a:t>$val</a:t></a:r></a:p></p:txBody></p:sp>"; }
compare_col() { local slide="$1" id="$2" x="$3" y="$4" cx="$5" cy="$6" title="$7" body="$8" accent="$9"
  officecli raw-set "$OUT" "$slide" --xpath "//p:cSld/p:spTree" --action append --xml "
<p:sp><p:nvSpPr><p:cNvPr id=\"$id\" name=\"Cmp$id\"/><p:cNvSpPr/><p:nvPr/></p:nvSpPr>
<p:spPr><a:xfrm><a:off x=\"$x\" y=\"$y\"/><a:ext cx=\"$cx\" cy=\"$cy\"/></a:xfrm><a:prstGeom prst=\"roundRect\"><a:avLst><a:gd name=\"adj\" fmla=\"val 6000\"/></a:avLst></a:prstGeom><a:solidFill><a:srgbClr val=\"152238\"/></a:solidFill><a:ln w=\"19050\"><a:solidFill><a:srgbClr val=\"$accent\"/></a:solidFill></a:ln></p:spPr>
<p:txBody><a:bodyPr wrap=\"square\" lIns=\"228600\" tIns=\"182880\" rIns=\"228600\" bIns=\"182880\" anchor=\"t\"/><a:lstStyle/>
<a:p><a:pPr algn=\"ctr\"/><a:r><a:rPr lang=\"zh-CN\" sz=\"1800\" b=\"1\" dirty=\"0\"><a:solidFill><a:srgbClr val=\"$accent\"/></a:solidFill><a:latin typeface=\"Microsoft YaHei\"/><a:cs typeface=\"Microsoft YaHei\"/></a:rPr><a:t>$title</a:t></a:r></a:p>
<a:p><a:pPr algn=\"l\"/><a:endParaRPr lang=\"zh-CN\" sz=\"600\"/></a:p>
<a:p><a:pPr algn=\"l\"/><a:r><a:rPr lang=\"zh-CN\" sz=\"1150\" dirty=\"0\"><a:solidFill><a:srgbClr val=\"C7D0DB\"/></a:solidFill><a:latin typeface=\"Microsoft YaHei\"/><a:cs typeface=\"Microsoft YaHei\"/></a:rPr><a:t>$body</a:t></a:r></a:p>
</p:txBody></p:sp>"; }

#################### 示例: 3 页骨架（复制后替换为你的内容）####################
echo "  -> Slide 1: 封面"
officecli add "$OUT" / --type slide
officecli raw-set "$OUT" /slide[1] --xpath "//p:cSld" --action prepend --xml "$BG_DARK"
deco /slide[1] 100 8500000 -1200000 4800000 4800000 00B4D8 8000
deco /slide[1] 101 -800000 4500000 3200000 3200000 E0AAFF 6000
textbox /slide[1] 103 800000 1500000 10500000 1400000 4000 FFFFFF "标题放这里"
subtext /slide[1] 105 800000 3700000 10500000 500000 1400 8B95A2 "副标题放这里"

echo "  -> Slide 2: 内容页示例"
add_slide /slide[2]
PARTTAG /slide[2] 10 "第一部分 · 标签"
HDR /slide[2] "本页标题" "本页副标题"
card /slide[2] 210 700000 2050000 3300000 2600000 "卡片1" "说明文字" 00B4D8
card /slide[2] 211 4150000 2050000 3300000 2600000 "卡片2" "说明文字" E0AAFF
card /slide[2] 212 7600000 2050000 3300000 2600000 "卡片3" "说明文字" FFD166
footnote /slide[2] 230 "页脚说明放这里"

echo "  -> Slide 3: 表格示例"
add_slide /slide[3]
PARTTAG /slide[3] 10 "第二部分 · 标签"
HDR /slide[3] "检索结果演示" "Query 示例"
row /slide[3] 210 700000 2150000 10550000 700000 "#1 技能名" "0.0428" 00B4D8
row /slide[3] 211 700000 2920000 10550000 700000 "#2 技能名" "0.0402" E0AAFF
row /slide[3] 212 700000 3690000 10550000 700000 "#3 技能名" "0.039" FFD166
footnote /slide[3] 230 "数据用 matcher.search() 实跑结果, 不要编造"

echo "DONE: $OUT"
echo "# 渲染校验: for p in \$(seq 1 3); do officecli view \"$OUT\" screenshot -o /tmp/p\$p.png --page \$p; done"
echo "# 合规校验: officecli validate \"$OUT\""
