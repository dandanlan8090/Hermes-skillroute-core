"""
路由门禁模块（配置与逻辑分离 + 声明式门禁加载）
职责：
  1. 管理静态门禁规则（手写维护，仅保留框架专名）
  2. 从 skills/ 目录动态加载技能的声明式门禁（gate.enabled + keywords）
  3. 提供统一的查询接口 is_query_allowed_for_skill()

背景（2026-07-13 老黎自检会话）：
  hermes-framework 是框架"进化史+说明书"（~17K 字符 / ~7K token 的重型文档），
  正常任务不该碰它。但因中文 sparse 按单字切分（重·构·优·化 都进字典）+ dense
  语义歧义（"重构函数" 与 "重构框架" 相近），业务类 query 会误命中它、瞬间注入 7K。

  实测结论（不可照搬直觉）：
    - disable 标签是"字面子串匹配"，写的是书面描述短语（"用户业务代码变更"），
      用户不会这么说话 → 形同虚设，拦不住泛用词。
    - trigger 摘词无效：泛用词根本不在 sparse 字典，噪声来自单字切分 + dense。
    - startswith('hermes-') 粗过滤会误杀 18 个日常 hermes-* 技能（tdd/git/safety…）。
  唯一治本：进检索前做"专名门禁"——只保护指定的重型技能，且门禁词必须是
  业务代码里不会出现的框架专名（裸词 "hermes" 实测会误伤 "hermes怎么配置" 等，已剔除）。

设计原则：
  - 只维护准入规则，不碰检索算法/分数。
  - 门禁词 = 业务/日常任务里不会出现的框架专名（专名门禁，非泛用词）。
  - GATED_SKILLS 未列出的技能一律放行（对绝大多数技能零影响）。
  - 声明式门禁（v2）：技能作者可在自身 SKILL.md frontmatter 写
    metadata.hermes.gate = {enabled: true, keywords: [...]}，
    框架扫描时自动注册，**默认安全**——未声明 gate 的技能永远不受门禁影响。
  - 声明式覆盖静态：技能作者写的 keywords 优先于框架默认，
    便于特例技能定制自己的门禁词。
"""

from typing import Set, Dict, Optional
import re
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

# ── 1. 静态门禁词表（持续增补；必须是"业务代码里不会出现的框架专名"）──────
# 注意：裸词 "hermes" 已剔除——实测 "hermes怎么配置/用hermes写测试/hermes发消息"
# 等日常 query 都含 hermes，保留它会把日常任务误锁进框架门禁。
FRAMEWORK_GATE_KEYWORDS: Set[str] = {
    "soul.md", "soul", "铁律", "vdb", "召回", "技能路由", "路由表",
    "微内核", "skill.md", "frontmatter", "rrf", "bge-m3", "chroma",
    "主脑", "oracle", "索引", "trigger", "disable", "框架",
    "hermes-framework", "进化史", "变更日志", "profile", "加载顺序",
    "system prompt", "内核", "技能检索", "微型框架", "微型架构",
}

# 未来扩展预留（需要时取消注释 + 在 STATIC_GATED_SKILLS 加映射，无需改 matcher.py）：
# MLOPS_GATE_KEYWORDS: Set[str] = {"训练", "模型", "推理", "mlops", "checkpoint"}
# MEDIA_GATE_KEYWORDS: Set[str] = {"剪辑", "音视频", "youtube", "字幕"}

# ── 2. 静态映射：skill_name（精确）→ 对应门禁词集 ───────────────────
# key 必须与 skills/ 下 frontmatter 的 name 精确一致（hermes-framework 而非 hermes_framework）。
STATIC_GATED_SKILLS: Dict[str, Set[str]] = {
    "hermes-framework": FRAMEWORK_GATE_KEYWORDS,
    "hermes-micro-framework": FRAMEWORK_GATE_KEYWORDS,
    # 未来扩展示例：
    # "mlops-pipeline": MLOPS_GATE_KEYWORDS,
}

# 编译正则缓存（每个门禁词集只编译一次）
_GATE_PATTERNS: Dict[str, re.Pattern] = {}


# ── 3. 声明式门禁加载（v2，从 SKILL.md frontmatter 读取） ─────────────

def _find_skills_root() -> Optional[Path]:
    """自动定位 skills/ 目录（从 vdb/ 同级向上找，再回退到 ~/.hermes/skills）。"""
    current = Path(__file__).resolve().parent  # vdb/
    candidates = [
        current.parent / "skills",                  # ../skills
        current.parent.parent / "skills",           # ../../skills
        Path.home() / ".hermes" / "skills",         # 用户级安装
    ]
    for p in candidates:
        if p.exists() and p.is_dir():
            return p
    logger.warning("未找到 skills/ 目录，声明式门禁将不生效")
    return None


def _is_active_skill_path(md_path: Path) -> bool:
    """判断 SKILL.md 是否属于活跃技能。排除 .archive/ 和 .curator_backups/。"""
    return not any(seg in md_path.parts for seg in {".archive", ".curator_backups"})


