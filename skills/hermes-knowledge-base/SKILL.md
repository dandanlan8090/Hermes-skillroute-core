---
name: hermes-knowledge-base
description: '知识库整理规范：Markdown + AAAK 格式，适配 Git/rsync 同步。
  Use when organizing markdown documents, building a knowledge base, migrating notes across devices,
  or standardizing documentation format.
  禁用：代码仓库文档、项目 README、一次性笔记。'
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
      - 知识库
      - 笔记整理
      - Markdown 规范
      - AAAK
      - 文档归档
      - git同步文档
      - rsync迁移
      - 知识库格式
      - knowledge base
      - markdown整理
      disable:
      - 项目README
      - 一次性笔记
      - 代码注释
    skill_type: workflow
    priority: normal
---
# 知识库整理规范

## 核心标准

- 格式：Markdown + AAAK 规范
- 同步：适配 Git / rsync 跨设备迁移
- 结构：结论前置，操作步骤居中，补充说明后置
- 标题层级：精简，不堆砌空段落

## AAAK 格式要点

- A（Abstract）：一句话摘要
- A（Architecture）：架构/原理说明
- A（Action）：具体操作步骤
- K（Knowledge）：相关知识链接

## 文件组织

- 按主题分类目录
- 每个主题一个独立 md 文件
- 图片/附件放在同目录 assets/ 下
- 索引文件（README.md）列出所有主题

## 团队知识库设计原则（老黎 2026-07-11 指引）

仅当知识库面向多人/多设备共享时才适用本段。硬性约束：

1. **环境&时效**：每条知识带 `verified_on` 与失效条件（如「lark-cli 升级后须重验」），过期即成误导。
2. **适配性**：同一结论在不同环境（ARM 电视盒 vs x86 VM vs 飞书国内端点）可能不成立。
3. **真实性**：来源可溯、可重验，不编造「看起来对」的内容。
4. **正确性**：经实测或官方文档佐证，非脑补。

**设备专属性陷阱**：部分知识仅限特定设备/环境通用，**不可盲目泛化**。每条知识必须标注来源范围（provenance / scope），例如「仅适用于 cm211 电视盒 + 局域网」。

**勿过早过度工程化**：框架未成熟前（如 Agent 仍处于起步期），不要做离线镜像兜底、自动同步层等冗余结构。先把「标 scope + 标时效」落到实体，再谈统一。

## 读取飞书（Lark）托管的文档

知识库常托管在飞书 Wiki，读取时：

- `feishu_doc_read` 工具**仅在飞书评论上下文可用**；普通会话调用会返回 `Feishu client not available (not in a Feishu comment context)`。
- 替代方案（已验证可用）：`lark-cli docs +fetch --doc <token> --format json`，从返回 JSON 的 `data.document.content` 取正文（HTML/XML 片段）。
- 列知识库节点：`lark-cli wiki +space-list --as user` → `lark-cli wiki +node-list --space-id <id> [--parent-node-token <tok>]`。
- 注意：本机命令是 `lark-cli`（包 `@larksuite/cli`），**不是** `larksuite`；认证用 `config bind --source hermes --identity user-default`，不要用 `config init`（会被拒，说会创建并行 app）。

## 适配要求

- Git：文本文件，无二进制大文件
- rsync：路径统一，无绝对路径引用
- 跨设备：使用相对路径，不依赖特定环境变量
