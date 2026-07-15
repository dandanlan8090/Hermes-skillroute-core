# FRAMEWORK_EVOLUTION.md — 框架演进记录

> 自动记录每次框架变更（新增 skill/修改铁律/优化路由），积累 3 条触发评审。

## [2026-07-14] feat: 铁律#7 从「全量加载」修订为「条件触发 + 过滤加载」
- 类型：feat（SOUL.md 铁律修订）+ fix（解决摘要反成 token 膨胀源）
- 触发：2026-07-14 上午落地初版铁律#7 后发现真实新坑——>50 条会话每轮无条件 cat 83KB 摘要（DATA 段含嵌套历史压缩块），反而比不读更费 token。用户给出修订草案。
- 修订内容（SOUL.md 铁律#7）：
  1. **触发条件从单条变三条同时满足**：① 会话消息 > 50 条；② 用户输入明确回指历史（"之前提到的"/"根据刚才讨论"/"回到 X 问题"等）；③ 当前无进行中 session_search 或其他历史检索。
  2. **加载从全量变过滤**：即使触发，也只提取 `[EXECUTED]` 和 `[ARGUMENT]` 段，忽略 `[DATA]` 段（工具输出信息密度低且可能含嵌套历史压缩块）。
  3. **作用域声明**：要求摘要头部标 `本摘要仅适用于会话 <session_id>`（scope=current_session_only），加载前校验 session_id 一致，禁止跨 session 压缩块。
  4. 过期/缺失/作用域不匹配 → 回退读 state.db 最近 N 条原始消息。
- context-processor.py 配套改动：`generate_summary()` 头部新增 `<!-- 本摘要仅适用于会话 <session_id> (scope=current_session_only) -->`（generated_at/last_message_id 元数据沿用前一版）。
- 验证（真实）：重新生成当前 session 摘要成功，头部三行元数据齐全；模拟过滤加载脚本确认只定位 EXEC/ARG 段、剥离 DATA；作用域声明可被正则解析。
- 结论：铁律#7 从"每轮无脑加载"变成"条件触发 + 过滤加载"，保留摘要价值同时控制 token，原 83KB 膨胀源问题彻底规避（DATA 段不再进对话）。
- 决策人：@lan（修订草案架构）/ Hermes（落地 + 验证）

## [2026-07-13] diag: 双压缩机制现状（context-processor.py + 系统 compression）
- 类型：diagnostic（运行态认知，无代码变更）
- 触发：用户描述压缩触发状态（"50% 触发 processor，低于 50% 不再触发，75% 系统兜底"），查代码实证纠正认知偏差。
- 实测结论（代码证据）：
  1. processor 触发阈值写死在 hook 命令 `--min-tokens 10000 --min-messages 50`（config.yaml:742），按**绝对 token** 判断，非预算百分比。当前 session 读数 54,605 token 远超阈值 → session >10000 时每次 terminal 后都跑，非"50% 触发一次"。
  2. 系统 `compression: enabled, threshold: 0.5`（config.yaml:147）是核心就地压缩，50% 预算触发、压到 target_ratio 0.2，真正影响对话上下文。config 无 0.75 配置（用户说的 75% 可能是核心内部硬上限或记忆偏差）。
  3. **两套压缩互不通信**：processor 每次覆盖写 compressed/<sid>.md，但 P3 未闭环（无读取端）→ 产物对当前对话零影响，纯落盘。系统压缩兜底真正压缩对话。两者压同一份 session，重复劳动；processor 精细分类（保留 EXECUTED 100%）成果有被系统粗暴压缩覆盖风险。
- 决策：用户确认**保持现状**——processor 落盘备用、系统压缩兜底、P3 继续挂起等验证。不改动 config。
- 待办（P3 未闭环相关，留待下次）：① 接读取端让长会话优先读 compressed/<sid>.md；② 或去重——关系统 compression 只用 processor+读取端。两路均依赖 P3 收口。
- 验证：当前 session 171 条消息无系统压缩产物行（processor 未接入、系统压缩在 50% 预算前不触发），processor 读数与钩子行为一致。
- 决策人：@lan（确认保持现状）/ Hermes（诊断 + 认知纠正）

