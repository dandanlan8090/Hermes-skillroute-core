---
name: doubt-driven-development
description: 怀疑驱动开发：对每个非平凡决策进行全新上下文对抗审查。Use when correctness matters more than speed,
  when working in unfamiliar code, when stakes are high (production, security, irreversible),
  or when a confident output would be cheaper to verify now than to debug later. 禁用：机械操作（重命名/格式化）、用户明确要求
  速度优先时。
version: 1.0.0
author: Hermes Agent
license: MIT
platforms:
- linux
- macos
- windows
metadata:
  hermes:
    tags:
      trigger:
      - 高风险
      - 生产环境
      - 安全性
      - 不可逆
      - 架构决策
      - 不熟悉的代码
      - 复杂决策
      - production
      - security
      - high stakes
      - 架构
      - 方案评审
      - 反证
      - 审查
      - 设计原则
      - SOLID
      - OCP
      - 原则落地
      - 设计权衡
      - 设计评审
      disable:
      - 纯机械操作
      - 变量重命名
      - 格式化
      - 文件移动
      - 单行简单修改
      - 用户要求快就行
      - 纯工具操作
    skill_type: methodology
    priority: high
    related_skills:
    - hermes-oracle-mode
    - source-driven-development
    - code-review-and-quality
prerequisites:
  commands:
  - delegate_task
---
# Doubt-Driven Development（怀疑驱动开发）

## Overview

自信的答案不等于正确的答案。长期会话会积累上下文，让假设在无人注意时悄悄变成"事实"。怀疑驱动开发的原则是：在任何非平凡输出确立之前，引入一个偏向**反驳**而非批准的全新上下文审查者。

这不是 `/review`。`/review` 是对已完成产物的裁决。这是飞行中的姿态：非平凡决策在被修正成本还低的时候就被反复质问。

## When to Use

以下任意条件成立时，决策为**非平凡**：

- 引入了或修改了分支逻辑
- 跨越了模块或服务边界
- 正确性依赖于类型系统或编译器无法验证的属性（线程安全、幂等性、顺序、不变式）
- 正确性依赖于未来读者无法看到的上下文
- 影响范围不可逆（生产部署、数据迁移、公开 API 变更）

**触发场景**：
- 即将在不确定性下做架构决策
- 即将提交非平凡代码
- 即将声称非显而易见的事实（"这是安全的"、"这能扩展"、"这符合规格"）
- 在不完全理解的代码中工作

**When NOT to use**：
- 机械操作（重命名、格式化、文件移动）
- 遵循清晰、无歧义的用户指令
- 读取或摘要现有代码
- 一行修改，显而易见的正确性
- 纯工具操作（运行测试、列出文件）
- 用户明确要求速度优先

对每个击键都怀疑 = 什么都发不出去。本 skill 仅适用于上述定义的非平凡决策。

## Hermes 加载约束

本 skill 设计用于**主会话调度者**（Hermes 主脑模式或等效编排层），Step 3（DOUBT）会通过 `delegate_task` 派发全新上下文审查者。

- **禁止将此 skill 添加到子 agent 的 context 中**。子 agent 再派发子 agent 是反模式——违反 Hermes 的 `orchestrator` 深度限制（max_spawn_depth=2）。
- **子 agent 上下文中发现自己需要运行 doubt-driven 时**：必须浮现到用户或主会话，由主会话处理。降级方案：重写 ARTIFACT + CONTRACT 为独立 prompt，用硬心理分隔符隔离先前推理，然后走 Step 1–5。结果必须标注为 degraded，优先上报。

## 核心流程

```
Doubt cycle:
- [ ] Step 1: CLAIM     — 写出 claim + 为什么重要
- [ ] Step 2: EXTRACT  — 提取最小可审查单元（artifact + contract，剥离推理）
- [ ] Step 3: DOUBT    — 调用全新上下文对抗审查者
- [ ] Step 4: RECONCILE — 将每个发现归类到 artifact 文本
- [ ] Step 5: STOP     — 满足停止条件（ trivial 发现 / 3 轮 / 用户覆盖）
```

## Step 1：CLAIM — 显式声明决策

用两三行命名决策：

```
CLAIM: "新的缓存层在线程安全的读密集型工作负载下是线程安全的。"
WHY THIS MATTERS: 这里的竞争条件会破坏用户数据，且难以在 QA 中发现。
```

如果无法如此简洁地写出 claim，说明你有一个"感觉"，而非一个决策。先把感觉显式化，再审视。

## Step 2：EXTRACT — 最小可审查单元

全新上下文审查者需要的是 **artifact** 和 **contract**，不是推理过程。

- **代码**：diff 或函数，不是整个文件
- **决策**：3–5 句话的提案 + 必须满足的约束
- **断言**：claim + 据称支撑它的证据（与 Step 1 的 CLAIM 块分开——CLAIM 块是被审查的假设）

