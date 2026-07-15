---
name: hermes-shipping-verification
description: Hermes 发布验证：在部署到生产前执行完整质量门控和回滚计划。Use when deploying to production, preparing
  a release, setting up monitoring, planning staged rollout, or when a rollback strategy
  is needed. 禁用：开发环境内部测试、纯特性开发阶段。
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
      - 发布
      - 部署
      - 部署服务
      - 上线
      - 生产环境
      - deploy
      - ship
      - release
      - 回滚
      - rollback
      - staged rollout
      - feature flag
      - monitoring
      - pre-launch
      disable:
      - 开发环境
      - 本地测试
      - staging 测试
      - 纯功能开发
      - 未要求发布
    skill_type: workflow
    priority: high
    related_skills:
    - hermes-oracle-mode
    - code-review-and-quality
    - security-and-hardening
    - test-driven-development
prerequisites:
  commands:
  - terminal
  - delegate_task
---
# Hermes Shipping Verification（Hermes 发布验证）

## Overview

安全发布，不只是部署。目标是：部署时已配套监控、回滚方案就绪、对何为成功有清晰认知。每次发布必须可逆、可观测、增量进行。

**Hermes 主脑模式适配**：此 skill 在主脑模式下作为最终质量门控运行。使用 `delegate_task` 并行派发验证子任务，而非原版 `/ship` 的 Claude Code persona fan-out。验证结果带回主会话做 GO / NO-GO 判定。

## When to Use

- 首次将特性部署到生产
- 向用户发布重大变更
- 迁移数据或基础设施
- 开启 beta 或 early access
- 任何有风险的部署（所有部署都有风险）

**When NOT to use**：
- 开发环境内部测试
- staging 环境验证
- 纯功能开发阶段
- 用户明确说"只是内部测试，不用检查"

## 发布前质量门控（Pre-Launch Checklist）

### 代码质量

- [ ] 所有测试通过（单元、集成、e2e）
- [ ] 构建成功，无警告
- [ ] Lint 和类型检查通过
- [ ] 代码审查通过并批准
- [ ] 无应在此阶段解决的 TODO
- [ ] 生产代码中无 `console.log` 调试语句
- [ ] 错误处理覆盖预期失败模式

### 安全性

- [ ] 代码或版本控制中无 secrets
- [ ] 依赖审计无 critical 或 high 漏洞
- [ ] 所有面向用户的端点有输入验证
- [ ] 认证和授权检查到位
- [ ] 配置安全 headers（CSP、HSTS 等）
- [ ] 认证端点有速率限制
- [ ] CORS 配置为特定 origin（非 wildcard）

### 性能

- [ ] Core Web Vitals 在"Good"阈值内
- [ ] 关键路径无 N+1 查询
- [ ] 图片已优化（压缩、响应式尺寸、懒加载）
- [ ] Bundle 大小在预算内
- [ ] 数据库查询有适当索引
- [ ] 静态资源和重复查询配置了缓存

### 基础设施

- [ ] 生产环境变量已设置
- [ ] 数据库迁移已应用（或准备就绪）
- [ ] DNS 和 SSL 已配置
- [ ] CDN 已配置用于静态资源
- [ ] 日志和错误上报已配置
- [ ] 健康检查端点存在且正常响应

### 文档

- [ ] README 已更新含新的设置要求
- [ ] API 文档为最新
- [ ] 架构决策已写入 ADR
- [ ] Changelog 已更新
- [ ] 用户文档已更新（如适用）

## Herme 主脑模式验证流程

当 Hermes 以主脑模式执行发布验证时，使用以下并行验证结构：

```
主脑模式发布验证
    │
    ├── (并行) 代码质量验证
    │       └── 子任务：跑测试套件、lint、类型检查、审查 diff
    │
    ├── (并行) 安全验证
    │       └── 子任务：secret 扫描、依赖审计、输入验证检查
    │
    ├── (并行) 基础设施验证
    │       └── 子任务：环境变量、健康检查、DNS/SSL 配置
    │
    └── (主会话) 汇总 + GO/NO-GO 决策 + 回滚计划
```

**派发示例**（在主脑模式中）：

```python
delegate_task(
    goal="运行代码质量验证。执行：pytest / npm test，报告通过/失败数；npm run lint；tsc --noEmit。输出简洁状态报告。",
    context="项目位于 <path>。测试文件：<glob>。构建工具：<npm/pip/其他>。",
    toolsets=["terminal"],
    role="leaf"
)

delegate_task(
    goal="执行安全检查。1. 检查代码中是否有硬编码 secrets（grep -r 'api_key\\|password\\|token' --include='*.py' --include='*.js' <path>）；2. 运行依赖审计（npm audit / safety check）；3. 验证生产环境变量配置存在且不含敏感值。输出简洁报告。",
    context="项目位于 <path>。敏感值应从 .env 读取，不应出现在源码中。",
    toolsets=["terminal"],
    role="leaf"
)
```

## Feature Flag 策略

用 feature flag 解耦部署与发布：

```
Feature flag 生命周期：
1. DEPLOY with flag OFF     → 代码在生产但未激活
2. ENABLE for team/beta     → 在生产环境做内部测试
3. GRADUAL ROLLOUT          → 5% → 25% → 50% → 100% 用户
4. MONITOR at each stage    → 监控错误率、性能、用户反馈
5. CLEAN UP                 → 完全推广后移除 flag 和死代码路径
```