## [2026-07-13] refactor: 门禁评审 P1+P2 — 清 trigger 泛用词 + infrastructure 重型 skill 体检
- 类型：refactor（trigger 净噪声清理）+ audit（体检，无新增门禁）
- 触发：3 条演进记录触发框架快速评审，评审给出 P1/P2/P3 三待办；老黎确认 P1 执行、P2 体检、P3 保持开放。
- P1（已执行）：hermes-framework 的 trigger 删「改进/优化/重构/增量变更」4 个裸泛用词，description 同步删「改进/优化/重构/patch/增量变更/进化」。理由：reference 已实证这些词不在 sparse 字典（噪声全来自中文单字切分），却占 dense 语义空间；与门禁的「专名哲学」一致。保留「架构优化/重构框架」（带框架限定的专名组合）与 §8 规则名描述「改进优先于新增」（非触发词）。验证：删后框架 query 用专名仍命中 3/3，业务泄漏 0/2，证明泛用词是净噪声。
- P2（已执行，结论=不新增门禁）：infrastructure/ 仅 3 个 skill。hermes-framework（2986t）已有门禁；hermes-context-compression（2605t）虽偏重但 trigger 专属（token太多/上下文太长/会话卡顿），业务 query 实测零误命中，不需门禁；hermes-web-tooling（1317t）轻量，"帮我调试报错"仅命中其 #5 末位（因 trigger 含"报错"），fault-troubleshooting/debugging-patterns 正确占据 #1/#2，末位轻量召回危害可忽略，不值得门禁。判据修正：门禁是为「重型文档(>3K token)误占 top1-3 高位」设计，非用于轻量末位召回。
- P3（保持开放）：context-compression 铁律#7（优先读 compressed 摘要）仍处「等真实运行验证」阶段，不写 SOUL.md。
- 验证：vdb build_index(force) 68 技能重建 healthy=True；框架 query 命中 3/3；业务泄漏 0/2。
- 决策人：@lan（确认 P1 执行 + P2 判据 + P3 开放）/ Hermes（评审 + 数据体检）

## [2026-07-13] feat: 门禁 v2 — 声明式加载 + micro-framework 注册指引 + hermes-framework 样板
- 类型：feat（在 v1 静态门禁基础上加去中心化声明式机制）
- 背景：老黎要求"新增/安装 skill 时门禁可自动登记"。区分了「约定层」（文档指引）与「机制层」（自动扫描），持久化由 git 负责（否决把门禁写进 SOUL/MEMORY——违反配置与逻辑分离）。
- 落地三件（A+B，不动 install.sh）：
  1. B-机制：vdb/routing.py 增声明式加载。技能 SKILL.md frontmatter 写 metadata.hermes.gate={enabled:true, keywords:[...]}，模块加载时 reload_gate_config() 自动扫描注册。默认安全（未声明的技能永不受门禁）；声明式覆盖静态同名键。get_gated_skills() 合并静态+声明式。
  2. A-约定：skills/integration/hermes-micro-framework/SKILL.md Common Pitfalls 加 4b 条——重型文档类 skill（>3K字符、描述框架本身）新增时必须登记门禁，静态或声明式二选一，禁用裸词 hermes。
  3. 样板：hermes-framework 自身 frontmatter 加 gate 声明（13 专名词），示范声明式用法；hermes-micro-framework 仍走静态，双模式共存验证。