def _parse_skill_frontmatter(md_path: Path) -> Optional[dict]:
    """从 SKILL.md 解析 YAML frontmatter，失败/无 frontmatter 返回 None。"""
    try:
        content = md_path.read_text(encoding="utf-8")
    except Exception as e:
        logger.debug(f"读取 {md_path} 失败: {e}")
        return None
    content = content.lstrip()
    if not content.startswith("---"):
        return None
    parts = content.split("---", 2)
    if len(parts) < 3:
        return None
    try:
        import yaml  # 局部导入，pyyaml 已验证在 venv 中可用
        fm = yaml.safe_load(parts[1])
    except Exception as e:
        logger.debug(f"YAML 解析失败 {md_path}: {e}")
        return None
    return fm if isinstance(fm, dict) else None


def load_gate_config_from_skills(skills_root: Optional[Path] = None) -> Dict[str, Set[str]]:
    """扫描 skills/ 加载活跃 SKILL.md 中声明的 gate 配置。

    返回 {skill_name: set(keywords)}。未声明 gate 或 gate.enabled != True 的技能忽略。
    自动过滤 .archive/ 与 .curator_backups/。
    """
    if skills_root is None:
        skills_root = _find_skills_root()
    if skills_root is None:
        return {}

    all_md = list(skills_root.glob("**/SKILL.md"))
    active_md = [p for p in all_md if _is_active_skill_path(p)]
    logger.debug(f"扫描到 {len(all_md)} 个 SKILL.md，活跃 {len(active_md)} 个")

    gate_map: Dict[str, Set[str]] = {}
    for md in active_md:
        fm = _parse_skill_frontmatter(md)
        if not fm:
            continue
        gate_cfg = fm.get("metadata", {}).get("hermes", {}).get("gate")
        if not gate_cfg or not gate_cfg.get("enabled", False):
            continue
        kw_raw = gate_cfg.get("keywords", [])
        if isinstance(kw_raw, str):
            kw_raw = [kw_raw]
        kw_set = {str(k).strip() for k in kw_raw if str(k).strip()}
        if not kw_set:
            logger.debug(f"{md} 声明 gate.enabled=true 但 keywords 为空，跳过")
            continue
        skill_name = fm.get("name") or md.parent.name
        gate_map[skill_name] = kw_set
        logger.debug(f"加载声明式门禁: {skill_name} -> {kw_set}")
    return gate_map


# 动态加载的声明式门禁（reload_gate_config 时刷新）
_DECLARED_GATES: Dict[str, Set[str]] = {}


def reload_gate_config(skills_root: Optional[Path] = None) -> None:
    """刷新声明式门禁配置（开发调试/新增 skill 后调用）。"""
    global _DECLARED_GATES
    _DECLARED_GATES = load_gate_config_from_skills(skills_root)
    _GATE_PATTERNS.clear()  # 让正则在下次调用时重新编译
    logger.info(f"门禁配置已刷新: 声明式 {_DECLARED_GATES} 个, 静态 {len(STATIC_GATED_SKILLS)} 个")


def get_gated_skills() -> Dict[str, Set[str]]:
    """返回合并后的完整门禁映射（声明式覆盖静态同名键）。"""
    merged = STATIC_GATED_SKILLS.copy()
    merged.update(_DECLARED_GATES)
    return merged


# 模块加载时自动跑一次声明式扫描
reload_gate_config()


# ── 4. 正则编译与查询接口 ──────────────────────────────────────────

def _get_gate_pattern(keywords: Set[str]) -> re.Pattern:
    """将关键词集合编译为一个正则（忽略大小写，支持中文，特殊字符转义）。

    关键词按长度降序拼接，避免短词遮蔽长词（如 vdb 先于 vd）。
    SOUL.md 的 "." 经 re.escape 转义为普通字符，不做通配。
    """
    sorted_kw = sorted(keywords, key=len, reverse=True)
    pattern_str = "|".join(re.escape(kw) for kw in sorted_kw)
    return re.compile(pattern_str, re.IGNORECASE | re.UNICODE)


def is_query_allowed_for_skill(query: str, skill_name: str) -> bool:
    """判断 query 是否允许召回指定 skill。

    决策顺序（按修正点 [4] 调整——先判门禁归属，再判空 query）：
      1. skill_name 不在任何门禁列表中 → 永远放行（True）。
      2. skill_name 在门禁列表中 + query 为空/空白 → 拒绝（False）。
      3. 否则：query 必须含至少一个对应门禁词才放行（True），否则拦截（False）。

    边界：
      - 大小写不敏感（正则 IGNORECASE）。
      - 中文无需分词，子串匹配即可。
    """
    gated = get_gated_skills()
    if skill_name not in gated:
        return True
    if not query or not query.strip():
        return False
    if skill_name not in _GATE_PATTERNS:
        _GATE_PATTERNS[skill_name] = _get_gate_pattern(gated[skill_name])
    return bool(_GATE_PATTERNS[skill_name].search(query))


# ── 5. 辅助函数（可观测） ──────────────────────────────────────────

def dump_gate_config() -> str:
    """打印当前所有门禁配置（用于 `python -m vdb.routing` 调试）。"""
    gated = get_gated_skills()
    lines = ["当前门禁配置:"]
    for name in sorted(gated):
        lines.append(f"  {name}: {', '.join(sorted(gated[name]))}")
    return "\n".join(lines)


if __name__ == "__main__":
    print(dump_gate_config())
