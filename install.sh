#!/usr/bin/env bash
# Hermes-skillroute-core 安装脚本
#
# 用法:
#   bash install.sh                    自动检测新装/存量
#   bash install.sh --force            强制全量覆盖（新装机）
#   bash install.sh --dry              预览变更不执行
#   bash install.sh --profile <name>   安装到指定 profile（如 --profile work）
#
# ⚠ profile 安全:
#   如果你在 profile 会话中运行 install.sh，默认会装到 ~/.hermes/（全局），
#   而不是你当前 profile 的目录 ~/.hermes/profiles/<name>/。
#   Hermes 对自身所处目录感知弱，请务必用 --profile 参数指定目标。
#
# 重点文件说明:
#   SOUL.md, memories/USER.md
#   如果是已有用户（~/.hermes/ 存在），这两个文件不会被覆盖。
#   新装机用户会全部复制。
#   已有用户请手动 diff 后按需合并。

set -uo pipefail

REPO_DIR="$(cd "$(dirname "$(readlink -f "$0" 2>/dev/null || realpath "$0" 2>/dev/null || echo "$0")")" && pwd)"
HERMES_DIR="${HOME}/.hermes"
IS_NEW=false
FORCE=false
DRY=false
PROFILE=""

# ── 参数 ────────────────────────────────────────────────────
while [ $# -gt 0 ]; do
    case "$1" in
        --force) FORCE=true ;;
        --dry)   DRY=true ;;
        --profile) PROFILE="${2:-}"; [ -n "$PROFILE" ] || { echo "--profile 需要参数"; exit 2; }; shift ;;
        --profile=*) PROFILE="${1#*=}" ;;
    esac
    shift
done

# ── Profile 检测 ──────────────────────────────────────────────
# 仅当显式传 --profile 时才切换到 profile 目录；不自动探测（避免无 hermes CLI 时报错）
if [ -n "$PROFILE" ]; then
    HERMES_DIR="${HOME}/.hermes/profiles/${PROFILE}"
    echo "  [profile] 目标: $HERMES_DIR"
    export HERMES_SKILL_DIR="${HERMES_DIR}/skills"
    echo "  [profile] 已设 HERMES_SKILL_DIR=$HERMES_SKILL_DIR"
fi

if [ ! -d "$HERMES_DIR" ]; then
    IS_NEW=true
fi

echo "=========================================="
echo " Hermes-skillroute-core — 安装脚本"
echo "=========================================="
echo ""
echo "  源目录: $REPO_DIR"
echo "  目标目录: $HERMES_DIR"
if [ "$IS_NEW" = true ]; then
    echo "  类型: 全新安装"
elif [ "$FORCE" = true ]; then
    echo "  类型: 强制覆盖"
else
    echo "  类型: 存量更新（保留核心配置）"
fi
echo ""

# ── 函数: 复制 ──────────────────────────────────────────────
do_cp() {
    local src="$1" dst="$2" label="$3"
    if [ "$DRY" = true ]; then
        echo "  [DRY] cp -r $src $dst  ← $label"
        return
    fi
    mkdir -p "$(dirname "$dst")"
    cp -rn "$src" "$dst" 2>/dev/null || cp -r "$src" "$dst"
    echo "  ✓ $label"
}

# ── 1. 核心元数据 ──────────────────────────────────────────
echo "── 核心元数据 ──"
do_cp "$REPO_DIR/SOUL.md" "$HERMES_DIR/SOUL.md" "SOUL.md（存量不覆盖）"
if [ "$IS_NEW" = true ] || [ "$FORCE" = true ]; then
    do_cp "$REPO_DIR/memories/USER.md" "$HERMES_DIR/memories/USER.md" "memories/USER.md"
    do_cp "$REPO_DIR/memories/FRAMEWORK_EVOLUTION.md" "$HERMES_DIR/memories/FRAMEWORK_EVOLUTION.md" "memories/FRAMEWORK_EVOLUTION.md"
else
    echo "  ⊘ memories/USER.md 跳过（存量保留）"
fi

# ── 2. 检索工具链 ────────────────────────────────────────
echo "── 检索工具链 (vdb/) ──"
if [ -d "$REPO_DIR/vdb" ]; then
    mkdir -p "$HERMES_DIR/vdb"
    for f in "$REPO_DIR"/vdb/*.py; do
        do_cp "$f" "$HERMES_DIR/vdb/$(basename "$f")" "vdb/$(basename "$f")"
    done
    [ -f "$REPO_DIR/vdb/idf_map.json" ] && do_cp "$REPO_DIR/vdb/idf_map.json" "$HERMES_DIR/vdb/idf_map.json" "vdb/idf_map.json"
    [ -f "$REPO_DIR/vdb/vdb_state.json" ] && do_cp "$REPO_DIR/vdb/vdb_state.json" "$HERMES_DIR/vdb/vdb_state.json" "vdb/vdb_state.json"
fi

# ── 3. 脚本 ────────────────────────────────────────────────
echo "── 脚本 (scripts/) ──"
if [ -d "$REPO_DIR/scripts" ]; then
    mkdir -p "$HERMES_DIR/scripts"
    for f in "$REPO_DIR"/scripts/*; do
        do_cp "$f" "$HERMES_DIR/scripts/$(basename "$f")" "scripts/$(basename "$f")"
    done
fi

# ── 4. 技能集（全量，只补充不覆盖）──────────────────────
echo "── 技能集 (skills/) ──"
if [ -d "$REPO_DIR/skills" ]; then
    mkdir -p "$HERMES_DIR/skills"
    # 逐目录复制，避免 git 大批量误收
    for d in "$REPO_DIR"/skills/*/; do
        name=$(basename "$d")
        do_cp "$d" "$HERMES_DIR/skills/$name" "skills/$name"
    done
    # 顶层散落 skill（无子目录）
    for f in "$REPO_DIR"/skills/*.md; do
        [ -f "$f" ] || continue
        do_cp "$f" "$HERMES_DIR/skills/$(basename "$f")" "skills/$(basename "$f")"
    done
fi

# ── 5. .env.example ───────────────────────────────────────
echo "── 环境变量 ──"
if [ -f "$REPO_DIR/.env.example" ] && [ ! -f "$HERMES_DIR/.env" ]; then
    do_cp "$REPO_DIR/.env.example" "$HERMES_DIR/.env" ".env（仅当不存在）"
else
    echo "  ⊘ .env 跳过（已存在或模板缺失）"
fi

# ── 6. .gitignore ─────────────────────────────────────────
echo "── 忽略规则 ──"
if [ -f "$REPO_DIR/.gitignore" ]; then
    do_cp "$REPO_DIR/.gitignore" "$HERMES_DIR/.gitignore" ".gitignore"
fi

# ── 完成 ────────────────────────────────────────────────────
echo ""
echo "=========================================="
echo " 安装完成"
if [ "$DRY" = true ]; then
    echo " （DRY 模式 — 未实际写入）"
else
    echo " 下一步:"
    echo "   cd ~/.hermes/vdb && bash init-vdb.sh   # 构建检索索引"
    echo "   hermes mcp list                        # 验证 MCP 接入"
fi
echo "=========================================="