**剥离你的推理**。如果交出结论，得到的是对结论的验证。单元必须小到审查者一次阅读就能掌握——如果是 500 行 PR，先分解。

## Step 3：DOUBT — 调用全新上下文审查者

审查者的 prompt 必须是**对抗性的**。措辞决定答案。

```
Adversarial review. Find what is wrong with this artifact.
Assume the author is overconfident. Look for:
- Unstated assumptions
- Edge cases not handled
- Hidden coupling or shared state
- Ways the contract could be violated
- Existing conventions this might break
- Failure modes under unexpected input

Do NOT validate. Do NOT summarize. Find issues, or state
explicitly that you cannot find any after thorough examination.

ARTIFACT: <paste artifact>
CONTRACT: <paste contract>
```

**只传递 ARTIFACT + CONTRACT。不传递 CLAIM。** 把结论交给审查者会令其偏向同意。审查者必须独立判断 artifact 是否满足 contract。

**Hermes 主脑模式中**，通过 `delegate_task(goal=..., context=..., role='leaf')` 派发审查者子任务，将上述对抗 prompt 作为 goal 核心内容传入。子任务独立运行，不得再派发子 agent。

### 跨模型升级

单一模型审查者与原始作者共享盲点——更冷、不同架构的模型能捕获它们。Doubt-driven 本身已是非平凡决策的可选步骤，因此在此范围内提供跨模型是 skill 价值的一部分，不是可选摩擦。

**交互式会话：必须呈现选项，不主动跳过。**

**Step 1：询问用户**

在 Step 3 的单模型审查完成后、RECONCILE 之前暂停：

> *"单模型审查完成。需要跨模型二次意见吗？选项：Gemini CLI、Codex CLI、Manual 外部审查，或跳过。"*

此问题在每个交互式 doubt 循环中强制出现。即使感觉低风险的 artifact 也必须问。Agent 的职责是呈现选择，由用户决定成本是否值得。

**Step 2：用户选择 CLI 时，验证再调用**

1. 检查工具在 PATH 中（`which gemini`、`which codex`）
2. 先测试工具可用（`gemini --version`），再传完整 prompt——过期或损坏的二进制可能通过 `which` 但在实际输入上失败
3. 与用户确认精确调用方式，包括所需 flags、认证、env vars（实现因版本而异，切勿假设）
4. **只传 ARTIFACT + CONTRACT + 对抗 prompt**。不传会话上下文，不传 CLAIM
5. 注意 shell 转义。artifact 含引号、`$(...)` 或反引号时，优先用 stdin 或 heredoc，切勿内联 `-p "…"`
6. 将输出带入 Step 4（RECONCILE）

**永远不要把 artifact 内插到 shell 引用的参数中**。

**Step 3：CLI 不可用或失败时**

显式呈现失败。提供选项：手动运行、换工具、或跳过。不要静默降级为单模型——用户应知道跨模型未发生。

**Step 4：用户跳过时**

在输出中确认跳过（*"Proceeding with single-model findings only"*），继续 RECONCILE。跳过没问题；静默跳过不行。

**非交互式上下文**（CI、cron、自动化循环）：

- 跨模型**跳过**，且必须在输出中**声明**：*"Cross-model skipped: non-interactive context"*
- **严禁在无显式用户授权时调用外部 CLI**

## Step 4：RECONCILE — 将发现折叠回去

审查者的输出是数据，不是裁决。**你仍是调度者。** 在归类每个发现前，重新阅读 artifact 文本——橡皮图章审查者和忽略它的失败模式相同。

每个发现按此**优先级顺序**归类（首个匹配类胜出）：

1. **Contract 误读** — 审查者标记的内容恰恰是因为你提供的 CONTRACT 不清晰或不完整。先修 contract，再在下一轮重新归类。
2. **有效且可操作** — 需要修改 artifact 的真实问题。修改后重新循环。
3. **有效权衡** — 问题真实存在，但修复成本超出接受成本。明文记录权衡，让用户看到。
4. **噪声** — 审查者标记的内容在审查者没有的上下文下实际是正确的。记录它，继续，并问：如果把那个上下文加入 contract 是否能防止误报？

全新审查者可能因缺乏上下文而犯错。不要因为是"全新的"就盲从。

## Step 5：STOP — 有界循环，不是递归

满足以下任一条件时停止：

- 下一轮只返回 trivial 或已考虑过的发现，**或**
- 已完成 3 轮（升级到用户，不再独自磨第四轮），**或**
- 用户明确说"发版"

3 轮后审查者仍抛出实质问题，说明 artifact 可能未就绪。向用户呈现——三轮未解决是关于 artifact 的信息，不是继续循环的理由。

