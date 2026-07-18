#!/usr/bin/env bash
# 调用 vdb 目录下的 benchmark 脚本
# 该脚本必须在 vdb 目录下运行（依赖 matcher.py/embed.py）
set -e
cd ~/.hermes/vdb
source .venv/bin/activate
python3 eval/benchmark_rrf.py "$@"
