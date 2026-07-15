---
name: hermes-fault-troubleshooting
description: '故障处理流程：定位原因→修复脚本→校验方案。按以下顺序输出：定位原因、修复脚本、校验方案。
  Use for system failures, service outages, error reports, unexpected behavior, or any operational issue.
  禁用：代码bug调试(见 debugging-patterns)、性能优化(非故障)。'
version: 1.0.0
author: Hermes
license: MIT
platforms:
- linux
- macos
- windows
metadata:
  hermes:
    tags:
      trigger:
      - 故障
      - 报错
      - 异常
      - 服务挂了
      - 出问题了
      - troubleshooting
      - 系统异常
      - 无法访问
      - error
      - crashed
      - 不工作
      - 坏了
      disable:
      - 代码bug调试
      - 性能优化
      - 排查报错
      - 服务启动不了
      - 新功能开发
    skill_type: methodology
    priority: high
---
# 故障处理流程

## 输出顺序

用户反馈故障时，按以下顺序输出：

1. **定位原因** — 先排查根因，不猜
2. **修复脚本** — 完整一键修复命令
3. **校验方案** — 如何验证修复成功

## Systematic Debugging

### Iron Law
不查根因禁止修。症状修复 = 失败。

### 四阶段
1. Root Cause：读错 → 复现 → 看最近变更 → 多组件逐层插桩 → 数据流反向追溯
2. Pattern Analysis：找 working example，对比差异，读完参考实现再动手
3. Hypothesis + Test：单一假设、最小改动、一个变量
4. Implementation：先写 failing test / failing 复现脚本 → 修 → 验证回归

### 3 次失败停止
同一问题累计 3 次修复失败 → 停止，问架构，不继续打补丁。

### 一行复现
bash -c '原命令' 2>&1 | tee /tmp/repro.log
看到原始报错 → 留着不删，作为 disclosed symptom。
