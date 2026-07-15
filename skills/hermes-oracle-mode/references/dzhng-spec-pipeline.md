# dzhng/skills Spec Pipeline 方法论补强

来源：https://github.com/dzhng/skills（clone 到 `/tmp/dzhng-skills/`）
适用：`hermes-oracle-mode` 现有七步流程（派发-验证-交付）之外的**spec-slice 切片**与**close-spec rationale** 方法论

## 一、Spec-Slice 流水线（替换七步流程的子任务切分环节）

dzhng `write-spec` + `implement-spec` + `review` + `close-spec` 链条直接对应 oracle mode 的子任务切分与终审。

### 1.1 先 grill 后 plan

**当前 oracle 流程**：任务解析直接列出子任务清单（plan mode 路径）。
**补强**：在列子任务前，**逐问探 fog-of-war**（已知/未知/盲区/不存在的图），每个问题带推荐答案让用户接受/拒绝/改。

> 一个 slice 必须有：想要的产物 + non-goals + 审阅面 + 神圣契约 + 缺失素材 + 第一个可玩检查点。少一个 = 不切片，先 grill。

### 1.2 按 API seam 切

**当前 oracle 流程**：按文件/子系统切子任务（dispatching-parallel-agents §8.3 已有）。
**补强**：每个 slice 必须像"一个小库"——命名模块边界、类型化输入/输出、确定性 fixture、seam 处的测试。**三个不相关系统要 boot 才能 verify = 切错了**，打磨 seam。

### 1.3 递归揭 fog-of-war

**当前 oracle 流程**：第一版 plan → 派发 → 验证（线性）。
**补强**：**第一张 slice graph 是 scouting pass，不是证明**。每个高风险 slice 自身当作 feature 检查：藏多个变量 / 不熟域 / 未证架构 / "实现时再说" → reslice 子集，递归到每个下个 slice 都只有一问、一 seam、一审阅面、一 verdict。

### 1.4 并行多草稿 → 合成

**当前 oracle 流程**：单次 plan 路径。
**补强**：对 multi-slice feature，**fan out 2-3 个独立草稿**，每个不同 bias（视角）+ 不同 model family，**blind 跑**。合议点 = 切分扎实。分歧点 = 单 plan 漏的 seam/risk。

### 1.5 一视觉变量一切片（视觉类特化）

Web/UI 任务：单 slice 不能要求"匹配最终 hero 图"。**按被判项切**：密度/轮廓/色/纹理/光照/雾/水的布置/水的材质/标签可读性/动画节奏。**每片带 crop/mask 和该变量 verdict**。**整帧对比只在 compose/integration 阶段**。

## 二、Implement-Spec 流程（替换七步流程的"子 Agent 派发"段）

### 2.1 每个 slice 独立可验证

**当前 oracle 流程**（dispatching-parallel-agents §8）：子任务独立、无共享状态。
**补强**：每个 slice 必须**有独立测试表面**（named module + typed I/O + deterministic fixture + seam test）。**不能跨 slice 共享状态做 verification**。

### 2.2 反馈循环优先

**当前 oracle 流程**：派发 → 等待 → 验证（串行）。
**补强**：slice 设计要**让下一个有用问题被快速回答**。优先：
- 极小可跑表面（路由、fixture page、harness、CLI probe、HTML 可视化）
- 热重载 harness
- 自包含 workbench
- asset-heavy 工作流：先做 asset app/workbench，让人/artist 加 sample、live preview、快看 validation failure

**不**做"整个 feature 存在后才能学"的 plan。

### 2.3 缺料不阻塞

**当前 oracle 流程**：缺凭证/外部素材 → 阻塞。
**补强**：**生成 placeholder + 替换契约**。Feature 用 placeholder 推进，单独 handoff 路径说明"用户/外部伙伴需提供什么"。

### 2.4 仓库存形状

**当前 oracle 流程**：默认按现有 app 结构推进。
**补强**：**monorepo → plan apps 和 packages**，不把新行为塞到当前 app。**每个可测表面 = 一级路由/命令**，不藏到不透明 query flag 后。

## 三、Review 协议（替换 oracle mode "质量验证"段）

