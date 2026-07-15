---
name: hermes-code-output
description: '代码与文档输出规范：完整代码块一键复制、结论前置文档格式、输出字面量铁律（禁止转义字面量）。
  Use when writing scripts, creating documentation, outputting code examples, or formatting terminal output.
  禁用：纯文字描述、无需代码的问答。'
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
      - 写脚本
      - 代码输出
      - 文档格式
      - 代码块
      - 输出规范
      - 脚本格式
      - 代码风格
      - 文档标准
      - 输出格式
      - 编写代码
      disable:
      - 纯文字描述
      - 无需代码的问答
      - 已有现成代码
    skill_type: methodology
    priority: high
---
# 代码与文档输出规范

## 代码输出

- 所有 Shell/Python/PowerShell/Docker 配置输出**完整整块代码块**
- 支持一键全选复制
- 禁止拆分零散小段代码
- 禁止省略关键行或用 "..." 代替
- 脚本自带注释、适配系统环境

## 文档输出

- 优先整合为单一完整 Markdown 文件交付
- 拒绝拆分多个碎片化文档
- 结构：结论前置，操作步骤居中，补充说明后置
- 精简标题层级，不堆砌空段落

## 输出字面量铁律

- 严禁在正文或代码块中使用转义字面量（\\n、\\r、\\t、\\x）和 HTML 实体（&#x20;、&nbsp;）
- 所有空白字符必须使用键盘物理按键直接输入
- 仅在专门讲解编程转义原理时允许使用双反斜杠（\\n）作为演示

## Think Before Coding

写代码前先阐明假设，若有多种解读需列出并暂停确认，不得隐藏困惑。

## Simplicity First

用最少代码解决问题，不做未要求的功能。若代码超 200 行可精简至 50 行，必须重写。

## Surgical Changes

只修改必须改动的部分，禁止顺手"改进"相邻代码。保持与现有风格一致。
