#!/usr/bin/env python3
"""
Hermes Skills Coverage Diagnoser — 目录 vs vdb 索引差集 + 失效软链检测
定位「路由表即索引」方向的硬阻塞：目录列出的技能里哪些 vdb 没索引到，
以及是否是失效符号链接造成的。

用法：
  python3 diagnose_skills_coverage.py
"""
import json
import os
import re
import sys
from pathlib import Path

HOME = Path.home()
HERMES = HOME / ".hermes"
AGENT_ROOT = HERMES / "hermes-agent"
VENV_SITE = AGENT_ROOT / "venv" / "lib"
sp = sorted(VENV_SITE.glob("python*/site-packages"))
for p in (str(sp[0]) if sp else "", str(AGENT_ROOT)):
    if p and p not in sys.path:
        sys.path.insert(0, p)


def get_catalog_names() -> set[str]:
    """从 build_skills_system_prompt 解析 available_skills 里的全部技能名。"""
    from agent.prompt_builder import build_skills_system_prompt
    full = build_skills_system_prompt(available_tools=None, available_toolsets=None, compact_categories=None)
    m = re.search(r"<available_skills>\n(.*?)\n</available_skills>", full, re.DOTALL)
    block = m.group(1) if m else full
    names: set[str] = set()
    for line in block.split("\n"):
        mm = re.match(r"\s+-\s+([\w:-]+):", line)
        if mm:
            names.add(mm.group(1))
        elif "[names only]:" in line:
            tail = line.split(":", 1)[1]
            for n in re.findall(r"[\w:-]+", tail):
                names.add(n)
    return names


def get_indexed_names() -> set[str]:
    state = json.loads((HERMES / "vdb" / "vdb_state.json").read_text())
    return set(state.get("skill_hashes", {}).keys())


def classify_symlinks(names: set[str]) -> dict:
    """对 catalog 中的每个名，判定在磁盘上是真实目录还是断链软链。"""
    result = {"real": [], "broken_symlink": [], "missing": []}
    skills_dir = HERMES / "skills"
    for n in sorted(names):
        p = skills_dir / n
        if p.is_symlink():
            try:
                target = p.resolve(strict=True)
                result["real"].append((n, str(target)))
            except (OSError, FileNotFoundError):
                result["broken_symlink"].append((n, os.readlink(p)))
        elif p.exists():
            result["real"].append((n, str(p)))
        else:
            result["missing"].append(n)
    return result


def main():
    catalog = get_catalog_names()
    indexed = get_indexed_names()

    print("=" * 60)
    print("  Hermes Skills Coverage Diagnoser")
    print("=" * 60)
    print(f"\n  available_skills 列出: {len(catalog)}")
    print(f"  vdb 已索引:           {len(indexed)}")

    only_catalog = sorted(catalog - indexed)
    only_vdb = sorted(indexed - catalog)
    print(f"\n  [catalog-only] 目录有 / vdb 无: {len(only_catalog)}")
    for n in only_catalog:
        print(f"    - {n}")
    print(f"\n  [vdb-only] vdb 有 / 目录无(幽灵): {len(only_vdb)}")
    for n in only_vdb:
        print(f"    - {n}")

    print("\n" + "-" * 60)
    print("  磁盘状态分类（解释 catalog-only 来自何处）:")
    cls = classify_symlinks(catalog)
    print(f"    真实目录/有效软链: {len(cls['real'])}")
    print(f"    失效软链(broken):  {len(cls['broken_symlink'])}")
    for n, tgt in cls["broken_symlink"]:
        print(f"      x {n} -> {tgt}  (目标不存在)")
    print(f"    完全缺失:           {len(cls['missing'])}")

    if cls["broken_symlink"]:
        print("\n  ! 失效软链是 vdb 覆盖缺口的根因：")
        print("    prompt_builder 读历史快照仍列出它们，但 vdb 的 rglob('SKILL.md')")
        print("    跟进断链拿不到文件 -> 漏索引。这是「路由表即索引」的硬阻塞。")


if __name__ == "__main__":
    main()
