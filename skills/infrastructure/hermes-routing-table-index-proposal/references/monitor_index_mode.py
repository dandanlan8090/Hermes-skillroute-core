#!/usr/bin/env python3
"""
index_mode 在线监控 v2 — 核心 query 集 vdb 命中率守卫

用法:
  --update-baseline   重新建立核心 query 集基线 (core_queries_baseline.json)
  --check             与基线对比 (默认)
  --dry               仅输出回滚建议, 不执行回滚 (v2 新增)
  --json              输出 JSON
  --threshold N       回滚阈值(百分点), 默认 5.0

⚠ 重要边界 (务必读):
  index_mode 只改 available_skills 注入, **完全不碰 vdb 检索管线**
  (vdb/routing.py 与注入是两条独立管线, 见提案 §3)。因此:
    - 本监控测的是「vdb 索引 / 检索健康」(索引漂移、chroma 损坏、embed 变更等),
      它能证明 index_mode 切换 **没有引入检索回归** (构造上命中率应不变)。
    - 本监控 **抓不到** names-only 的真正风险: 模型失去 description 后的端到端
      选技能退化。那需要跑 LLM 端到端评估, 不在本脚本范围。
  结论: 本脚本是「无回归」证据, 不是「names-only 安全」证据。

告警投递: 本脚本只负责 stdout 输出报告; 超阈值/异常告警由调用方
  (cronjob deliver=feishu) 经已连通的飞书通道送达, 不内置 webhook 推送。

依赖: 必须在 ~/.hermes/vdb 的 .venv 下运行 (独立 chromadb 环境)
  cd ~/.hermes/vdb && .venv/bin/python <path>/monitor_index_mode.py
"""
import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

VDB_DIR = Path.home() / ".hermes" / "vdb"
if str(VDB_DIR) not in sys.path:
    sys.path.insert(0, str(VDB_DIR))
os.chdir(str(VDB_DIR))

from matcher import _get_collection, is_healthy
from embed import get_cloud_dense, calculate_sparse_score

RRF_K = 60
VEC_WEIGHT = 0.6
SPARSE_WEIGHT = 0.4

# 核心 query 集 (覆盖主要技能类别, 中英混合)。全部 expected 真实存在于索引。
RAW_QUERIES = [
    ("写个 TDD 测试", "hermes-tdd-workflow"),
    ("帮我 review 一下这段代码", "code-review-and-audit"),
    ("调试一下报错信息", "debugging-patterns"),
    ("部署 flask 到生产环境", "hermes-shipping-verification"),
    ("写一个 plan", "hermes-plan-workflow"),
    ("这个功能的设计方案", "spec-driven-development"),
    ("看看代码性能瓶颈", "performance-optimization"),
    ("git 怎么用 worktree 隔离分支", "hermes-git-worktree"),
    ("写个 agent skill", "hermes-agent-skill-authoring"),
    ("帮我搜索一下最新的 AI 论文", "arxiv"),
    ("合并代码到主分支", "hermes-git-worktree"),
    ("这个页面交互有点问题", "dogfood"),
    ("系统信息是什么", "system-admin"),
    ("先查 codebase 再改代码", "codebase-memory-first"),
    ("装一个服务到 ubuntu", "system-admin"),
    ("发一条推特", "xurl"),
    ("单元测试怎么写", "hermes-tdd-workflow"),
    ("代码简化一下", "code-simplification"),
    ("看看我的待办列表", "lark-task"),
    ("帮我排错", "debugging-patterns"),
    ("发布新版本", "hermes-shipping-verification"),
    ("Oracle Mode 调度一下", "hermes-oracle-mode"),
    ("YouTube 视频摘要", "youtube-content"),
    ("检查一下安全规范", "hermes-safety"),
    ("实验数据可视化分析", "jupyter-live-kernel"),
    ("消息既然你已发出去", "yuanbao"),
    ("配置 CI/CD 流水线", "ci-cd-and-automation"),
    ("写一个 API 接口文档", "api-and-interface-design"),
    ("重构老系统迁移方案", "deprecation-and-migration"),
    ("增量实现这个功能", "incremental-implementation"),
    ("debug the segmentation fault", "debugging-patterns"),
    ("search arxiv for NLP papers", "arxiv"),
    ("what's trending on twitter", "xurl"),
    ("video transcript and summary", "youtube-content"),
    ("segment objects in this image", "segment-anything-model"),
    ("generate music from text", "audiocraft-audio-generation"),
    ("find me a GIF for this", "gif-search"),
    ("send an email", "himalaya"),
    ("turn on the living room lights", "openhue"),
    ("query polymarket for prices", "polymarket"),
    ("check blog feed for updates", "blogwatcher"),
    ("knowledge base from wiki", "llm-wiki"),
    ("确认一下部署结果", "hermes-verification-rules"),
    ("不要编造任何信息", "hermes-truth-redline"),
    ("信息真实性确认", "hermes-truth-redline"),
    ("agent 协作架构", "agent-collaboration-workflow"),
    ("fault troubleshooting", "hermes-fault-troubleshooting"),
    ("开闭原则怎么落地", "doubt-driven-development"),
    ("写代码前先查官方文档", "source-driven-development"),
    ("用 openai 兼容模型的思考链", "openai-compat-thinking"),
    ("vdb 检索怎么工作的", "vdb-retrieval-pipeline"),
    ("并行派发多个 agent", "hermes-parallel-dispatch"),
    ("批量调研这个话题", "agent-reach"),
]


