# vdb 索引漏掉软链技能 — 根因与修复（实测复现）

> 2026-07-14 实测发现并修复。本文件是**可复跑的调试配方**，不是流水账。

## 现象（smell）

`matcher.search("发飞书消息")` 等飞书 query 的 top 结果里**完全没有 lark-* 技能**，
即使 `~/.hermes/skills/lark-im` 等软链存在且 `readlink -f` 能解析到真实 `SKILL.md`。

复现缺口的 Detect 配方：

```python
# 在 hermes-agent venv 下取 available_skills 全量技能名
import re, json, sys
from pathlib import Path
sys.path.insert(0, '~/.hermes/hermes-agent')
sys.path.insert(0, '~/.hermes/hermes-agent/venv/lib/python3.11/site-packages')
from agent.prompt_builder import build_skills_system_prompt

full = build_skills_system_prompt(available_tools=None, available_toolsets=None, compact_categories=None)
block = re.search(r"<available_skills>\n(.*?)\n</available_skills>", full, re.DOTALL).group(1)
names = set()
for line in block.split("\n"):
    m = re.match(r"\s+-\s+([\w:-]+):", line)
    if m: names.add(m.group(1))
    elif "[names only]:" in line:
        for n in re.findall(r"[\w:-]+", line.split(":",1)[1]): names.add(n)

state = json.loads(Path("~/.hermes/vdb/vdb_state.json").read_text())
indexed = set(state.get("skill_hashes", {}).keys())
gap = sorted(names - indexed)
print(f"目录 {len(names)} | vdb {len(indexed)} | 缺口 {len(gap)}")
print(gap)   # 若输出 27 个 lark-*，即命中本 bug
```

## 根因（root cause）

`~/.hermes/vdb/indexer.py` 用 `SKILLS_DIR.rglob("SKILL.md")` 扫描技能。
**Python 3.14 的 `Path.rglob` 默认不跟进目录软链（directory symlink）**。
27 个 `lark-*` 是软链目录（`~/.hermes/skills/lark-im` → `~/.agents/skills/lark-im`），
被 `rglob` 直接跳过 → vdb 只索引到 71 个、漏 27 个。

软链本身**一直正确**（`../../.agents/skills/X` 从 `~/.hermes/skills/` 解析即 `~/.agents/`，
真实路径存在且含 `SKILL.md`）。不是数据丢失、不是历史残留、不是路径写错。
误判"多套一层 .hermes"是错的——`readlink -f` 验证即可排除。

佐证（同一目录两种扫描的差异）：

```python
from pathlib import Path
import os
hits = list(Path('~/.hermes/skills').rglob('SKILL.md'))      # 跟进软链? 否(Py3.14)
lark_rglob = [h for h in hits if 'lark-' in str(h)]                   # -> 仅 1 个
lark_walk  = [r for r,_,f in os.walk('~/.hermes/skills', followlinks=True)
              if 'lark-' in r and 'SKILL.md' in f]                    # -> 28 个
```

## 修复（fix）

`indexer.py` 两处扫描（`build_index` 与 `check_index_stale`）从 `rglob` 改为
`os.walk(followlinks=True)`，并对每个命中构造 `Path(root)/"SKILL.md"`：

```python
# build_index() 内
_skill_paths: list[Path] = []
for root, _dirs, files in os.walk(str(SKILLS_DIR), followlinks=True):
    rel = root.replace(str(SKILLS_DIR), "", 1)
    if ".venv" in rel or "/.archive/" in rel:
        continue
    if "SKILL.md" in files:
        _skill_paths.append(Path(root) / "SKILL.md")
for path in sorted(_skill_paths):
    ...
```

`check_index_stale()` 用同样写法，否则"索引过期检查"会忽略软链技能而误判不重建。

## 验证（verify）

```bash
# vdb 有独立 .venv（python3.14），chromadb 只装在那里 —— 必须用这个解释器
cd ~/.hermes/vdb && .venv/bin/python -c "import indexer; indexer.build_index(force=True)"
# 期望: Chroma 写入完成: 98 个技能 (原为 71)
```

修复后复测：

- vdb 索引 71 → **98** 个技能
- 目录 96 个 vs vdb 98 个 → **缺口 = 0（100% 覆盖）**
- `lark-*`: 目录 28 = vdb 28，全部纳入
- 飞书 query（发消息/表格/日历/文档）top3 全部命中对应 lark-* skill

## 工具链事实（避免下次绕路）

- vdb 管道跑在 **`~/.hermes/vdb/.venv`**（python3.14），与 hermes-agent 的
  `~/hermes-agent/venv`（python3.11）**是两个独立环境**。
  → 跑 `matcher.py` / `indexer.py` 必须用 `.venv/bin/python`，否则
  `ModuleNotFoundError: chromadb`。
- `prompt_builder.py` / `coding_context.py` 在 hermes-agent venv（python3.11）下导。
- 这两个 venv 不能混用。
