#!/usr/bin/env bash
# vdb 环境初始化脚本（供 install.sh 调用或独立运行）
#
# 用法:
#   bash scripts/init-vdb.sh            复制 vdb/.env.example → ~/.hermes/.env（如果不存在）
#   bash scripts/init-vdb.sh --skip-env 跳过 .env 处理（安装脚本已处理）
#   bash scripts/init-vdb.sh --profile work  重建指定 profile 的技能索引
#
# 独立运行（如果 vdb/ 已经复制到 ~/.hermes/vdb/）：
#   bash ~/.hermes/scripts/init-vdb.sh
#   bash ~/.hermes/scripts/init-vdb.sh --profile work

set -euo pipefail

VDB_DST="${HOME}/.hermes/vdb"
HERMES_DIR="${HOME}/.hermes"
SKIP_ENV=false
PROFILE=""

while [ $# -gt 0 ]; do
    case "$1" in
        --skip-env) SKIP_ENV=true ;;
        --profile) PROFILE="${2:-}"; [ -n "$PROFILE" ] || { echo "--profile 需要参数"; exit 2; }; shift ;;
        --profile=*) PROFILE="${1#*=}" ;;
        *) echo "未知参数: $1"; exit 2 ;;
    esac
    shift
done

if [ -n "$PROFILE" ]; then
    export HERMES_SKILL_DIR="${HOME}/.hermes/profiles/${PROFILE}/skills"
    echo "==> profile: $PROFILE"
    echo "    技能目录: $HERMES_SKILL_DIR"
fi

echo "==> 1. 检查 vdb 工具链"
if [ ! -f "${VDB_DST}/sparse.py" ]; then
    echo "错误：找不到 ~/.hermes/vdb/sparse.py"
    echo "请先运行 install.sh 或手动复制 vdb/ 到 $VDB_DST"
    exit 1
fi
echo "  ✓ vdb 工具链已就绪"

echo "==> 2. 创建虚拟环境"
if [ -d "${VDB_DST}/.venv" ]; then
    echo "  .venv 已存在，跳过"
else
    python3 -m venv "${VDB_DST}/.venv"
    echo "  ✓ .venv 已创建"
fi

source "${VDB_DST}/.venv/bin/activate"
echo "==> 3. 安装依赖"
pip install -q chromadb openai python-dotenv 2>&1 | tail -1
echo "  ✓ 依赖安装完成"

if ! $SKIP_ENV; then
    echo "==> 4. 配置 API Key"
    if [ ! -f "${HERMES_DIR}/.env" ]; then
        if [ -f "${HERMES_DIR}/.env.example" ]; then
            cp "${HERMES_DIR}/.env.example" "${HERMES_DIR}/.env"
            echo "  ✓ .env 模板已创建"
            echo "  ⚠ 请编辑 ${HERMES_DIR}/.env，填入你的 SILICONFLOW_API_KEY"
        else
            echo "  ⚠ 未找到 .env.example，请手动创建 ${HERMES_DIR}/.env"
            echo "    格式: SILICONFLOW_API_KEY=sk-your-key"
        fi
    else
        echo "  ✓ .env 已存在，跳过"
    fi
fi

echo "==> 5. 重建索引（含 IDF）"
cd "$VDB_DST"
PYTHONPATH="$PWD" python3 "${HERMES_DIR}/scripts/vdb-autoload.py" --auto
echo ""

echo "=========================================="
echo " ✅ vdb 初始化完成"
echo "    chroma/ 目录已创建（向量存储）"
echo "    重启 Hermes 会话即可自动使用 vdb 检索"
echo "=========================================="