def eval_one(collection, query, expected):
    """RRF top1/top3 精确匹配 expected (复用线上 matcher 逻辑, 不碰 index_mode)。"""
    from indexer import TOP_K_CANDIDATES
    q_text = query if len(query) >= 15 else f"调用{query}。"
    query_dense = get_cloud_dense([q_text])[0]
    results = collection.query(
        query_embeddings=[query_dense],
        n_results=TOP_K_CANDIDATES,
        include=["distances", "metadatas"],
    )
    if not results["ids"][0]:
        return 0, 0, None, []
    distances = results["distances"][0]
    metadatas = results["metadatas"][0]
    candidates = []
    for dense_rank, (dist, meta) in enumerate(zip(distances, metadatas), start=1):
        dense_score = 1.0 - dist
        tag_sparse = meta.get("tag_sparse", "{}")
        sparse_score = calculate_sparse_score(query, tag_sparse)
        disable = json.loads(meta.get("disable_tags", "[]"))
        query_lower = query.lower().replace("_", " ")
        hit = False
        for d in disable:
            d_lower = d.lower().replace("_", " ")
            parts = d_lower.split()
            if len(parts) > 1 and all(p in query_lower for p in parts):
                hit = True
                break
            if d_lower in query_lower:
                hit = True
                break
        candidates.append({
            "skill_name": meta["skill_name"],
            "dense_score": dense_score,
            "sparse_score": sparse_score,
            "dense_rank": dense_rank,
            "disable_hit": hit,
        })
    valid = [c for c in candidates if not c["disable_hit"]]
    if not valid:
        return 0, 0, None, []
    sparse_sorted = sorted(valid, key=lambda c: c["sparse_score"], reverse=True)
    sparse_rank_map = {c["skill_name"]: i for i, c in enumerate(sparse_sorted, start=1)}
    rrf_results = []
    for c in valid:
        sr = sparse_rank_map.get(c["skill_name"], len(valid) + 1)
        rrf_score = 1.0 / (RRF_K + c["dense_rank"]) + 1.0 / (RRF_K + sr)
        rrf_results.append((c["skill_name"], rrf_score))
    rrf_sorted = sorted(rrf_results, key=lambda x: x[1], reverse=True)
    top1 = rrf_sorted[0][0] if rrf_sorted else None
    top3 = [x[0] for x in rrf_sorted[:3]] if rrf_sorted else []
    return (1 if top1 == expected else 0, 1 if expected in top3 else 0, top1, top3)


def build_core_queries(collection):
    data = collection.get(include=["metadatas"])
    indexed = {m["skill_name"] for m in data["metadatas"]}
    valid = [(q, exp) for q, exp in RAW_QUERIES if exp in indexed]
    missing = sorted({exp for q, exp in RAW_QUERIES if exp not in indexed})
    return valid, missing


