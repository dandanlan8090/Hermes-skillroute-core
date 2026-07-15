# METADATA_GUIDE.md — Hermes 技能召回元数据编写规范

> 适用对象：`~/.hermes/skills/**/SKILL.md` 的 frontmatter 编写者
> 配套 skill：`autoload-vdb`（检索系统）、`hermes-agent-skill-authoring`（技能创建）
> 架构版本：v6.0.0 / 2026-07-11 收官状态

---

## 0. 为什么这份指南存在

Hermes 的技能检索是 **dense(BGE-M3 1024d 云端) + sparse(IDF 增强 本地) RRF 融合**：

```
query ─┬─ 稠密：PROSE_DOC_TEMPLATE("{name}：{leading}。{desc}。触发：{branches}。") → BGE-M3 → 1024d
       └─ 稀疏：trigger_tags + description 中文短语(≥2字) → TF-IDF 权重
              ↓
       RRF(K=60) = 1/(60+dense_rank) + 1/(60+sparse_rank) + (trigger命中 ? +0.010 : 0)
              ↓
       disable 过滤 → top-5
```

**算法层已收敛**：RRF 取代 0.6/0.4、trigger 加法加成 +0.010、IDF 增强 sparse、desc 中文短语入索引——这些调优全部完成，benchmark 稳定。

**剩余的失败 case 100% 指向元数据缺陷**：trigger 不足、disable 缺失、纯英文 description。
**本指南把这些"写好元数据"的经验固化成可执行的规则**，让新技能/新装技能从第一天就带高质量召回元数据，不再靠事后补丁。

---

## 1. trigger_tags 编写规范

### 1.1 数量底线
**≥ 7 条。** 62 技能实测：trigger < 7 的技能在口语 query 上召回明显不稳；≥ 7 后 Top-1/T3 都稳定。

### 1.2 来源原则：模拟用户怎么"说"，不写技能"内部概念"
trigger 是给用户自然语言 query 做 sparse 匹配的。写的时候问自己：*用户会怎么口语化地表达这个需求？*

| ✅ 好 trigger（用户视角、自然语言） | ❌ 坏 trigger（内部概念、纯英文） |
|---|---|
| `["调试代码","报错排查","bug修复","程序崩溃","代码跑不起来","为什么报错","定位异常"]` | `["debugging","error-handling","stack-trace"]` |
| `["发邮件","邮件客户端","SMTP发信","发信"]` | `["email-client","smtp-protocol"]` |

- **中文优先**，可中英混排（如 `"bug"`、`"QA"`、`"PR操作"` 都有效，因为 tokenizer 英文按词切）
- **不要写技能名本身**（除非用户真的会搜技能名，如 `"yuanbao"`、`"xurl"` 这类本身就是产品名）
- **覆盖高频同义说法**：一个技能至少覆盖 3-4 种用户可能说的句式

### 1.3 反例：纯英文 trigger 在中文本地 query 下稀疏匹配弱
用户说"帮我调试一下这个报错"，sparse 端按中文逐字 + 英文按词切。如果 trigger 全是 `"debugging"` `"troubleshoot"`，中文 query 里没有这些词 → sparse=0 → 完全依赖 dense。

---

## 2. disable_tags 编写规范

### 2.1 数量底线
**必填，≥ 2-3 条。** 没有 disable 的技能容易被"语义相近但不对"的 query 误召。

### 2.2 匹配逻辑（关键）
matcher 的过滤是：
```python
any(d.lower() in query_lower for d in disable_tags)   # disable 必须是 query 的【连续子串】
```
**disable 标签要能原样出现在用户的自然语言里。**

### 2.3 写 phrase-level，不要单字
| ✅ 好 disable（短语级，真实出现在 query 中） | ❌ 坏 disable（单字/拼凑短语） |
|---|---|
| `["代码bug调试","性能优化","新功能开发"]`（debugging-patterns 的地盘其实是 fault/system-admin/shipping，主动让出） | `["排查报错"]`（在"排查一下为什么报错"中不是连续子串 → 失效） |
| `["日常任务执行","项目开发 commit"]` | `["排","错"]`（太碎，误伤正常 query） |

**反例教训**：曾写 `"排查报错"` 想防"排查一下为什么报错"，但前者在后者里不是连续子串 → 过滤失效。正确写法是 `"排错"` 或 `"排查"`（真实子串）。

### 2.4 disable 是"主动让出"，不是"自我描述"
disable 写的是**本技能不该接、该走别处的 query**。例：
- `debugging-patterns` disable `["代码bug调试","性能优化","新功能开发"]` —— 这些是 fault-troubleshooting / system-admin / shipping-verification 的地盘
- `hermes-framework` disable `["日常任务执行","用户业务代码变更"]` —— 框架技能不接普通业务

---

## 3. description 编写规范

