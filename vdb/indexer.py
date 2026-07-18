"""
索引构建 — Chroma 入库。

流程:
  1. 遍历 skills/ 解析 frontmatter（yaml.safe_load，修复 RISK-2 脆弱正则）
  2. PROSE_DOC_TEMPLATE 拼接 name+leading+desc+branches → 云端 BGE-M3 稠密向量
  3. trigger_tags → 本地 sparse weights（隔离英文 description，leading word 2x boost）
  4. P2: 全局 IDF 计算，weight = log(1+tf) × idf(t)
  5. 写入 Chroma 集合（向量 + metadata 含 tag_sparse）
  6. (v3 RISK-1) build_index 后自动刷新 matcher 的 trigger mapping

v2.1 (2026-07-10) 改进点:
  - DOC_TEMPLATE 改成 prose 模板：name：{leading}。{desc}。触发：{branches}。
  - 自动从 description 提取 leading word（首段第一动词短语）
  - 触发条件从 description 抽"Use when X"和"触发：X"段落
  - 模板改动 → 必须 force=True 重建索引
v3 (2026-07-18) 改进点:
  - RISK-2: _parse_skill_md 改用 yaml.safe_load（替代脆弱正则解析 frontmatter）
  - RISK-1: build_index() 末尾自动 refresh trigger mapping
  - SKILLS_DIR 默认迁移到 ~/knowledge/skills（技能即知识架构）
"""

import os, re, hashlib, json, math
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

import yaml
import chromadb
from chromadb.config import Settings

from embed import get_cloud_dense, get_tag_sparse_dict
from sparse import compute_idf_from_skills


def _get_hermes_home() -> Path:
    """Return the effective Hermes home, reading HERMES_HOME env var first.

    Hermes sets HERMES_HOME when running under a named profile
    (e.g. ``/home/user/.hermes/profiles/work/``).  When unset, fall
    back to the default ``~/.hermes``.
    """
    val = os.environ.get("HERMES_HOME", "").strip()
    if val:
        return Path(val).expanduser()
    return Path.home() / ".hermes"


HERMES_HOME = _get_hermes_home()
# v3 (2026-07-18): 技能即知识架构 — 技能库从框架自带的 ~/.hermes/skills
# 迁移到独立的 ~/knowledge/skills（作为可检索的知识文档层）。
# ~/.hermes/skills 仅保留 hermes-skill-router 一个铁律指向 prompt，
# 使 available_skills 注入归零；真实技能内容由 vdb 索引 ~/knowledge/skills，
# 会话内经 vdb.search() 命中 skill_path 后用 read_file 按需读取。
# 仍支持 HERMES_SKILL_DIR 环境变量覆盖（必须在 import 前设置才生效）。
_KNOWLEDGE_SKILLS_DEFAULT = Path.home() / "knowledge" / "skills"
SKILLS_DIR = Path(os.environ.get("HERMES_SKILL_DIR", str(_KNOWLEDGE_SKILLS_DEFAULT)))
VDB_DIR = Path.home() / ".hermes" / "vdb"
CHROMA_DIR = VDB_DIR / "chroma"

COLLECTION_NAME = "skills"
# v3 (2026-07-18): 大库（100+ 技能）下稠密召回候选数从 16 提到 32，
# 给 RRF 融合更多分母，降低长尾技能漏召。
TOP_K_CANDIDATES = 32

# v2.1 prose 模板: name+leading_word+desc+branches 一段自然语言
# 优势: BGE-M3 拿到的是"技能做什么+何时触发"完整语义，不是字段堆叠
PROSE_DOC_TEMPLATE = "{name}：{leading}。{desc}。触发：{branches}。"

# ── Chroma 客户端 ─────────────────────────────────────────────────

_client: chromadb.ClientAPI | None = None


def _get_collection():
    global _client
    if _client is None:
        CHROMA_DIR.mkdir(parents=True, exist_ok=True)
        _client = chromadb.PersistentClient(
            path=str(CHROMA_DIR),
            settings=Settings(anonymized_telemetry=False),
        )
    return _client.get_or_create_collection(
        name=COLLECTION_NAME,
        metadata={"hnsw:space": "cosine"},
    )