def run_eval(collection, queries):
    t1 = t3 = 0
    detail = []
    for q, exp in queries:
        h1, h3, top1, top3 = eval_one(collection, q, exp)
        t1 += h1
        t3 += h3
        detail.append({
            "query": q, "expected": exp, "top1_hit": bool(h1),
            "top3_hit": bool(h3), "top1_skill": top1,
            "miss": None if (h1 or h3) else {"expected": exp, "top1": top1, "top3": top3},
        })
    n = len(queries)
    return {
        "n": n, "top1": t1, "top3": t3,
        "top1_pct": round(t1 / n * 100, 1) if n else 0.0,
        "top3_pct": round(t3 / n * 100, 1) if n else 0.0,
        "detail": detail,
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--update-baseline", action="store_true", help="重建核心 query 集基线")
    ap.add_argument("--check", action="store_true", help="与基线对比 (默认)")
    ap.add_argument("--dry", action="store_true", help="仅输出回滚建议, 不执行回滚")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--threshold", type=float, default=5.0, help="回滚阈值(百分点)")
    args = ap.parse_args()

    ref_dir = Path(__file__).resolve().parent
    baseline_path = ref_dir / "core_queries_baseline.json"
    log_path = ref_dir / "monitor_log.jsonl"

    if not is_healthy():
        msg = "[monitor] vdb 不可用 (chroma 损坏/未构建), 无法评估。"
        print(msg)
        sys.exit(1)
    col = _get_collection()

    if args.update_baseline or not baseline_path.exists():
        valid, missing = build_core_queries(col)
        res = run_eval(col, valid)
        baseline = {
            "created": datetime.now(timezone.utc).isoformat(),
            "n": res["n"], "top1": res["top1"], "top3": res["top3"],
            "top1_pct": res["top1_pct"], "top3_pct": res["top3_pct"],
            "core_queries": valid,
            "excluded_missing_expected": missing,
            "note": "vdb 检索层基线。非 names-only 端到端效应指标。",
        }
        baseline_path.write_text(json.dumps(baseline, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"[monitor] 核心 query 集基线已建立: {baseline_path}")
        print(f"  n={res['n']}, top1={res['top1_pct']}%, top3={res['top3_pct']}%")
        if missing:
            print(f"  排除 {len(missing)} 个悬空 expected: {missing}")
        print("  (注释: 此基线测 vdb 检索健康, 非 names-only 端到端效应)")
        return

    baseline = json.loads(baseline_path.read_text(encoding="utf-8"))
    valid = [(q, exp) for q, exp in baseline["core_queries"]]
    res = run_eval(col, valid)

    d_top1 = baseline["top1_pct"] - res["top1_pct"]
    d_top3 = baseline["top3_pct"] - res["top3_pct"]
    trigger = (d_top1 > args.threshold) or (d_top3 > args.threshold)

    missed = [d for d in res["detail"] if d["miss"]]
    ts = datetime.now(timezone.utc).isoformat()
    log_entry = {
        "ts": ts, "n": res["n"],
        "top1_pct": res["top1_pct"], "top3_pct": res["top3_pct"],
        "base_top1_pct": baseline["top1_pct"], "base_top3_pct": baseline["top3_pct"],
        "delta_top1": round(d_top1, 1), "delta_top3": round(d_top3, 1),
        "threshold": args.threshold, "rollback_triggered": trigger,
        "dry": args.dry,
    }
    with log_path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(log_entry, ensure_ascii=False) + "\n")

    rollback_cmd = "hermes config set agent.skills_index_mode full"
    report_lines = [
        "=" * 60,
        "  index_mode 在线监控 v2 — 核心 query 集 vdb 命中率",
        "=" * 60,
        f"  时间: {ts}",
        f"  核心 query 数: {res['n']}",
        f"  基线: top1={baseline['top1_pct']}%  top3={baseline['top3_pct']}%",
        f"  当前: top1={res['top1_pct']}%  top3={res['top3_pct']}%",
        f"  降幅(top1): {d_top1:+.1f}pp   (阈值 {args.threshold}pp)",
        f"  降幅(top3): {d_top3:+.1f}pp",
    ]
    if missed:
        report_lines.append(f"\n  未命中 ({len(missed)}/{res['n']}):")
        for m in missed[:12]:
            report_lines.append(f"    - {m['query'][:40]!r}: 期望={m['expected']} 实际top1={m['top1_skill']}")
        if len(missed) > 12:
            report_lines.append(f"    ... 还有 {len(missed) - 12} 个")

    if trigger:
        report_lines.append(f"\n  ⚠ 回滚阈值触发 ({'DRY RUN' if args.dry else '建议执行'})!")
        report_lines.append(f"    {rollback_cmd}")
        report_lines.append("    并核查 vdb 索引/embed 是否漂移。")
        if not args.dry:
            # 注意: 默认不自动改 config (guardrail 保护, 需人工确认回滚意图)
            report_lines.append("    (自动回滚未启用: 需人工确认后执行上述命令)")
    else:
        report_lines.append("\n  ✓ 未超阈值, 检索层无回归。")
    report_lines.append("  (注: 此监控测 vdb 检索健康, 非 names-only 端到端效应)")
    report = "\n".join(report_lines)

    if args.json:
        print(json.dumps({**log_entry, "missed": missed[:12]}, ensure_ascii=False, indent=2))
    else:
        print(report)


if __name__ == "__main__":
    main()
