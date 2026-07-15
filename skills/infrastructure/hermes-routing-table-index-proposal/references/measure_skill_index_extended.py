#!/usr/bin/env python3
"""
Hermes Skill Index Size Measurer — Extended
实测 full / names-only / routing-only 三种 index_mode 下 <available_skills> 区块大小。
直接调用真实 prompt_builder.build_skills_system_prompt(index_mode=...)，无伪代码。

用法:
  python3 measure_skill_index_extended.py            # 测当前 config 模式
  python3 measure_skill_index_extended.py --all      # 测全部三模式并对比
  python3 measure_skill_index_extended.py --mode names-only
  python3 measure_skill_index_extended.py --all --json > out.json
"""
import argparse
import json
import os
import re
import sys
from pathlib import Path

AGENT_ROOT = Path.home() / ".hermes" / "hermes-agent"
VENV_SITE = AGENT_ROOT / "venv" / "lib"
sp = sorted(VENV_SITE.glob("python*/site-packages"))
for p in (str(sp[0]) if sp else "", str(AGENT_ROOT)):
    if p and p not in sys.path:
        sys.path.insert(0, p)

try:
    from agent.prompt_builder import build_skills_system_prompt
except ImportError as e:
    print(f"❌ 导入失败: {e}")
    sys.exit(1)


def extract_block(full: str) -> str:
    m = re.search(r"<available_skills>\n(.*?)\n</available_skills>", full, re.DOTALL)
    return "<available_skills>\n" + m.group(1) + "\n</available_skills>" if m else full


def measure(mode: str) -> dict:
    # 真实调用：prompt_builder 内部自己扫描 skills/ + external_dirs
    full = build_skills_system_prompt(
        available_tools=None,
        available_toolsets=None,
        compact_categories=None,
        index_mode=mode,
    )
    if not full:
        return {"mode": mode, "bytes": 0, "lines": 0, "desc": 0, "names": 0, "block": "(empty)"}
    block = extract_block(full)
    desc = len(re.findall(r"^\s+-\s+[\w:-]+: .+", block, re.MULTILINE))
    names = len(re.findall(r"^\s+-\s+[\w:`→\- ]+", block, re.MULTILINE))
    return {
        "mode": mode,
        "bytes": len(block.encode("utf-8")),
        "lines": block.count("\n"),
        "desc": desc,
        "names": names,
        "block": block,
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--mode", choices=["full", "names-only", "routing-only"])
    ap.add_argument("--all", action="store_true")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    current = os.environ.get("HERMES_SKILLS_INDEX_MODE", "").strip().lower()
    if not current:
        try:
            from hermes_cli.config import load_config
            current = str((load_config() or {}).get("agent", {}).get("skills_index_mode", "full")).strip().lower()
        except Exception:
            current = "full"

    modes = ["full", "names-only", "routing-only"] if (args.all or not args.mode) else [args.mode]
    if not args.all and not args.mode:
        modes = [current]

    results = {m: measure(m) for m in modes}

    if args.json:
        print(json.dumps(results, ensure_ascii=False, indent=2))
        return

    print("=" * 64)
    print("  Hermes Skill Index Size Measurer — Extended")
    print("=" * 64)
    print(f"  当前 config skills_index_mode = {current}")
    print(f"\n  {'模式':<14}{'bytes':>9}{'行数':>6}{'desc技能':>9}{'行数':>6}")
    print(f"  {'─'*14}{'─'*9}{'─'*6}{'─'*9}{'─'*6}")
    for m, r in results.items():
        print(f"  {m:<14}{r['bytes']:>9}{r['lines']:>6}{r['desc']:>9}{r['names']:>6}")

    if len(results) > 1 and "full" in results:
        base = results["full"]["bytes"]
        print(f"\n  对比 full (基准 {base:,} bytes):")
        for m, r in results.items():
            d = r["bytes"] - base
            pct = (d / base * 100) if base else 0
            print(f"    {m:<14} {r['bytes']:>9,}  ({d:+,}  {pct:+.1f}%)")
        saved = base - results.get("names-only", {}).get("bytes", base)
        saved2 = base - results.get("routing-only", {}).get("bytes", base)
        if "names-only" in results:
            print(f"  → names-only 节省 ~{saved:,}B (~{int(saved/3):,} tokens)")
        if "routing-only" in results:
            print(f"  → routing-only 节省 ~{saved2:,}B (~{int(saved2/3):,} tokens)")

    if not args.json:
        print("\n  (预览用 --json 看完整区块)")


if __name__ == "__main__":
    main()
