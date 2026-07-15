"""Skill 盲测工具 — prompt 生成 + 结果收录 + verdict 判决。

不是 vdb 索引对象，是 skill 质量保证工具（不进 vdb）。

设计（来自 dzhng/skills eval-skills）:
  1. Inputs: target skill 名 + golden case（input + bar）
  2. Blind run prompt 生成 (context-free, 不给 bar）
  3. 用户把 prompt 给 fresh hermes 运行，贴回结果
  4. Judge: 用户运行 judge prompt（给 artifact + bar + skill 第一性原理）

用法:
  # 生成单个 case 的盲测 prompt
  python3 eval_skill.py --skill agent-collaboration-workflow --case 1 --prompt blind

  # 生成单个 case 的 judge prompt（需要先有 artifact）
  python3 eval_skill.py --skill agent-collaboration-workflow --case 1 --prompt judge --artifact /tmp/artifact.txt

  # 列已有测试套
  python3 eval_skill.py --list

cases/*.json 格式:
  [
    {
      "name": "test-name",
      "input": "用户的 query 输入",
      "bar": "通过标准（judge 用这个判 pass/fail）",
      "smells": ["失败特征 1", "失败特征 2"]
    }
  ]
"""

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

HERMES_HOME = Path.home() / ".hermes"
VDB_DIR = HERMES_HOME / "vdb"
EVAL_DIR = VDB_DIR / "eval"
CASES_DIR = EVAL_DIR / "cases"
PROMPTS_DIR = EVAL_DIR / "prompts"
RESULTS_DIR = EVAL_DIR / "results"

DEFAULT_SUITES = {
    "hermes-agent-skill-authoring": "skill_authoring.json",
}


def _ensure_dirs():
    for d in [CASES_DIR, PROMPTS_DIR, RESULTS_DIR]:
        d.mkdir(parents=True, exist_ok=True)


def _load_skill_md(skill_name: str) -> str | None:
    """从 vdb 索引取 skill_path，加载 SKILL.md。"""
    sys.path.insert(0, str(VDB_DIR))
    from matcher import _get_collection
    collection = _get_collection()
    result = collection.get(
        where={"skill_name": skill_name},
        include=["metadatas"],
    )
    if not result["metadatas"]:
        print(f"[eval] 找不到 skill: {skill_name}", file=sys.stderr)
        return None
    skill_path = result["metadatas"][0].get("skill_path")
    if not skill_path or not Path(skill_path).exists():
        print(f"[eval] skill 路径失效: {skill_path}", file=sys.stderr)
        return None
    return Path(skill_path).read_text(encoding="utf-8")


def _extract_first_principles(skill_md: str) -> str:
    """从 SKILL.md 抽'第一性原理'段。"""
    import re
    m = re.search(
        r"##\s*(?:1\.?|一[、.]|第一性原理|First Principles)\s*\n(.*?)(?=\n##\s*(?:2\.?|二[、.]|工作流|Workflow)|\Z)",
        skill_md, re.DOTALL
    )
    return m.group(1).strip()[:1500] if m else "(no first principles section found)"


def gen_blind_prompt(skill_name: str, case: dict) -> str:
    """生成盲测 prompt（context-free subagent 用）。"""
    skill_md = _load_skill_md(skill_name)
    if not skill_md:
        return f"[ERROR] skill {skill_name} not found"
    return (
        f"你是一个 fresh subagent，没有任何上下文。\n"
        f"你的任务：只使用以下 skill 回答用户的真实问题。\n"
        f"不要问用户问题，直接按 skill 定义执行。\n\n"
        f"--- BEGIN SKILL.md ({skill_name}) ---\n{skill_md}\n--- END SKILL.md ---\n\n"
        f"--- USER INPUT ---\n{case['input']}\n--- END USER INPUT ---\n\n"
        f"请输出最终结果。"
    )