来源：dzhng `review` 34 行 + `refactor-clean` + `code-review` + `write-docs` 合成。

**三层 closeout**（一个 verdict 顺序过）：

### 3.1 refactor-clean

**当前 oracle 流程**：没有"先重构后审稿"层。
**补强**：**先 move ownership 到一个 clean concept**，不在问题旁加 compatibility sediment。**refactor 失败的 change 不许进 review**。

### 3.2 code-review

**当前 oracle 流程**：验证清单按"数据/服务/连接/逻辑"分面。
**补强**：审 stale 名词、dead 引用、needless complexity、只复述代码不解释的注释。**输出 clean / not-clean 二值 verdict**，不输出"还可以"。

### 3.3 write-docs

**当前 oracle 流程**：交付物即文档（单一 Markdown）。
**补强**：**docs 写成原则 + 指针的 glossary**，**禁止**成代码镜像（会腐烂）。引用"代码在哪"用指针，不复制。

## 四、Close-Spec（oracle mode 缺失的关键收尾）

**当前 oracle mode**：交付即结束，无"任务关闭后的 rationale record"。

**补强（dzhng `close-spec`）**：spec 落地后必须：
1. **归档 spec 文件**（不再可改）
2. **重写成 rationale record**（不是"怎么建"，是"为什么这么建"）
3. **指针指回代码**：当前 owner 位置、对应 commit、关键决策的 smell

**oracle 集成点**：oracle mode 七步流程的"交付输出"前加一步 `close-spec` —— 任务结束后把 spec/ 从 build plan 改成 rationale record，归档到 `~/.hermes/oracle/closed/<task>/`。

## 五、Leading Word 应用（oracle 风格）

dzhng 风格的 leading word 可直接套到 oracle mode 文档：

| 弱句 | leading word 替代 |
|---|---|
| "派发子任务后等待结果" | "fan out → collect" |
| "独立验证子 Agent 结果" | "blind judge" |
| "任务完成后归档" | "close-spec" |
| "复杂任务先理清未知" | "map fog-of-war" |
| "每个子任务独立可验证" | "API seam" |

替换原则：SKILL.md 里找 2+ 句能用一个已有概念词替代的，立即换。

## 六、Eval 协议（oracle 终审层补强）

oracle mode 现有"质量验证清单"是**静态 checklist**。dzhng 提供了**动态 eval 协议**：

- **不要把每条标准列成 checklist 让 judge 勾**——那是 conformance check，不是 judgment test
- **给 judge 的是"bar"（标准）+ "smells"（坏味道）**，让 judge 自由 fault "too coarse" 和 "too fine" 两边
- **Nondeterminism 兜底**：重要判定重跑 2-3 遍报 pass rate，不信单次 green
- **Blind 原则**：oracle 验证子 Agent 结果时，**不要让 judge 看到子 Agent 的"应该输出"**，只看到产物 + bar + first principles

**oracle 集成点**：把质量验证清单改造成"每项一个 bar 段落 + smell 清单"，judge subagent 拿这些去判。

## 七、ship standard（oracle mode 子任务切分质量门）

一个派发包算 ship-ready 当且仅当：

- [ ] 子任务 fog-of-war 已 grill 到每个 slice 一问
- [ ] 每个 slice 有独立 API seam + fixture + seam test
- [ ] 高风险 slice 自身已 reslice 过（递归到末梢）
- [ ] 2-3 个独立草稿已 fan out + 合成（multi-slice feature）
- [ ] 缺料已 plan placeholder + 替换契约
- [ ] close-spec 路径已设（`~/.hermes/oracle/closed/<task>/`）
- [ ] review 三层（refactor-clean / code-review / write-docs）顺序存在
- [ ] eval 协议走 blind judge + nondeterminism 兜底

**最后更新**: 2026-07-10
**来源 commit**: dzhng/skills @ main（2026-07 clone 到 `/tmp/dzhng-skills/`）
**冲突审计**：本参考文件未与 SKILL.md 现有七步流程冲突，作为"子任务切分/子 Agent 派发/质量验证/交付"四段的补强；不重写七步主体。