- 老黎方案的 4 处纠正（均实测证明必要，否则致命）：① import 用 `import routing` 非 `from . import`（单文件脚本非包，后者 ImportError 直接废掉 search）；② glob 扫描过滤 .archive/.curator_backups（否则 5 个归档 framework-* 副本污染门禁）；③ FRAMEWORK_GATE_KEYWORDS 剔除裸词 hermes/Hermes（承 v1 数据结论，会误伤"hermes怎么配置"）；④ is_query_allowed 空 query 判断移到 in-gated 之后（避免歧义误伤非门禁技能）。
- 验证（5+项全绿）：routing 单元 9/9；声明式加载测试（临时 skill 注册 + archive 过滤 + 关键词生效）通过；端到端业务泄漏 0/4、框架命中 3/3；hermes-framework frontmatter YAML 合法、gate 13 词读取、声明式覆盖静态；vdb build_index(force) 68 技能重建 healthy=True；脱敏无敏感。
- 决策人：@lan（方案架构 + 声明式方向）/ Hermes（4 处数据纠正 + 编号修复 + 验证）

## [2026-07-13] feat: vdb 检索加装"专名门禁"路由层（vdb/routing.py）
- 类型：feat（进检索前的意图分层，符合老黎"进向量前路由而非改融合分数"立场）
- 根因（实测三连否定，非直觉）：业务类 query（"重构函数"/"优化性能"）会误命中重型文档 hermes-framework（~17K字符/~7K token），瞬间注入。① disable 标签是字面子串匹配、写的是书面短语（"用户业务代码变更"），用户不会这么说 → 形同虚设；② trigger 摘泛用词无效——泛用词根本不在 sparse 字典，噪声来自中文单字切分（重·构·优·化 都进字典）+ dense 语义歧义；③ startswith('hermes-') 粗过滤会误杀 18 个日常 hermes-* 技能。
- 方案：新建 vdb/routing.py，专名门禁——GATED_SKILLS={hermes-framework, hermes-micro-framework} 只在 query 含框架专名（SOUL/vdb/铁律/召回/微内核…业务代码不会出现的词）时才放行；其余技能一律不管。裸词 "hermes" 实测会误伤 "hermes怎么配置" 等日常 query，已剔除。matcher.search() line150 排序后、返回前插 1 行门禁过滤。
- 落地边界：全在 ~/.hermes/vdb（私有引擎，白名单跟踪），零侵入 Hermes 核心；未来加 mlops-/media- 族门禁只改 routing.py，不动 matcher.py。
- 验证：routing 单元测试 9/9（含空query/大小写/非门禁放行边界）；端到端业务query泄漏 framework 0/4、框架query命中 3/3；vdb healthy=True。（"改vdb索引逻辑"→vdb-retrieval-pipeline 优先是正确召回，非缺陷。）
- 决策人：@lan（提方案架构）/ Hermes（数据验证+纠偏裸词hermes与前缀误杀）

## [2026-07-13] fix: 自检修复 SOUL.md 悬空 skill 引用 + 清 stale 索引
- 类型：fix（铁律引用失效 + 索引漂移）
- 根因：多个 framework/boundary/evolution 微技能已在 2.0 合并入 `hermes-framework` 总纲并归入 skills/.archive/，但 SOUL.md 的铁律 skill_view、路由表右栏、技能索引段仍引用旧名 → 实测 skill_view(name='hermes-boundary-no-*'/'hermes-evolution-rules'/'hermes-base-config-sync') 返回 not found，铁律 #5/#6 细则无法调出。
- 变更内容（全 patch，未整文件覆盖）：
  - 铁律 #5 → `hermes-framework` §8；铁律 #6 → `hermes-framework` §9（原引 6 个已归档 skill）
  - 路由表右栏 5 个 framework-* + 4 个 boundary-* + base-config-sync → 收敛到 `hermes-framework`/`repo-publishing-workflow`（真名可跳转）
  - 技能索引段 core/methodology/infrastructure/integration 四类更新为真实活跃 skill 名
  - vdb 索引 stale（hermes-context-compression/officecli-office-docs 改后未重建）→ build_index(force=True)，68 技能重建，stale=False
- 验证结果：铁律 skill_view 5/5 可加载、路由表右栏 24/24 可跳转、零悬空；实测 skill_view(hermes-framework + references) 正常；vdb stale=False。
- 澄清（非缺陷）：磁盘 138 SKILL.md 中 70 个在 .archive/（故意不索引），68 个活跃全部已索引，索引完整性无问题。
- 决策人：@lan / Hermes 自检

