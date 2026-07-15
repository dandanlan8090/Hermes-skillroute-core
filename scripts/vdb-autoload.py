"""vdb 启动预热 + 索引过期检测 + 自动重建

用途：
  1. 预热 Chroma 连接（消除首查延迟）
  2. 检测 skills/ 是否比索引新
  3. P2: 新增/删除技能时自动重建 IDF 权重
  4. 检测到过期时自动重建（--auto）或提示

用法：
  python3 vdb-autoload.py            # 预热 + 被动检测，过期提示
  python3 vdb-autoload.py --auto     # 预热 + 过期自动重建（推荐开机/install 用）
  python3 vdb-autoload.py --force    # 强制全量重建（不管是否过期）
  python3 vdb-autoload.py --check    # 只检测不预热

放置位置：~/.hermes/scripts/vdb-autoload.py
install.sh 安装最后执行一次 `--auto`。
"""

import sys, os, argparse, subprocess

VDB_DIR = os.path.expanduser("~/.hermes/vdb")
HERMES_HOME = os.path.expanduser("~/.hermes")
ENV_PATH = os.path.join(HERMES_HOME, ".env")
SCRIPTS_DIR = os.path.dirname(os.path.abspath(__file__))

# 确保 vdb 在 Python 路径
if VDB_DIR not in sys.path:
    sys.path.insert(0, VDB_DIR)

# 从 .env 读取 API Key
if not os.environ.get("SILICONFLOW_API_KEY"):
    if os.path.exists(ENV_PATH):
        for line in open(ENV_PATH):
            if line.startswith("SILICONFLOW_API_KEY="):
                val = line.split("=", 1)[1].strip().strip("\"'")
                os.environ["SILICONFLOW_API_KEY"] = val
                break


def warmup():
    """预热 Chroma 连接。"""
    try:
        from matcher import _get_collection, is_healthy
        _get_collection()
        return is_healthy()
    except Exception as e:
        print(f"[vdb] 预热失败: {e}")
        return False


def check_stale():
    """检查索引是否过期。"""
    try:
        from indexer import check_index_stale
        stale, reason = check_index_stale()
        return stale, reason
    except Exception as e:
        return True, str(e)


def rebuild():
    """全量重建索引（含 IDF 重算）。"""
    venv_python = os.path.join(VDB_DIR, ".venv", "bin", "python3")
    if not os.path.exists(venv_python):
        venv_python = "python3"
    cmd = [
        venv_python, "-c",
        "from indexer import build_index; build_index(force=True)"
    ]
    print("[vdb]   正在重建索引（含 IDF）...")
    result = subprocess.run(cmd, cwd=VDB_DIR, capture_output=True, text=True, timeout=300)
    for line in result.stdout.strip().split("\n"):
        print(f"         {line}")
    if result.returncode != 0:
        print(f"[vdb]   ❌ 重建失败: {result.stderr[:200]}")
        return False
    print("[vdb]   ✅ 索引重建完成")
    return True


def process_context():
    """SpanKind 上下文分类: 给最近消息打 EXECUTED/DATA/ARGUMENT 标签.

    借鉴 dcg 的 SpanKind 命令上下文分类范式, 用于 Agent 长对话压缩/复用.
    真实数据: Data 占 75-85% token, 分类压缩省 75-83% 且执行上下文零损失.
    私有 side table (message_tags.db), 不侵入 hermes-agent 核心.
    """
    proc = os.path.join(SCRIPTS_DIR, "context-processor.py")
    if not os.path.exists(proc):
        print("[context] ⚠ context-processor.py 不存在, 跳过")
        return
    print("[context] 正在分类最近消息 (SpanKind)...")
    try:
        result = subprocess.run(
            [sys.executable, proc, "200"],
            capture_output=True, text=True, timeout=120)
        for line in result.stdout.strip().split("\n"):
            print(f"         {line}")
        if result.returncode != 0:
            print(f"[context]   ⚠ 分类失败: {result.stderr[:200]}")
    except Exception as e:
        print(f"[context]   ⚠ 分类异常: {e}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="vdb 预热 + 索引检测 + 重建")
    parser.add_argument("--force", action="store_true", help="强制全量重建（忽略过期检测）")
    parser.add_argument("--auto", action="store_true", help="预热 + 过期自动重建")
    parser.add_argument("--check", action="store_true", help="只检测不预热")
    parser.add_argument("--process-context", action="store_true",
                        help="运行 SpanKind 上下文分类 (最近 200 条消息打标签)")
    args = parser.parse_args()

    if args.process_context:
        process_context()
        sys.exit(0)

    if args.check:
        stale, reason = check_stale()
        if stale:
            print(f"[vdb] 索引过期: {reason}")
            print("[vdb] ⚠  IDF 基于当前技能集计算，新增/删除技能后 IDF 不准确。")
            print("[vdb] 运行：python3 vdb-autoload.py --auto  自动重建")
        else:
            print("[vdb] ✅ 索引最新（IDF 与你当前技能集匹配）")
        sys.exit(0 if not stale else 1)

    if args.force:
        print("[vdb] 🔨 强制全量重建（--force）")
        ok = warmup()
        rebuild()
        sys.exit(0)

    # --auto 或不带参数：预热 + 过期检测
    ok = warmup()
    if ok:
        print("[vdb] ✅ Chroma 预热完成")
    else:
        print("[vdb] ⚠️  Chroma 不可用，vdb 将降级为 skills_list 回退")
        # 上下文分类不依赖 chroma, 仍运行 (读写 state.db, 与 vdb 无关)
        if args.auto:
            process_context()
        sys.exit(1)

    stale, reason = check_stale()
    if stale:
        print(f"[vdb] ⚠️  索引过期: {reason}")
        print(f"    IDF 需要基于当前全部技能重新计算。")
        if args.auto:
            rebuild()
            process_context()
        else:
            print(f"    运行下命令自动重建：")
            print("       python3 vdb-autoload.py --auto")
    else:
        print(f"[vdb] ✅ 索引最新（IDF 与当前技能集一致）")
        if args.auto:
            process_context()
