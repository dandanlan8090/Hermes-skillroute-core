# VDB Indexer 软链技能遗漏修复

## 症状
`available_skills` 列出的技能数（96 个）远多于 vdb 索引数（71 个）。
27 个 lark-* 飞书技能在 vdb 中全部缺少,即使它们在 `~/.hermes/skills/` 下以
**符号链接**形式存在(指向 `~/.agents/skills/*`,且目标真实存在)。

## 根因
`~/.hermes/vdb/indexer.py` 使用 `Path.rglob("SKILL.md")` 扫描技能目录。
**Python 3.14 的 `pathlib.Path.rglob()` 默认不跟进目录符号链接**，
因此 27 个 lark-* 的 symlink 目录被静默跳过。
`check_index_stale()` 同样使用 `rglob`,导致过期检测同样忽略软链技能。

## 修复
两处 `rglob("SKILL.md")` 全部替换为 `os.walk(followlinks=True)`。

`build_index()`:
```python
_skill_paths: list[Path] = []
for root, _dirs, files in os.walk(str(SKILLS_DIR), followlinks=True):
    if ".venv" in rel or "/.archive/" in rel: continue
    if "SKILL.md" in files: _skill_paths.append(Path(root) / "SKILL.md")
```

`check_index_stale()`: 相同模式,在 `if "SKILL.md" in files:` 块内直接处理。

## 结果
vdb 索引 71 → **98 个**(目录 96 个技能 **100% 覆盖**),lark-* 全部纳入。
`check_index_stale()` 现在正确检测软链技能变更。

## 注意
Python 3.11/3.12 的 `Path.rglob` 会跟进 symlinks,但 `os.walk(followlinks=True)`
在所有版本上行为一致,移植无风险。
