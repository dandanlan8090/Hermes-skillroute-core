---
name: code-simplification
description: 代码简化：在保持行为完全不变的前提下降低复杂度。Use when refactoring for clarity, when code works
  but is hard to read/maintain/extend, or when reviewing code with accumulated unnecessary
  complexity. 禁用：代码已整洁时、不理解代码时、 性能关键路径（简化后可能变慢）时、重写整个模块时。
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
      - 简化
      - 重构
      - 清理代码
      - 复杂
      - 难读
      - 代码优化
      - refactor
      - simplify
      - cleanup
      - 代码评审
      - 降低复杂度
      disable:
      - 代码已整洁
      - 不理解代码
      - 性能关键
      - 即将重写整个模块
      - 用户未要求简化
    skill_type: methodology
    priority: normal
    related_skills:
    - code-review-and-quality
    - doubt-driven-development
prerequisites:
  commands:
  - terminal
  - read_file
  - patch
---
# Code Simplification（代码简化）

## Overview

通过降低复杂度同时保持精确行为来简化代码。目标不是更少的行数——而是更易阅读、理解、修改和 debug 的代码。每个简化必须通过一个简单测试："新团队成员理解这个是否比原始版本更快？"

> 灵感来源：Claude Code Simplifier plugin（Anthropic 官方）。已改造为任意 AI coding agent 可用的模型无关、流程驱动的 skill。

## When to Use

- 特性已工作、测试通过，但实现比需要的更重
- 代码审查中发现可读性或复杂度问题
- 遇到深嵌套逻辑、长函数、不清晰命名
- 重构时间压力下写的代码
- 合并后引入了重复或不一致
- 用户明确要求简化或整理代码

**When NOT to use**：
- 代码已经干净可读——不要为了简化而简化
- 还不知道代码做什么——先理解再简化
- 代码是性能关键路径——"更简单"的版本可能明显更慢
- 即将完全重写模块——简化废弃代码浪费精力

## 五项原则

### 1. 精确保持行为

不改变代码做什么——只改变它如何表达。所有输入、输出、副作用、错误行为、边界情况必须完全相同。如果不确定简化是否保持行为，不要做。

```
每次变更前问：
→ 对每个输入产生相同输出吗？
→ 保持相同错误行为吗？
→ 保持相同副作用和顺序吗？
→ 所有现有测试仍然通过且无需修改吗？
```

### 2. 遵循项目惯例

简化意味着让代码与代码库更一致，而非施加外部偏好。简化前：

```
1. 读取 CLAUDE.md / 项目惯例
2. 研究相邻代码如何处理类似模式
3. 匹配项目的：
   - 导入顺序和模块系统
   - 函数声明风格
   - 命名约定
   - 错误处理模式
   - 类型注解深度
```

破坏项目一致性的简化不是简化——是 churn（无效改动）。

### 3. 清晰优先于技巧

当简洁版本需要 mental pause 来解析时，显式代码优于紧凑代码。

```typescript
// 不清晰：密集三元链
const label = isNew ? 'New' : isUpdated ? 'Updated' : isArchived ? 'Archived' : 'Active';

// 清晰：可读映射
function getStatusLabel(item: Item): string {
  if (item.isNew) return 'New';
  if (item.isUpdated) return 'Updated';
  if (item.isArchived) return 'Archived';
  return 'Active';
}
```

```typescript
// 不清晰：链式 reduce 带内联逻辑
const result = items.reduce((acc, item) => ({
  ...acc,
  [item.id]: { ...acc[item.id], count: (acc[item.id]?.count ?? 0) + 1 }
}), {});

// 清晰：命名中间步骤
const countById = new Map<string, number>();
for (const item of items) {
  countById.set(item.id, (countById.get(item.id) ?? 0) + 1);
}
```

### 4. 保持平衡

简化有失败模式：过度简化。警惕这些陷阱：

