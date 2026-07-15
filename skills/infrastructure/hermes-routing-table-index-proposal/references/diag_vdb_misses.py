#!/usr/bin/env python3
"""诊断: 对 7 个稳定未命中 query 拉 top-5 候选明细 (dense/sparse 分 + rank)。"""
import json, os, sys
from pathlib import Path

VDB_DIR = Path.home() / ".hermes" / "vdb"
sys.path.insert(0, str(VDB_DIR))
os.chdir(str(VDB_DIR))

from matcher import _get_collection, is_healthy
from embed import get_cloud_dense, calculate_sparse_score

MISSES = [
    ("这个功能的设计方案", "spec-driven-development"),
    ("合并代码到主分支", "github"),
    ("系统信息是什么", "system-admin"),
    ("看看我的待办列表", "hermes-todo-progress"),
    ("帮我排错", "debugging-patterns"),
    ("消息既然你已发出去", "yuanbao"),
    ("开闭原则怎么落地", "doubt-driven-development"),
]

RRF_K = 60

def dump(query, expected):
    col = _get_collection()
    from indexer import TOP_K_CANDIDATES
    q_text = query if len(query) >= 15 else f"调用{query}。"
    qd = get_cloud_dense([q_text])[0]
    res = col.query(query_embeddings=[qd], n_results=TOP_K_CANDIDATES,
                    include=["distances", "metadatas"])
    cands = []
    for dr, (dist, meta) in enumerate(zip(res["distances"][0], res["metadatas"][0]), 1):
        ds = 1.0 - dist
        ss = calculate_sparse_score(query, meta.get("tag_sparse", "{}"))
        disable = json.loads(meta.get("disable_tags", "[]"))
        ql = query.lower().replace("_", " ")
        hit = False
        for d in disable:
            dl = d.lower().replace("_", " ")
            parts = dl.split()
            if len(parts) > 1 and all(p in ql for p in parts): hit = True; break
            if dl in ql: hit = True; break
        cands.append((meta["skill_name"], ds, ss, dr, hit))
    valid = [c for c in cands if not c[4]]
    sp_sorted = sorted(valid, key=lambda c: c[2], reverse=True)
    srmap = {c[0]: i for i, c in enumerate(sp_sorted, 1)}
    scored = []
    for name, ds, ss, dr, _ in valid:
        sr = srmap.get(name, len(valid) + 1)
        rrf = 1/(RRF_K+dr) + 1/(RRF_K+sr)
        scored.append((name, ds, ss, dr, sr, rrf))
    scored.sort(key=lambda x: x[5], reverse=True)
    print(f"\n### query={query!r}  期望={expected}")
    print(f"{'rank':<5}{'skill':<38}{'dense':>7}{'sparse':>8}{'drank':>6}{'srank':>6}{'RRF':>8}")
    for i, (name, ds, ss, dr, sr, rrf) in enumerate(scored[:5], 1):
        flag = " <== 期望" if name == expected else ""
        print(f"{i:<5}{name:<38}{ds:>7.3f}{ss:>8.3f}{dr:>6}{sr:>6}{rrf:>8.4f}{flag}")

if __name__ == "__main__":
    if not is_healthy():
        print("vdb 不可用"); sys.exit(1)
    for q, exp in MISSES:
        dump(q, exp)
