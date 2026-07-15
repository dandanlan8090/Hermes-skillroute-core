#!/usr/bin/env python3
"""
Hermes Skill Index Size Measurer — 实测脚本
对比 auto 与 focus 模式下 <available_skills> 区块的真实字节数。

修复点（前人踩坑）：
  1. Python 关键字必须小写（import/from/if），否则 SyntaxError。
  2. 不能依赖 config.set("agent.coding_context", mode) —— build_skills_system_prompt
     不直接读 config，必须显式传 compact_categories 参数。
  3. coding_compact_skill_categories() 在非 coding 工作区（如 $HOME，非 git repo）
     返回空集 → 降级不激活 → 测出 0 节省（假阴性）。直接取
     _NON_CODING_SKILL_CATEGORIES 作为测试数据传入，剥离环境依赖。

用法：
  python3 measure_skill_index.py
"""
import os
import re
import sys
from pathlib import Path

# ── 路径引导 ──────────────────────────────────────────────────────────────
AGENT_ROOT = Path.home() / ".hermes" / "hermes-agent"
VENV_SITE = AGENT_ROOT / "venv" / "lib"
sp = sorted(VENV_SITE.glob("python*/site-packages"))
for p in (str(sp[0]) if sp else "", str(AGENT_ROOT)):
    if p and p not in sys.path:
        sys.path.insert(0, p)

try:
    from agent.prompt_builder import build_skills_system_prompt
    from agent.coding_context import _NON_CODING_SKILL_CATEGORIES as NON_CODING
except ImportError as e:
    print(f"❌ 导入失败: {e}")
    print(f"  site-packages: {sp}")
    sys.exit(1)


def extract_skills_block(full_prompt: str) -> str:
    m = re.search(r"<available_skills>\n(.*?)\n</available_skills>", full_prompt, re.DOTALL)
    if m:
        return "<available_skills>\n" + m.group(1) + "\n</available_skills>"
    return full_prompt


def measure(label: str, compact_categories: "frozenset[str] | None") -> dict:
    full = build_skills_system_prompt(
        available_tools=set(),
        available_toolsets=set(),
        compact_categories=compact_categories,
    )
    if not full:
        return {"label": label, "bytes": 0, "lines": 0, "desc": 0, "block": "(empty)"}
    block = extract_skills_block(full)
    desc = len(re.findall(r"^\s+-\s+\S+: .+", block, re.MULTILINE))
    return {
        "label": label,
        "bytes": len(block.encode("utf-8")),
        "lines": block.count("\n"),
        "desc": desc,
        "block": block,
    }


def main():
    auto = measure("auto (默认)", None)
    focus = measure("focus (降级非编码类)", frozenset(NON_CODING))

    print("=" * 62)
    print("  Hermes Skill Index Size Measurer (实测)")
    print("=" * 62)
    print(f"\n  NON_CODING_SKILL_CATEGORIES ({len(NON_CODING)} 类):")
    for c in NON_CODING:
        print(f"    · {c}")

    print(f"\n  {'模式':<26} {'bytes':>8} {'行数':>5} {'desc技能':>8}")
    print(f"  {'─'*26} {'─'*8} {'─'*5} {'─'*8}")
    print(f"  {auto['label']:<26} {auto['bytes']:>8} {auto['lines']:>5} {auto['desc']:>8}")
    print(f"  {focus['label']:<26} {focus['bytes']:>8} {focus['lines']:>5} {focus['desc']:>8}")

    saved = auto["bytes"] - focus["bytes"]
    pct = (saved / auto["bytes"]) * 100 if auto["bytes"] > 0 else 0
    print(f"\n  💾 节省: {saved:,} bytes (~{int(saved/3):,} tokens) = {pct:.1f}%")
    print(f"  降级 desc 行: {auto['desc'] - focus['desc']}")

    # 列出被降级的类与技能
    auto_cats = set(re.findall(r"  (\S+):", auto["block"]))
    focus_cats = set(re.findall(r"  (\S+):", focus["block"]))
    demoted = [
        c for c in (auto_cats & focus_cats)
        if f"{c} [names only]" in focus["block"]
    ]
    if demoted:
        print(f"\n  被降级类 ({len(demoted)}):")
        for c in sorted(demoted):
            line = [l for l in focus["block"].split("\n") if f"{c} [names only]" in l]
            print(f"    {line[0].strip() if line else c}")


if __name__ == "__main__":
    main()