### 3.1 中文优先
纯英文 description **完全进不了 sparse 中文短语索引**（提取正则 `re.findall(r'[\u4e00-\u9fff]{2,}')` 只取连续中文 ≥2 字）。
后果：中文 query 下该技能 sparse=0，只能靠 dense——而 dense 在信息密度低的口语 query 上不稳。

能写中文就写中文。中英混排也可（如 `"YouTube 视频摘要"` 里"视频摘要"会被提取）。

### 3.2 三段式结构（description 是始终加载的唯一文本）
```
前 30 字符：{leading word} + 触发场景
中间 60 字符：核心动作 + 产出
末尾：分支条件（"Use when X"）+ 禁用场景（"禁用：Z"）
```
例：
```
Root-Cause：交互式调试与根因排查。Use when 报错/异常/traceback/服务不可用。禁用：纯配置变更/仅查看日志
```

### 3.3 leading word 选模型已有概念
`tracer bullet` / `root cause` / `gate` / `dispatch` / `tight loop` 等——模型已懂，省 token 且锚定行为。自定义新词需注册到 SOUL.md §词汇库。

---

## 4. 创建 / 安装技能后的必做动作

> 这条是**硬约束**，不是建议。新技能不进索引 = 永不被召回。

### 4.1 本会话内创建（skill_manage / write_file）
```bash
cd ~/.hermes/vdb && source .venv/bin/activate && PYTHONPATH=$PWD \
  python3 -c "from indexer import build_index; build_index(force=True)"
```
改完跑验证：
```bash
python3 ~/.hermes/scripts/vdb-autoload.py --check   # 应返回 "索引最新"
```

### 4.2 新装外部技能（clone / copy / 其它 session 写入）
任何把新 `SKILL.md` 放进 `~/.hermes/skills/` 的操作（不限于本会话内 create）都必须重建索引：
- `skill_manage(action='create')` 写入后立即 `build_index(force=True)`
- clone 一个 repo 的 `skills/` 到本地后，同样重建
- **当前 session 的检索缓存不会自动感知磁盘变化**——不重建索引就查不到新技能

### 4.3 install / 开机
`scripts/init-vdb.sh` 第 5 步调 `vdb-autoload.py --auto`（哈希检测 skills 列表，过期自动重建），已覆盖安装场景。

---

## 5. 边界认知（不要死磕元数据）

**dense embedding 足够强时，sparse/trigger/disable 的边际贡献趋近于零。**

当两技能 dense 向量很近（如 `fault-troubleshooting dr=1` vs `debugging-patterns dr=7~9`），sparse + trigger 加成翻不动——根因是 embedding 质量，不是元数据。

实测天花板 case（BGE-M3 语义偏差，元数据补不动）：
| Query | 期望 | dense 实际召回 | 本质 |
|---|---|---|---|
| 同步配置文件 | repo-publishing | source-driven | dense 里"同步配置"靠近"源码驱动" |
| framework 文件加载规则 | framework-loader | source-driven | dense 里"加载"靠近"源码驱动" |
| changelog 更新了啥 | framework-changelog | git-worktree | dense 里"更新"靠近"git 操作" |
| 开闭原则怎么落地 | repo-publishing | source-driven | dense 里"设计原则"靠近"源码驱动" |
| self-optimize | hermes-self-optimization | hermes-framework | dense 里"优化"靠近"框架优化" |

**结论**：这些 case 除非换 embedding 模型或做 dense 侧 domain fine-tune，否则到顶。不要在元数据层反复调参。

当前 benchmark（2026-07-11）：
- 正式集 61 条：T1=88.3% / T3=91.7%
- harder 集 17 条：T1=70.6% / T3=94.1%
- 基线（TF 0.6/0.4）对比：正式集 +14.9pp，harder +17.7pp

---

## 6. 自检清单

创建/修改技能时逐条核对：

- [ ] **trigger_tags ≥ 7 条**
- [ ] trigger 全为**用户视角自然语言**（非内部概念、非纯英文）
- [ ] 覆盖了 ≥ 3 种用户可能说的句式
- [ ] **disable_tags 必填，≥ 2-3 条**
- [ ] disable 是 phrase-level 真实子串（匹配逻辑 `disable in query`）
- [ ] disable 写的是"让出给别处"的 query，不是自我描述
- [ ] **description 含中文**（或确认英文 desc 的中文 sparse 覆盖率可接受）
- [ ] description 三段式：leading + 触发 + 禁用
- [ ] **已执行 `build_index(force=True)` 重建索引**（或确认本次改动不影响 trigger/disable/desc）
- [ ] 运行 `vdb-autoload.py --check` 确认 "索引最新"

---

## 7. 与现有流程的衔接

- **`hermes-agent-skill-authoring`**：「召回质量约束」段 + Workflow 第 7 步 + Verification Checklist 已引用本指南的 §1/§2/§3/§4。
- **`autoload-vdb`**：「创建新技能后」「新装外部技能后」段已引用本指南的 §4。
- 本指南是**规范源**（why + how），两个 skill 是**流程钩子**（when + 必做动作）。改规范先改本文件，再同步 skill 引用。