# ── frontmatter 解析 ──────────────────────────────────────────────

def _load_frontmatter(path: Path) -> dict | None:
    text = path.read_text(encoding="utf-8")
    if not text.startswith("---"):
        return None
    m = re.search(r"\n---\s*\n", text[3:]) or re.search(r"\n---\s*[^\n]", text[3:])
    if not m:
        return None
    try:
        import yaml
        return yaml.safe_load(text[3:m.start() + 3])
    except Exception:
        return None


def _parse_trigger(fm: dict | None) -> list[str]:
    if not fm:
        return []
    raw = fm.get("metadata", {}).get("hermes", {}).get("tags", {})
    if isinstance(raw, dict):
        return [t.strip() for t in raw.get("trigger", []) if t and isinstance(t, str) and t.strip()]
    return []


def _parse_disable(fm: dict | None) -> list[str]:
    if not fm:
        return []
    raw = fm.get("metadata", {}).get("hermes", {}).get("tags", {})
    if isinstance(raw, dict):
        return [t.strip() for t in raw.get("disable", []) if t and isinstance(t, str) and t.strip()]
    return []


# ── v2.1 prose 抽取 ────────────────────────────────────────────────

# leading word 池（与 sparse.LEADING_WORD_POOL 对齐）
LEADING_WORDS = {
    "red-green", "fog-of-war", "tracer-bullet", "root-cause", "verify-first",
    "sunk-cost", "ship-it", "ground-truth",
    "dispatch", "gate", "handoff", "slice",
    "probe", "fire", "scaffold",
    "bridge", "mirror",
}

# 中文 leading word 同义词（description 出现这些词标 leading 字段）
LEADING_WORDS_ZH = {
    "red-green": "红绿循环",
    "fog-of-war": "探索未知",
    "tracer-bullet": "端到端通路",
    "root-cause": "根因排查",
    "verify-first": "验证先行",
    "sunk-cost": "推倒重来",
    "ship-it": "部署发布",
    "ground-truth": "文档驱动",
    "dispatch": "多 agent 派发",
    "gate": "门控卡口",
    "handoff": "交接产物",
    "slice": "切片独立",
    "probe": "探查只读",
    "fire": "触发一次性",
    "scaffold": "生成模板",
    "bridge": "跨平台适配",
    "mirror": "同步镜像",
}


def _extract_leading_word(desc: str, skill_name: str) -> str:
    """从 description 提取 leading word（强概念短语）。

    策略:
      1. 先在 desc 中搜 leading word 池子命中（连字符形式或中文同义词）
      2. 没命中就退到"取首段第一个名词短语"作为兜底
      3. 兜底也失败就用 skill_name
    """
    if not desc:
        return skill_name
    desc_lower = desc.lower()
    # 1. 精确匹配连字符 leading word
    for lw in LEADING_WORDS:
        if lw in desc_lower:
            return lw
    # 2. 中文同义词
    for lw, zh in LEADING_WORDS_ZH.items():
        if zh in desc:
            return lw
    # 3. 兜底：取 description 前 30 字符作为伪 leading word
    return desc[:30].strip("：:。.,，、 ")


def _extract_branches(desc: str, max_branches: int = 3) -> str:
    """从 description 提取触发分支（"Use when X" / "触发：X" 模式）。

    最多返回 max_branches 个，用"、"连接。
    兜底：用 trigger tags 的前 3 个。
    """
    if not desc:
        return ""
    # 英文 "Use when" 模式
    uses = re.findall(r"[Uu]se when\s+([^。.;；]+)", desc)
    # 中文 "触发：" 模式
    if not uses:
        m = re.search(r"触发[：:]\s*([^。.;；]+)", desc)
        if m:
            uses = [seg.strip() for seg in re.split(r"[,，、/]", m.group(1)) if seg.strip()]
    # 中文 "当 ... 时" 模式
    if not uses:
        uses = re.findall(r"当\s*([^。,，;；]+?)\s*时", desc)
    if not uses:
        return ""
    return "、".join(uses[:max_branches])


