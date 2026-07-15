# 路由门禁层 (vdb/routing.py) — 设计、踩坑与验证

防止"重型框架说明文档"技能（hermes-framework 等，>3K 字符 / ~7K token）
被业务类 query 误命中、瞬间注入。2026-07-13 老黎门禁会话落地。

> 注：门禁层代码属于 vdb 检索管道（vdb-retrieval-pipeline skill 的领域），
> 但那个 skill 被 pin、背景 curator 无法写入，故设计记录暂存于此框架总纲下。
> 若日后 vdb-retrieval-pipeline 被 unpin，应把本文迁移过去并同步其主体描述。

## 根因（实测，非直觉）

业务 query（"重构函数"/"优化性能"）误召回 hermes-framework，来自两层：
1. **中文 sparse 单字切分**：sparse 字典 148 词里 134 个是单字（框/架/构/优/化…）。
   "重构框架"被拆成 重·构·框·架，"重构函数"里的 重·构 命中框架字典 → 误命中。
   实测：摘掉 trigger 里的泛用词（改进/优化/重构）**前后 sparse 得分一字不差**，
   因为泛用词根本不在字典，噪声全来自单字。摘词方案无效，别再试。
2. **dense 语义歧义**：BGE-M3 认为"重构函数"与"重构框架"语义相近，给中等相似度。

## 为何其他拦截方案都失败（三连否定，勿走回头路）

- **disable 标签**：matcher.py 实现是字面子串匹配，disable 写的是书面短语
  （"用户业务代码变更"），用户自然语言 query 不含这些连续词 → 永不命中 → 形同虚设。
  且同一词"重构"既在 trigger 又在 disable，字面逻辑自相矛盾。
- **摘 trigger 泛用词**：见上，无效。
- **`startswith('hermes-')` 前缀过滤**：会误杀 18 个日常 hermes-* 技能
  （hermes-tdd-workflow / hermes-git-worktree / hermes-code-output / hermes-safety …）。
  用户问"写测试"会把 tdd-workflow 干掉。灾难性误伤。

## 正确方案：专名门禁

只保护指定的重型技能（GATED_SKILLS），门禁词必须是**业务代码里不会出现的框架专名**
（SOUL.md / vdb / 铁律 / 微内核 / RRF / Chroma / 主脑模式 …）。业务 query 不含专名 →
剔除该重型技能；框架 query 含专名 → 放行。零误伤日常技能。

**裸词 "hermes" 必须剔除**：实测 "hermes怎么配置" / "用hermes写测试" / "hermes发消息"
都含 hermes 但是日常任务，保留会把它们误锁进框架门禁。

## 两种登记方式

### 静态（保守）
`routing.py` 的 `STATIC_GATED_SKILLS` 字典：
```python
STATIC_GATED_SKILLS = {
    "hermes-framework": FRAMEWORK_GATE_KEYWORDS,
    "hermes-micro-framework": FRAMEWORK_GATE_KEYWORDS,
}
```

### 声明式（推荐，去中心化，默认安全）
技能自身 SKILL.md frontmatter：
```yaml
metadata:
  hermes:
    gate:
      enabled: true
      keywords: [SOUL.md, 铁律, vdb, 召回, 微内核, RRF, Chroma, ...]
```
`reload_gate_config()` 启动时扫描 skills/ 自动注册。未声明 gate 的技能永不受门禁。
声明式覆盖静态同名键（技能作者说了算）。hermes-framework 已加此声明作样板；
hermes-micro-framework 仍走静态——双模式共存验证过。

## 关键实现点（老黎方案的 4 处必要纠正，均实测证明否则致命）

1. **import 形式**：matcher.py 用 `import routing`，**不是** `from . import routing`。
   vdb 是单文件脚本集（无 `__init__.py` 包结构，靠 PYTHONPATH=$PWD import），
   `from .` 会 ImportError 直接废掉 search()。
2. **glob 过滤归档**：`load_gate_config_from_skills` 必须排除 `.archive/` 和
   `.curator_backups/`（`_is_active_skill_path`），否则归档里的旧 framework-* 副本
   （5 个）会污染门禁。
3. **剔除裸词 hermes**：见上。
4. **空 query 判断顺序**：`is_query_allowed_for_skill` 先判 `skill_name not in gated:
   return True`（非门禁技能永远放行），**再**判 `if not query: return False`。
   顺序反了会让空 query 误伤非门禁技能。

## 接入点

matcher.search() 在 `valid.sort(...)` 之后、`return` 之前：
```python
gated = [it for it in valid if routing.is_query_allowed_for_skill(query, it["skill_name"])]
return gated[:top_k]
```

## 验证清单（每次改门禁后跑）

- routing 单元测试：业务拦 / 框架放 / 空query / 大小写 / 非门禁放行 边界
- 端到端：业务 query 泄漏 framework 应 0/N；框架 query 命中应 N/N
- 声明式：建临时 skill 声明 gate → reload_gate_config() → 验证进 get_gated_skills()；
  再在 .archive/ 放同名声明 → 验证被过滤
- 改 frontmatter 后：`build_index(force=True)` 重建 + `is_healthy()` 检查
- `python routing.py` 打印 `dump_gate_config()` 审计当前门禁

## 新增重型 skill 的登记指引

见 `hermes-micro-framework` SKILL.md Common Pitfalls 第 4b 条。判据：SKILL.md
> 3,000 字符 且 描述框架/系统本身而非解决业务问题 → 需登记门禁。普通业务技能不登记。

## 门禁适用判据（2026-07-13 P2 体检修正，避免过度门禁）

体积大 ≠ 需要门禁。门禁是为「**重型文档(>3K token)被业务 query 误占 top1-3 高位**」
设计的，不是为所有大 skill。判定一个 skill 是否需要门禁，跑两问：

1. **体积**：SKILL.md > 3,000 token（≈12,000 字符）？否 → 不需要（轻量误召回危害小）。
2. **trigger 专属性**：它的 trigger 词是否与业务/日常 query 语义重叠？
   - 重叠（如 hermes-framework 的"重构/优化"）→ **需要门禁**。
   - 专属（如 context-compression 的"token太多/会话卡顿"、web-tooling 的"web_search报错"）
     → **不需要**，业务 query 天然不会误命中。

实证方法（别靠直觉，跑 matcher）：
```python
from matcher import search
biz = ["重构这个函数","优化性能","部署flask","写脚本","调试报错","写测试"]
for q in biz:
    hits = [r["skill_name"] for r in search(q) if r["skill_name"]=="<候选skill>"]
    # 只有当候选 skill 稳定冲进 top1-3 才算真泄漏；末位(#4/#5)轻量召回可忽略。
```
P2 实例：context-compression(2605t)业务 query 零命中→不加；web-tooling(1317t)
"调试报错"仅 #5 末位、真正的 debugging-patterns 占 #1→不加。二者都不需门禁。
