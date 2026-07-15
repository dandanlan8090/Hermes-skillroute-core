---
name: hermes-verification-rules
description: '验证铁律：任何"完成/搞定/成功/修复"结论前必须执行 IDENTIFY→RUN→READ→VERIFY 四步验证流程。
  Use when declaring a task complete, confirming a fix, verifying a deployment, announcing test results,
  or reporting any successful operation.
  禁用：纯文本回答、一次性只读查询、用户明确说"不用验证"。'
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
      - 验证
      - 检查
      - 确认
      - 部署完了
      - 搞定
      - 完成
      - 成功
      - 修复
      - verify
      - confirm
      - test result
      - 再跑一下
      - 验收
      disable:
      - 纯文本回答
      - 只读查询
      - 用户明确说不用验证
    skill_type: methodology
    priority: highest
---
# 验证铁律

## 核心四步

任何"完成/搞定/成功/修复"等肯定结论出现之前：

### 1. IDENTIFY
确定什么命令可以证明该操作成功。

### 2. RUN
完整运行验证命令（不是 echo "should pass"）。

### 3. READ
完整读输出，检查 exit code，统计失败数。

### 4. VERIFY
输出是否真的支持结论？确认后再宣布。

## 场景验证对照

| 声明 | 验证方法 |
|------|---------|
| "测试通过" | pytest <file>::<test> --tb=short，0 failures |
| "服务起来" | systemctl status <svc> + curl /healthz |
| "配置生效" | grep / ss / ls 三选一实际值 |
| "已修复" | 用原报错命令复跑，看不到原报错才算 |
| "已 commit" | git log --oneline -1 |
| "agent 报告完成" | 实际跑一遍，不要信 agent 自报 |

## 禁止措辞

不能说：应该、似乎、看起来、大概、让它跑跑看、我猜 OK
不能说：完美、搞定（完成时）、太棒了、一气呵成