def _file_hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()[:16]


# ── 索引构建 ──────────────────────────────────────────────────────

def build_index(force: bool = False):
    """全量重建 Chroma 索引。"""
    collection = _get_collection()
    if force:
        try:
            _client.delete_collection(COLLECTION_NAME)
        except Exception:
            pass
        collection = _get_collection()

    # 扫描技能
    # 注：SKILLS_DIR.rglob() 在 Python 3.14 下默认不跟进目录软链，
    # 导致 lark-* 等软链技能（指向 ~/.agents/skills/*）被跳过、vdb 索引漏掉。
    # 改用 os.walk(followlinks=True) 才能正确解析软链下的 SKILL.md。
    skills = []
    _skill_paths: list[Path] = []
    for root, _dirs, files in os.walk(str(SKILLS_DIR), followlinks=True):
        rel = root.replace(str(SKILLS_DIR), "", 1)
        if ".venv" in rel or "/.archive/" in rel:
            continue
        if "SKILL.md" in files:
            _skill_paths.append(Path(root) / "SKILL.md")
    for path in sorted(_skill_paths):
        rel = path.as_posix()
        if ".venv" in rel or "/.archive/" in rel:
            continue
        fm = _load_frontmatter(path)
        name = fm.get("name", path.parent.name) if fm else path.parent.name
        desc = (fm.get("description") or "").strip() if fm else ""
        trig = _parse_trigger(fm)
        disable = _parse_disable(fm)
        # v2.1 prose 模板
        leading = _extract_leading_word(desc, name)
        branches = _extract_branches(desc)
        if not branches:
            # 兜底: 用 trigger tags 前 3 个
            branches = "、".join(trig[:3])
        doc_text = PROSE_DOC_TEMPLATE.format(
            name=name, leading=leading, desc=desc, branches=branches
        )
        skills.append((name, str(path), doc_text, trig, disable, desc))

    if not skills:
        print("[indexer] 无技能需索引")
        return

    # P2: 全局 IDF 计算（含 trigger_tags + desc 中文短语）
    print(f"[indexer] 计算全局 IDF（{len(skills)} 个技能，含 description 中文短语）...")
    idf_map = compute_idf_from_skills(skills)
    print(f"[indexer] IDF tokens: {len(idf_map)}，"
          f"范围 [{min(idf_map.values()):.2f}, {max(idf_map.values()):.2f}]")

    print(f"[indexer] 技能 {len(skills)} 个，正在云端稠密向量化...")
    dense_vecs = get_cloud_dense([s[2] for s in skills])

    print(f"[indexer] 本地 sparse 权重（IDF 增强版）...")
    ids, embeddings, documents, metadatas = [], [], [], []
    for i, (name, path, doc_text, trig, disable, desc) in enumerate(skills):
        tag_sparse = get_tag_sparse_dict(trig, idf_map=idf_map, desc=desc)
        h = _file_hash(Path(path))
        ids.append(f"{name}__v{h}")
        embeddings.append(dense_vecs[i])
        documents.append(doc_text)
        metadatas.append({
            "skill_name": name,
            "skill_path": path,
            "trigger_tags": json.dumps(trig, ensure_ascii=False),
            "disable_tags": json.dumps(disable, ensure_ascii=False),
            "tag_sparse": tag_sparse,
            "file_hash": h,
            "embedding_version": "bge-m3-siliconflow-v2-idf",
        })

    collection.add(
        ids=ids,
        embeddings=embeddings,
        documents=documents,
        metadatas=metadatas,
    )
    count = collection.count()
    print(f"[indexer] Chroma 写入完成: {count} 个技能, dim={len(dense_vecs[0])}")

    # ── 写状态文件（含 IDF 映射）─────────────────────────────────
    VDB_DIR.mkdir(parents=True, exist_ok=True)
    state = {
        "count": count,
        "dim": len(dense_vecs[0]),
        "skill_hashes": {s[0]: _file_hash(Path(s[1])) for s in skills},
        "idf_tokens": len(idf_map),
        "embedding_version": "bge-m3-siliconflow-v2-idf",
        "built_at": __import__("datetime").datetime.now().isoformat(),
    }
    state_path = VDB_DIR / "vdb_state.json"
    state_path.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")

    # 存储 IDF 映射（供后续版本兼容使用，当前查询端不依赖）
    idf_path = VDB_DIR / "idf_map.json"
    idf_path.write_text(json.dumps(idf_map, ensure_ascii=False), encoding="utf-8")
    print(f"[indexer] 状态文件已保存: {state_path}")
    print(f"[indexer] IDF 映射已保存: {idf_path} ({len(idf_map)} tokens)")

    # ── RISK-1 修复：build_index 后自动刷新 matcher 的 trigger mapping ──
    # 索引重建后，matcher._TRIGGER_MAPPING 和 _SKILL_PATH_BY_NAME 必须同步刷新，
    # 否则 fast_path 仍使用旧映射（技能增删改后 fast_path 命中错误/漏召）。
    # 延迟导入避免循环依赖（matcher 已导入 indexer 的常量）。
    # force=True 时 Chroma 先删旧 collection，新 collection 可能短暂不可用，
    # 加小幅重试等待 PersistendClient 完成落盘。
    try:
        import time as _time
        import matcher as _matcher_mod
        _refresh_ok = False
        for _attempt in range(5):
            try:
                _matcher_mod.refresh_trigger_mapping()
                _refresh_ok = True
                break
            except Exception:
                _time.sleep(0.3)
        if _refresh_ok:
            logger.info("build_index: trigger mapping refreshed after index rebuild")
        else:
            logger.warning("build_index: trigger mapping refresh skipped (collection not ready)")
    except Exception as exc:
        logger.warning("build_index: failed to refresh trigger mapping: %s", exc)
        # 不阻断构建流程，最坏情况 fast_path 在当前会话用旧映射