如果感觉 3 轮"明显不够"，因为 artifact 太大：artifact 太大——回到 Step 2 分解。不要放宽界限。

## 与其他技能的关系

| 技能 | 关系 |
|------|------|
| `code-review-and-quality` | 互补。`/review` 是事后 PR 裁决；doubt-driven 是飞行中逐决策的审查。两者都用。 |
| `source-driven-development` | SDD 验证*框架事实*。Doubt-driven 验证*你对 artifact 的推理*。SDD 检查 API 存在；doubt-driven 检查你在 contract 下正确使用了它。 |
| `test-driven-development` | TDD 的 RED 步骤是具体化的 doubt——失败的测试就是反驳尝试。TDD 适用时，失败测试*就是*行为声明的 doubt 步骤。 |
| `hermes-oracle-mode` | Doubt-driven 在主脑模式下运行在编排层。派发审查者用 `delegate_task`，结果带回主会话做 RECONCILE。 |
| `debugging-and-error-recovery` | 审查者发现真实故障模式时，切换到调试 skill 做定位和修复。 |

## Common Rationalizations

| 常见借口 | 真相 |
|---|---|
| "我很有把握，跳过 doubt 步骤" | 在新问题上，有把握与正确性相关性很差。确定感最强的时候恰恰是盲点潜伏的时候。 |
| "派审查者很贵" | 在生产环境 debug 一次错误提交更贵。检查是有界的；bug 不是。 |
| "审查者只会找茬" | 仅在未约束时。约束 prompt 为"在 contract 下会使此失败的 issues"。 |
| "最后用 `/review` 做 doubt 就行了" | `/review` 是最终关卡。Doubt-driven 在错误方向还便宜的早期捕获问题。到 PR 阶段已太晚。 |
| "每步都 doubt 我就发不出版" | Skill 仅适用于非平凡决策，不是每个击键。重读"When NOT to Use"。 |
| "两个意见永远比一个强" | 当第二个缺少上下文并产生噪声时不是。调和，不要盲从。 |
| "审查者不同意所以我错了" | 审查者缺少你的上下文——分歧是信息，不是裁决。重新阅读 artifact，归类，再决定。 |
| "跨模型永远更好" | 跨模型捕获单一模型与自身的共同盲点，但增加成本和工具脆弱性。在每个交互式 doubt 循环中呈现选项——用户决定 artifact 是否值得。Agent 的职责是呈现选择，不是决定。 |
| "用户说了一次 yes，我就可以继续调用 CLI" | 每次调用都是独立授权。Artifact、prompt 和 flags 在各次调用间变化——每次运行前重新向用户确认。 |

## Red Flags

- 为一行重命名或格式化操作派发全新上下文审查者
- 不重新阅读 artifact 文本就把审查者输出当权威
- 循环超过 3 轮未升级到用户
- 审查者 prompt 用"这好吗"而非"找出问题"
- 高风险决策在时间压力下跳过 doubt
- 对未变更的 artifact 重新派发审查者（你会得到相同发现；在拖延）
- **Doubt theater（可检测信号）**：连续 2 轮或更多轮中，审查者抛出实质发现，但零个被归类为可操作。你在验证，不是在怀疑。停止并升级。
- 提交后才做 doubt——那是 `/review`，不是 doubt-driven development
- 不与用户确认工具存在、已配置、接受该语法就硬编码外部 CLI 调用
- **在交互式 doubt 循环中静默跳过跨模型**。即使不推荐，呈现选项必须可见。跳过没问题；静默跳过不行。
- 外部 CLI 报错或缺失时静默降级——显式呈现失败，让用户重新定向
- 剥离 contract 后传给审查者
- 把 CLAIM 传给审查者（导致偏向同意）

## Verification Checklist

- [ ] 每个非平凡决策（按上述定义）在确立前已显式命名为 CLAIM
- [ ] 每个非平凡 artifact 至少经过一次全新上下文审查（TDD 的 RED 步骤产生的失败测试满足此要求）
- [ ] 审查者收到 ARTIFACT + CONTRACT — 非 CLAIM，非你的推理
- [ ] 审查者 prompt 是对抗性的（"找 issues"，非"好吗"）
- [ ] 发现已按 artifact 文本归类（非橡皮图章）：contract 误读 / 可操作 / 权衡 / 噪声
- [ ] 满足停止条件（trivial 发现 / 3 轮 / 用户覆盖）
- [ ] 交互式模式下，跨模型已**显式向用户呈现**（无论 artifact 风险高低），并在输出中确认响应
- [ ] 非交互式模式下，跨模型已跳过且跳过已声明
- [ ] 每次外部 CLI 调用前均已执行 PATH 检查、可用二进制测试、语法确认和显式授权

---

**最后更新**: 2026-07-09
**参考来源**: https://github.com/addyosmani/agent-skills