- **过度内联** — 移除给了概念名字的帮助函数使调用点更难读
- **合并不相关逻辑** — 两个简单函数合并为一个复杂函数不会更简单
- **移除"不必要"的抽象** — 一些抽象为可扩展性或可测试性而存在，不是为复杂度
- **优化行数** — 更少的行不是目标；更易理解才是

### 5. 限定范围在变更处

默认只简化最近修改的代码。除非明确要求扩大范围，避免顺便重构无关代码。无范围简化会在 diff 中产生噪音并带来意外回归风险。

## 简化流程

### Step 1：触碰前先理解（Chesterton's Fence）

在改变或移除任何东西之前，理解它为什么存在。这就是 Chesterton's Fence：如果你看到路中间有围栏但不理解为什么在那里，不要拆掉它。先理解原因，再判断原因是否仍然适用。

```
简化前必须回答：
- 这段代码的职责是什么？
- 谁调用它？它调用谁？
- 边界情况和错误路径是什么？
- 有定义预期行为的测试吗？
- 为什么可能写成这样？（性能？平台约束？历史原因？）
- 检查 git blame：这段代码的原始上下文是什么？
```

如果答不上来，还没准备好简化。先读更多上下文。

### Step 2：识别简化机会

扫描这些模式——每个都是具体信号，不是模糊味道：

**结构性复杂度**：

| 模式 | 信号 | 简化方法 |
|------|------|----------|
| 深嵌套（3+ 层） | 控制流难追踪 | 将条件提取为 guard clauses 或 helper 函数 |
| 长函数（50+ 行） | 多重职责 | 拆分为聚焦的、带描述性名字的函数 |
| 嵌套三元 | 需要 mental stack 解析 | 替换为 if/else 链、switch 或查找对象 |
| 布尔参数 flags | `doThing(true, false, true)` | 替换为 options 对象或分离函数 |
| 重复条件判断 | 多处相同的 `if` 检查 | 提取为命名良好的谓词函数 |

**命名和可读性**：

| 模式 | 信号 | 简化方法 |
|------|------|----------|
| 通用命名 | `data`, `result`, `temp`, `val` | 重命名为描述内容：`userProfile`, `validationErrors` |
| 缩写命名 | `usr`, `cfg`, `btn`, `evt` | 用全词，除非是通用缩写（`id`, `url`, `api`） |
| 误导性命名 | 函数名 `get` 但实际修改状态 | 重命名以反映实际行为 |
| 解释"what"的注释 | `// increment counter` 在 `count++` 上方 | 删除注释——代码已经够清晰 |
| 解释"why"的注释 | `// Retry because the API is flaky under load` | 保留——这些携带代码无法表达的目的 |

**冗余**：

| 模式 | 信号 | 简化方法 |
|------|------|----------|
| 重复逻辑 | 多处相同的 5+ 行 | 提取为共享函数 |
| 死代码 | 不可达分支、未使用变量、注释掉的块 | 移除（确认真的死后再动） |
| 不必要的抽象 | 不添加值的包装器 | 内联包装器，直接调用底层函数 |
| 过度工程的模式 | 单策略的 factory、单策略的 strategy | 替换为简单直接方案 |
| 冗余类型断言 | 转换为已经推断出的类型 | 移除断言 |

### Step 3：增量应用变更

一次做一个简化。每次变更后运行测试。**重构变更单独提交，与特性或 bugfix 变更分开。** 重构 + 加特性的 PR 是两个 PR——分开提交。

```
每次简化：
1. 做变更
2. 运行测试套件
3. 测试通过 → 提交（或继续下一个简化）
4. 测试失败 → 回滚并重新考虑
```

避免把多个简化打包成一次未测试的变更。如果出问题，需要知道是哪个简化导致的。

**500 行规则**：如果重构会触及超过 500 行，投资自动化（codemods、sed 脚本、AST 转换）而非手工做。手工编辑到这个规模容易出错且审起来很累。

### Step 4：验证结果

所有简化完成后，退后一步评估整体：