# ── 状态文件（健康检查） ─────────────────────────────────────────────

STATE_FILE = VDB_DIR / "vdb_state.json"


def check_index_stale() -> tuple[bool, str]:
    """检查索引是否过期（对比技能目录最新 hash vs 状态文件）。

    返回:
        (is_stale: bool, reason: str)
    """
    if not STATE_FILE.exists():
        return True, "状态文件不存在（从未构建或手动删除）"
    try:
        state = json.loads(STATE_FILE.read_text(encoding="utf-8"))
    except Exception:
        return True, "状态文件损坏"

    # 扫描当前技能（与 build_index 一致，必须 followlinks 才能纳入软链技能）
    current = {}
    for root, _dirs, files in os.walk(str(SKILLS_DIR), followlinks=True):
        rel = root.replace(str(SKILLS_DIR), "", 1)
        if ".venv" in rel or "/.archive/" in rel:
            continue
        if "SKILL.md" in files:
            path = Path(root) / "SKILL.md"
            relp = path.as_posix()
            if ".venv" in relp or "/.archive/" in relp:
                continue
            fm = _load_frontmatter(path)
            name = fm.get("name", path.parent.name) if fm else path.parent.name
            current[name] = _file_hash(path)

    saved = state.get("skill_hashes", {})

    # 检查技能增减
    added = set(current) - set(saved)
    removed = set(saved) - set(current)
    if added:
        return True, f"新增技能: {', '.join(sorted(added)[:5])}"
    if removed:
        return True, f"删除技能: {', '.join(sorted(removed)[:5])}"

    # 检查已修改
    changed = [n for n in current if n in saved and current[n] != saved[n]]
    if changed:
        return True, f"技能已修改: {', '.join(changed[:5])}"

    return False, ""


# ── CLI ─────────────────────────────────────────────────────────────

if __name__ == "__main__":
    build_index(force="--force" in __import__("sys").argv)
