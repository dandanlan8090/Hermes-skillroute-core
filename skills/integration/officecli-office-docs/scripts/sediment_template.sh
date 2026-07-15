#!/bin/bash
# 反向沉淀：把 officecli 做出来的好成品存回本 skill 的 examples/ 模板库。
# 用法: bash ~/.hermes/skills/integration/officecli-office-docs/scripts/sediment_template.sh --confirmed <成品文件> <子目录:root|word|excel|ppt> <场景名>
# 例:  bash sediment_template.sh --confirmed ~/Q3汇报.pptx ppt q3-business-review
#
# 🛑 沉淀闸门：必须显式传 --confirmed（代表用户已确认成品 OK）。
#    缺该 flag 直接退出，不执行任何 cp/dump。这是 SKILL.md 中"成品 OK 才能沉淀"铁律的执行级强制。
#
# 行为: 复制成品 + dump 可复现蓝图(json) + 提示手动在 INDEX.md 追加一行。
set -euo pipefail
CONFIRMED=0
if [ "${1:-}" = "--confirmed" ]; then
  CONFIRMED=1
  shift
fi
SRC="${1:-}"
SUB="${2:-ppt}"
NAME="${3:-}"
if [ "$CONFIRMED" -ne 1 ]; then
  echo "🛑 沉淀闸门未过：必须在用户显式确认成品 OK 之后才能沉淀。" >&2
  echo "   用法: $0 --confirmed <成品文件> <子目录> <场景名>" >&2
  echo "   (用户 2026-07-13 明确：模板沉淀需要交付完成，成品OK才能沉淀模板)" >&2
  exit 2
fi
if [ -z "$SRC" ] || [ -z "$NAME" ]; then
  echo "用法: $0 --confirmed <成品文件> <子目录:root|word|excel|ppt> <场景名>" >&2
  exit 1
fi
EXDIR=~/.hermes/skills/integration/officecli-office-docs/examples
DEST="$EXDIR/$SUB"
mkdir -p "$DEST"
cp "$SRC" "$DEST/$NAME.${SRC##*.}"
echo "已存成品: $DEST/$NAME.${SRC##*.}"
# dump 蓝图（需 officecli 在 PATH）
if command -v officecli >/dev/null 2>&1; then
  officecli dump "$SRC" -o "$DEST/$NAME.json" 2>/dev/null && echo "已存蓝图: $DEST/$NAME.json" || echo "dump 失败(可跳过)"
else
  echo "officecli 未安装，跳过 dump 蓝图"
fi
echo ">>> 请手动在 $EXDIR/INDEX.md 对应表格追加一行: $NAME / 场景 / 生成方式"