## [2026-07-10] feat: 极致拆解 SOUL.md，创建 4 个新 skill
- 类型：refactor / feat
- 原因：SOUL.md token 太大（12,529ch），极致拆解后降至 4,783ch
- 变更内容：
  - SOUL.md §框架故障处理 → 独立 skill infrastructure/hermes-framework-troubleshooting
  - SOUL.md §增加约束/方法守则 → 独立 skill methodology/hermes-framework-evolution
  - 铁律#6 细则 → 独立 skill core/hermes-focus-scope
  - 新增 methodology/hermes-framework-changelog（框架变更审计）
  - SOUL.md 路由表新增 3 行
- 验证结果：待 vdb 重建后确认 recall
- 决策人：@lan

## [2026-07-11] docs: 确立「配置领域无关性」原则
- 类型：docs / feat（认知固化，非代码变更）
- 原因：纠正归因——"当前配置适合什么生产类型"不应由 SOUL.md 铁律决定，铁律是跨领域通用宪法；真正决定适配度的是 skills/ 资产库的主题分布（vdb 按需注入，不命中的 skill 永不进对话）。
- 变更内容：
  - 记忆固化：配置领域无关性原则（MEMORY.md）
  - hermes-framework 总纲 §0 概览补「配置领域无关性」原则
  - repo README.md 新增「配置领域无关性」小节（§使用 之后、§技能全集 之前）
- 推论：想让配置适配新生产类型 = 往 skills/ 加对应 skill + rebuild vdb，无需改 SOUL。
- 验证结果：记忆写入成功（77% 用量）；README/hermes-framework 两处 patch 已落地，待下次 repo 推送同步
- 决策人：@lan

## [2026-07-12] security: repo 发布安全门下沉到底层 workflow
- 类型：security / workflow-hardening
- 原因：用户指出"正确做法是底层框架加强 agent 发布 repo 的安全操作"。真实运行凭据若进入公开 repo，delete/archive 不能消除 clone/fork/cache/历史扩散风险，必须在 agent 发布流程中前置拦截，而非依赖人工记忆。
- 变更内容：
  - repo-publishing-workflow 新增 Step 0.7「运行环境凭据不可发布门禁」
  - hermes-safety 开源发布规则新增：真实运行凭据不得进 repo；泄露后先 rotate secret，再清历史/删除/归档
  - self-hosted-proxy-deployment 已补「凭据管理纪律」：真实接入参数只留运行环境，skill/templates 只留占位符
- 关键门禁：push 前必须扫描 staged diff 与工作树中的 proxy URI、password/uuid/key/指纹、mihomo/Xray config、SSH 命令和敏感文件名；命中即中止 commit/push。
- 验证结果：待执行脱敏扫描确认本次 skill 变更未含真实凭据。
- 决策人：@lan

## [2026-07-12] feat: 新增 context-compression skill + 上下文分类治理（SpanKind 迁移）
- 类型：feat / methodology（新能力 + 新方法论）
- 原因：分析 GitHub trending 项目 dcg（Destructive Command Guard）时，用户指出"对其安全护栏不关心，关心它的架构与 agent 钩子关系，以及相比 vdb 可借鉴的先进理念"。从 dcg 的 SpanKind（命令上下文分类：Executed/Data/Comment）提炼出可迁移范式——先判断"这段输入是否影响结果"再决定动作，而非无差别处理。用户明确：置信度加权/分数微调不必做（向量天花板内允许命中失败），正确方向是"进检索前的路由/分层"。
- 变更内容：
  - 新增 skills/infrastructure/hermes-context-compression/SKILL.md（触发词：token 太多/上下文太长/压缩对话/历史检索全是工具输出/会话卡顿/长 session 管理；disable：单轮短对话/保留完整日志/调试模式/审计合规）
  - scripts/init-context-tables.sql：建 message_tags.db 私有 side table（不侵入 Hermes 核心）
  - scripts/context-processor.py：规则分类最近 N 条消息（role=tool→DATA，assistant+tool_calls→EXECUTED），compress_ratio EXECUTED=1.0/DATA=0.08/ARGUMENT=0.2
  - scripts/vdb-autoload.py：新增 --process-context 开关，--auto 模式自动触发分类
  - 落地方式守"核心窄腰"约束：不改 hermes_state.py 核心，历史检索优先用现有 role_filter=["user","assistant"] 排除 tool（Data 类）
  - ~/.hermes 初始化本地 git 仓库（无 remote），vdb 源码白名单跟踪 + tag vdb-v2.1-context-routing 方便回滚