```
对比前和后：
- 简化版本确实更易理解吗？
- 引入了与代码库不一致的新模式吗？
- diff 干净且可审查吗？
- 队友会批准这个变更吗？
```

如果"简化"版本更难理解或审查，回滚。不是每个简化尝试都成功。

## Real-World Example: vdb 架构三阶段简化 (2026-07)

**背景**：vdb（技能语义匹配系统）经历了三次架构迭代，每次都是简化。

**阶段 1 → 阶段 2（FAISS 6 文件 → 单文件 200 行）**：
原本由 6 个文件（~500 行）构成：core.py (FAISS)、embed.py (fastembed)、indexer.py、matcher.py、config.yaml、watcher.py。仅服务 58 个技能，复杂度远超需求。
简化后：~/.hermes/vdb/vdb.py 单文件 200 行，numpy 点积替代 FAISS，常量替代 config 系统。

**阶段 2 → 阶段 3（单文件 → Chroma + sparse 混合架构）**：
单文件架构解决了文件数问题，但稠密向量+英文 description 导致中文 keyword 匹配差（"写 SKILL.md"查不到 skill-authoring）。
简化后：Chroma 替代 numpy 存储 + 本地 sparse lexical 替代纯稠密语义。4 文件 ~800 行，57 技能 116ms 查询。

**最终架构**：
```
```
~/.hermes/vdb/
├── core.py          # FAISS IndexFlatIP 封装
├── embed.py         # fastembed 包装 + tag embedding
├── indexer.py       # 扫描 skills/ → FAISS 索引
├── matcher.py       # 三阶段流水线 + config 加载
├── config.yaml      # 所有权重/阈值
├── watcher.py       # inotify 监听
├── fix_tags.py      # 批量修复
├── __init__.py      # 包入口
├── autoload.py      # Hermes 启动钩子
├── index.faiss      # 二进制索引
├── tag_embeddings.npy
├── tag_index.json
```

*问题*：每一段功能都有自己的文件，但 58 个技能靠 numpy 点积 + argsort 就够，FAISS 完全多余。

**简化后**：
```
~/.hermes/vdb/
├── vdb.py           # ~200 行，唯一代码文件
├── __init__.py      # 导出 VDB
├── index.npy        # numpy (58, 1024) float32
├── meta.jsonl       # 元数据
```

*简化手段*：
1. 移除 FAISS → numpy 点积（58 个向量的事，不用引进重型索引）
2. 移除 config.yaml → 常量定义在文件顶部（< 10 个配置项不需要 config 系统）
3. 移除 watcher.py → 手动 build (force=True)（变化频率低，自动监听 ROI 低）
4. 合并所有类到一个 `VDB` 类，200 行可全文件阅读

**结果**：
| 指标 | 之前 | 之后 |
|------|------|------|
| 文件数 | 9 | 2 |
| 代码行数 | ~500 | ~200 |
| 索引构建 | 7s (本地 CPU) | 1.5s (API batch) |
| 模型替换点 | 7 处 | 1 处（MODEL 常量） |
| 跨语言匹配 | 零（BGE-Small-ZH） | 正确定位（BGE-M3） |
| 可理解性 | 需要跨文件跟踪 | 一个文件读完 |

**教训**：模块化不是免费的。每个文件增加心智负担。YAGNI 判断：在 < 1K 向量的场景，numpy 点积比 FAISS 更简单、更快理解、更容易替换。延迟 8ms→250ms 是可接受的代价（人类感知不到），换来了跨语言能力和架构简化。

### TypeScript / JavaScript

```typescript
// 简化：不必要的 async wrapper
// Before
async function getUser(id: string): Promise<User> {
  return await userService.findById(id);
}
// After
function getUser(id: string): Promise<User> {
  return userService.findById(id);
}

// 简化：冗长条件赋值
// Before
let displayName: string;
if (user.nickname) {
  displayName = user.nickname;
} else {
  displayName = user.fullName;
}
// After
const displayName = user.nickname || user.fullName;