**规则**：
- 每个 feature flag 有 owner 和到期日期
- 完全推广后 2 周内清理 flag
- 不要嵌套 feature flag（产生指数级组合）
- 在 CI 中测试两种 flag 状态（on 和 off）

## 分阶段发布

### 发布序列

```
1. DEPLOY to staging
   └── 全量测试套件在 staging 环境运行
   └── 关键流程手动冒烟测试

2. DEPLOY to production (feature flag OFF)
   └── 验证部署成功（健康检查）
   └── 检查错误监控（无新错误）

3. ENABLE for team (flag ON for 内部用户)
   └── 团队在生产环境使用特性
   └── 24 小时监控窗口

4. CANARY rollout (flag ON for 5% 用户)
   └── 监控错误率、延迟、用户行为
   └── 对比指标：canary vs. baseline
   └── 24-48 小时监控窗口
   └── 仅在所有阈值通过后才推进（见下表）

5. GRADUAL increase (25% → 50% → 100%)
   └── 每步相同监控
   └── 任意时刻可回滚到前一百分比

6. FULL rollout (flag ON for 所有用户)
   └── 监控 1 周
   └── 清理 feature flag
```

### 发布判定阈值

| 指标 | 推进（绿色） | 暂停调查（黄色） | 回滚（红色） |
|------|------------|----------------|------------|
| 错误率 | 在基线 10% 以内 | 基线上 10-100% | >基线 2 倍 |
| P95 延迟 | 在基线 20% 以内 | 基线上 20-50% | >基线 50% |
| 业务指标 | 持平或正向 | 下降 <5%（可能是噪声） | 下降 >5% |

### 立即回滚条件

- 错误率增长超过基线 2 倍
- P95 延迟增长超过基线 50%
- 用户报告问题激增
- 检测到数据完整性问题
- 发现安全漏洞

## 监控和可观测性

### 监控内容

```
应用指标：
├── 错误率（总计和按端点）
├── 响应时间（p50, p95, p99）
├── 请求量
├── 活跃用户
└── 关键业务指标（转化、参与度）

基础设施指标：
├── CPU 和内存利用率
├── 数据库连接池使用
├── 磁盘空间
├── 网络延迟
└── 队列深度（如适用）

客户端指标：
├── Core Web Vitals（LCP, INP, CLS）
├── JavaScript 错误
└── API 错误率
```

### 发布后第一个小时的验证

```
1. 健康检查端点返回 200
2. 错误监控仪表板（无新错误类型）
3. 延迟仪表板（无回归）
4. 手动测试关键用户流程
5. 验证日志正常流入且可读
6. 确认回滚机制可用（dry run 如可能）
```

## 回滚策略

每种部署前必须有回滚计划：

```markdown
## 回滚计划 for [特性/发布]

### 触发条件
- 错误率 > 基线 2 倍
- P95 延迟 > [X]ms
- 用户报告 [具体问题]

### 回滚步骤
1. 禁用 feature flag（如适用）
   或
1. 部署前一版本：`git revert <commit> && git push`
2. 验证回滚：健康检查、错误监控
3. 通知：告知团队回滚

### 数据库考虑
- 迁移 [X] 有回滚：`npx prisma migrate rollback`
- 新特性插入的数据：[保留/清理]

### 回滚时间
- Feature flag：< 1 分钟
- 重新部署前一版本：< 5 分钟
- 数据库回滚：< 15 分钟
```

## Common Rationalizations

| 常见借口 | 真相 |
|---|---|
| "staging 能工作生产也能" | 生产有不同的数据、流量模式和边界情况。部署后要监控。 |
| "这个不需要 feature flag" | 每个特性都能从 kill switch 受益。即使"简单"变更也可能出问题。 |
| "监控是额外开销" | 没有监控意味着从用户投诉而非仪表板发现问题。 |
| "以后再加监控" | 发布前加。看不到的东西无法 debug。 |
| "回滚是承认失败" | 回滚是负责任的工程。发布坏特性才是失败。 |

## Red Flags

- 部署时没有回滚计划
- 生产没有监控或错误上报
- 大爆炸发布（一次性全量，无 staging）
- Feature flag 无到期日或 owner
- 发布后第一个小时无人监控
- 生产环境配置靠记忆而非代码
- "周五下午了，发版吧"

## Hermes 主脑模式 GO / NO-GO 判定

收集所有验证子任务结果后，主脑模式输出：

```markdown
## 发布判定：GO | NO-GO

### 阻塞项（发布前必须修复）
- [来源：具体问题 + 位置]

### 推荐修复（发布前应修复）
- [来源：具体问题 + 位置]

### 已确认风险（已知晓仍发布）
- [风险 + 缓解措施]

### 回滚计划
- 触发条件：[什么信号会触发回滚]
- 回滚步骤：[精确步骤]
- 恢复时间目标：[目标]

### 协助验证的子 Agent
- [子任务 1]
- [子任务 2]
- [子任务 3]
```

## Verification Checklist

**发布前**：
- [ ] Pre-launch checklist 完成（所有章节绿色）
- [ ] Feature flag 已配置（如适用）
- [ ] 回滚计划已记录
- [ ] 监控仪表板已设置
- [ ] 团队已通知发布

**发布后**：
- [ ] 健康检查返回 200
- [ ] 错误率正常
- [ ] 延迟正常
- [ ] 关键用户流程正常
- [ ] 日志正常流入
- [ ] 回滚已测试或确认就绪

---

**最后更新**: 2026-07-09
**参考来源**: https://github.com/addyosmani/agent-skills（重写适配 Hermes 主脑模式）