- 真实验证数据（state.db 两个长 session 实测）：
  - Data 类占 75.5%/85.4% token；分类压缩省 74.1%/83.0%；执行上下文保留 100%
  - 历史检索命中执行决策率：FTS 全文 50% → 分类优先 100%（关键词 disable 实测）
  - 已分类 208 条消息：EXECUTED 101 / DATA 96 / ARGUMENT 11
- 能力边界（如实记录，不夸大）：真实价值集中在"Data 识别"这一刀；COMMENT 类实测 0（此用户交互风格直接给方案）；复杂边缘场景（tool 输出混决策）暂不处理。
- 决策人：@lan

## [2026-07-12] insight: 外部范式借鉴的通用纪律（来自 context-compression 诞生会话）
- 类型：insight / methodology（迁移外部范式的方法论固化，由框架自注入 SKILL.md 设计原则段，此处收口到演进记录）
- 原因：本次从 dcg 成功迁移 SpanKind，需固化"怎么借外部项目"的纪律，避免未来空谈式借鉴。
- 三条纪律：
  1. 分析外部项目重其**架构/钩子关系**而非功能清单；借用的理念须用**真实数据验证**而非空谈。
  2. 向量/语义检索天花板内，不靠置信度加权/分数微调抢救失败 case；正确方向是"进检索前的路由/分层"。
  3. 落地实现优先私有侧扩展（side table / 调用侧参数），**不侵入核心代码**，符合 hermes-agent AGENTS.md 核心窄腰约束。
- 决策人：@lan

## [2026-07-13] SpanKind 实时上下文分类钩子落地（真实对话自动跑中，待观效）
- 类型：fix + integration（根治预设技能"空中楼阁"，接入真实路由）
- 根因两处地基 bug：① `context-processor.py` 的 STATE_DB 指向 `hermes-agent/state.db`（0字节空库），真实库在 `~/.hermes/state.db`；② message_tags.db 的 410 条标签关联空库 id，与真实消息错位。
- 修复（全在 ~/.hermes 边界内，零侵入核心）：STATE_DB 改正 + 清空错 id 旧库 + 补 ensure_schema()；脚本新增 get_current_session_id()/count_session_tokens()/generate_summary() + --min-messages/--min-tokens/--from-stdin/--summary（阈值自检 + 从 hook stdin JSON 取 session_id + 生成 memories/compressed/${sid}.md）；config.yaml 加 hooks.post_tool_call(matcher:terminal) + hooks_auto_accept:true。
- 验证：hermes hooks test 真实触发成功（exit=0,0.16s，id 对齐 state.max=12218=tags.max，分布 EXEC192/DATA179/ARG18，摘要 110KB）。
- 待观察：真实长对话中每次 terminal 调用自动刷新摘要的效果、压缩收益、有无性能/副作用。铁律#7（优先读 compressed 摘要）尚未写 SOUL.md，等真实跑一轮确认有效再补。
- 决策人：@lan / Hermes