// 简化：手工数组构建
// Before
const activeUsers: User[] = [];
for (const user of users) {
  if (user.isActive) {
    activeUsers.push(user);
  }
}
// After
const activeUsers = users.filter((user) => user.isActive);

// 简化：冗余布尔返回
// Before
function isValid(input: string): boolean {
  if (input.length > 0 && input.length < 100) {
    return true;
  }
  return false;
}
// After
function isValid(input: string): boolean {
  return input.length > 0 && input.length < 100;
}
```

### Python

```python
# 简化：冗长字典构建
# Before
result = {}
for item in items:
    result[item.id] = item.name
# After
result = {item.id: item.name for item in items}

# 简化：嵌套条件用 early return
# Before
def process(data):
    if data is not None:
        if data.is_valid():
            if data.has_permission():
                return do_work(data)
            else:
                raise PermissionError("No permission")
        else:
            raise ValueError("Invalid data")
    else:
        raise TypeError("Data is None")
# After
def process(data):
    if data is None:
        raise TypeError("Data is None")
    if not data.is_valid():
        raise ValueError("Invalid data")
    if not data.has_permission():
        raise PermissionError("No permission")
    return do_work(data)
```

### React / JSX

```tsx
// 简化：冗长条件渲染
// Before
function UserBadge({ user }: Props) {
  if (user.isAdmin) {
    return <Badge variant="admin">Admin</Badge>;
  } else {
    return <Badge variant="default">User</Badge>;
  }
}
// After
function UserBadge({ user }: Props) {
  const variant = user.isAdmin ? 'admin' : 'default';
  const label = user.isAdmin ? 'Admin' : 'User';
  return <Badge variant={variant}>{label}</Badge>;
}

// 简化：prop drilling 通过中间组件
// Before — 考虑 context 或 composition 是否能更好解决。
// 这是判断题——标记它，不要自动重构。
```

## Common Rationalizations

| 常见借口 | 真相 |
|---|---|
| "能工作，不用动它" | 能工作但难读的代码出问题时会难修。现在简化，每次未来变更都省时间。 |
| "更少的行永远更简单" | 1 行的嵌套三元不比 5 行的 if/else 简单。简单是关于理解速度，不是行数。 |
| "顺手把这个无关的代码也简化了" | 无范围简化产生噪音 diff，并带来未打算修改的代码的回归风险。保持专注。 |
| "类型让它自文档化了" | 类型记录结构，不记录意图。带命名良好的函数比类型签名更好地解释*为什么*。 |
| "这个抽象以后可能有用" | 不要保留投机性抽象。如果现在没用到，就是没有价值的复杂度。用到时再加。 |
| "原作者一定有原因" | 也许。检查 git blame——应用 Chesterton's Fence。但累积的复杂度往往没有原因；只是压力下迭代的残留。 |
| "加特性时顺手重构了" | 把重构与特性工作分开。混合变更更难审查、回滚和在历史中理解。 |

## Red Flags

- 简化需要修改测试才能通过（可能改变了行为）
- "简化"后的代码比原始版本更长更难追踪
- 把命名改成自己的偏好而非项目惯例
- 因为"让代码更干净"移除了错误处理
- 简化还不完全理解的代码
- 把多个简化打包成一个大、难审查的 commit
- 在当前任务范围外重构代码而未要求
- 简化过程中引入了与代码库不一致的新模式

## Verification Checklist

- [ ] 所有现有测试通过且无需修改
- [ ] 构建成功，无新警告
- [ ] Linter / formatter 通过（无风格回归）
- [ ] 每个简化都是可审查的增量变更
- [ ] diff 干净——无无关变更混入
- [ ] 简化后代码遵循项目惯例（对照 CLAUDE.md 或等效文件检查）
- [ ] 未移除或削弱错误处理
- [ ] 未留下死代码（未使用的 imports、不可达分支）
- [ ] 队友或审查者会将此变更批准为净改进

---

**最后更新**: 2026-07-09
**参考来源**: https://github.com/addyosmani/agent-skills