def gen_judge_prompt(skill_name: str, case: dict, artifact: str) -> str:
    """生成 judge prompt（给 verdict 用）。"""
    skill_md = _load_skill_md(skill_name)
    if not skill_md:
        return f"[ERROR] skill {skill_name} not found"
    first_principles = _extract_first_principles(skill_md)
    return (
        f"你是 eval judge agent。只根据 bar 判 artifact pass/fail。\n\n"
        f"--- SKILL: {skill_name} ---\n"
        f"第一性原理:\n{first_principles}\n\n"
        f"--- CASE ---\n"
        f"Input: {case['input']}\n"
        f"Bar (通过标准): {case['bar']}\n"
        f"Smells (失败特征): {json.dumps(case.get('smells', []), ensure_ascii=False)}\n\n"
        f"--- ARTIFACT (盲测结果) ---\n{artifact}\n--- END ARTIFACT ---\n\n"
        f"请给出 verdict（pass/fail），引用 artifact 中具体证据。\n"
        f"如果 fail，对照 write-skills 的 9 个 failure modes 给出 defect 类型。"
    )


def list_suites() -> list[str]:
    return sorted(p.name for p in CASES_DIR.glob("*.json")) if CASES_DIR.exists() else []


def add_result(skill_name: str, case_name: str, verdict: str, notes: str = ""):
    """记录手动判定结果。"""
    _ensure_dirs()
    results_file = RESULTS_DIR / f"{skill_name}_results.json"
    if results_file.exists():
        results = json.loads(results_file.read_text(encoding="utf-8"))
    else:
        results = {"skill": skill_name, "cases": []}
    results["cases"].append({
        "case": case_name,
        "verdict": verdict,
        "notes": notes,
        "timestamp": datetime.now().isoformat(),
    })
    results_file.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[eval] 结果已记录: {results_file}")


def main():
    ap = argparse.ArgumentParser(description="Hermes skill 盲测工具")
    ap.add_argument("--skill", help="skill 名")
    ap.add_argument("--case", type=int, default=0, help="cases 索引（1-based）")
    ap.add_argument("--prompt", choices=["blind", "judge"], help="生成 prompt 类型")
    ap.add_argument("--artifact", help="artifact 文件路径（judge prompt 用）")
    ap.add_argument("--list", action="store_true", help="列已有测试套")
    ap.add_argument("--record", help="记录手动判定结果 (pass/fail)")
    ap.add_argument("--notes", default="", help="附加说明")
    args = ap.parse_args()

    _ensure_dirs()

    if args.list:
        for s in list_suites():
            print(s)
        return

    if args.prompt == "blind":
        cases_path = CASES_DIR / f"{args.skill}.json"
        if not cases_path.exists():
            # 试 DEFAULT_SUITES
            cases_file = DEFAULT_SUITES.get(args.skill)
            if cases_file:
                cases_path = CASES_DIR / cases_file
        if not cases_path.exists():
            ap.error(f"测试套不存在: {cases_path}")
        cases = json.loads(cases_path.read_text(encoding="utf-8"))
        idx = (args.case or 1) - 1
        case = cases[idx]
        prompt = gen_blind_prompt(args.skill, case)
        out_path = PROMPTS_DIR / f"{args.skill}_case{idx+1}_{case['name']}_blind.txt"
        out_path.write_text(prompt, encoding="utf-8")
        print(f"[eval] 盲测 prompt 已生成: {out_path}")
        print("=" * 50)
        print(prompt)
        return

    if args.prompt == "judge":
        if not args.artifact:
            ap.error("judge prompt 需要 --artifact 指定文件")
        cases_path = CASES_DIR / f"{args.skill}.json"
        if not cases_path.exists():
            cases_file = DEFAULT_SUITES.get(args.skill)
            if cases_file:
                cases_path = CASES_DIR / cases_file
        if not cases_path.exists():
            ap.error(f"测试套不存在: {cases_path}")
        cases = json.loads(cases_path.read_text(encoding="utf-8"))
        idx = (args.case or 1) - 1
        case = cases[idx]
        artifact = Path(args.artifact).read_text(encoding="utf-8")
        prompt = gen_judge_prompt(args.skill, case, artifact)
        out_path = PROMPTS_DIR / f"{args.skill}_case{idx+1}_{case['name']}_judge.txt"
        out_path.write_text(prompt, encoding="utf-8")
        print(f"[eval] judge prompt 已生成: {out_path}")
        print("=" * 50)
        print(prompt)
        return

    if args.record:
        add_result(args.skill, f"case{args.case}", args.record, args.notes)
        return

    ap.print_help()


if __name__ == "__main__":
    main()