## [2026-07-14] fix+docs: 修正 vdb 描述型 skill 与 matcher.py 实现漂移（RRF 滞后 + pin 绕过 review）
- 类型：fix（文档与代码实现对齐）+ docs（把隐性同步纪律显式化进流程）
- 触发：例行检查 skill 创建规则/架构说明时，发现 `vdb-retrieval-pipeline`（priority: highest，被 pin 保护）的描述仍写「打分: 0.6dense+0.4sparse」，而 `matcher.py` 早在 2026-07-11 就切到 RRF(K=60) 倒数排名融合。同批过期的还有 autoload-vdb 的「58 技能」数字、hermes-framework 的「活跃 ~68 技能」——实测 vdb 索引已 99 技能（含 27 个软链目录如飞书 lark-*，os.walk(followlinks=True) 跟进）。
- 根因（两层，非单一）：
  1. **代码改了但描述型 skill 没同步**：matcher.py 融合策略变更后，没有任何清单强制同步 `vdb-retrieval-pipeline` / `autoload-vdb` 的描述段 → 文档停留在旧实现长达 3 天无人发现。
  2. **pin 机制绕过了日常 review**：vdb-retrieval-pipeline 被 `hermes curator pin` 保护，日常改动需先 unpin，但「pin 状态下该走的解 pin 流程」从未写进任何文档 → 它既被保护、又因不被碰而长期滞后。pin 的意义是「防止误改」，不是「绕过审核」——缺的是配套的 unpin→review→re-pin 流程。
- 变更内容（全 patch，rebuild vdb 验证召回）：
  - `vdb-retrieval-pipeline`：unpin → 描述段「0.6dense+0.4sparse」→ RRF(K=60) 公式 + 标注已弃用；架构图同改；sparse 输入「仅 trigger_tags」→「trigger_tags + desc 中文短语(IDF 增强)」；权重段「可调 VEC_WEIGHT/SPARSE_WEIGHT」→ 明确「两常量仅保留不参与实际打分，调无效」；数字 99 技能 → 重新 pin。
  - `autoload-vdb`：文件结构注释「chroma/ ~1.2MB / 58 技能」→ 99；§3「58 个技能」→ 99。（正文 §5 已于 2026-07-11 正确写 RRF，仅注释数字过期。）
  - `hermes-framework`：文件结构「活跃 ~68 技能」→「活跃 ~99 技能（含 27 软链目录；vdb 索引实测 99）」。
  - `hermes-framework` §6 变更日志规范：新增**「⚠ 跨 skill 同步清单（vdb 代码改动必做）」**——改 vdb/ 融合或索引逻辑后必须同步两个描述型 skill（融合公式/sparse 输入/技能数/依赖），并新增**「关于 pin 保护 skill 的同步」**指引：目标 skill 被 pin 时须 `unpin → review → 同步 → re-pin`，禁止 pin 状态下直接改或跳过 review。
- 验证（真实）：vdb build_index(force) 99 技能 healthy=True；召回「技能检索管道/融合策略/vdb 架构」→ vdb-retrieval-pipeline 正确命中；「技能语义匹配怎么搭」→ autoload-vdb；vdb-retrieval-pipeline 重新 pin 闭环（curator: pinned, bypass auto-transitions）。
- 方法论价值（隐性知识显式化）：本次本质是「代码-文档漂移」类问题的典型案例——**代码改了，但描述它的 skill 因无强制同步清单 + 被 pin 绕过 review 而长期失真**。纠正不是补一次文档，而是把「vdb 代码改动 → 同步两描述型 skill → pin 走解 pin 流程」沉淀为 hermes-framework §6 的强制检查项。框架演进中这类「隐性纪律」应主动显式化、流程化，避免同样问题在另一个被 pin 的 skill 上重演。
- 边界认知：skills/ 内的历史实证数字（code-simplification 的「58 技能 FAISS 过度工程」演进叙事、autoload-vdb 的 2026-07-09 benchmark 数据）是当时真实快照，属封存证据，**不改**——改了反而破坏叙事真实性。
- 决策人：@lan（拍板保留 trigger 词、确认同步清单+pin 指引写入、强烈建议记入本文件）/ Hermes（诊断 + 修正 + 验证 + 沉淀）
