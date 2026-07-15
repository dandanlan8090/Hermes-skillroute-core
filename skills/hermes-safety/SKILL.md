---
name: hermes-safety
description: '安全约束规范：禁止生成挖矿/破解/内网扫描/提权入侵类脚本。
  密钥/密码/API仅提供模板提醒用户替换。开源发布前必须脱敏。
  禁用：正常系统管理、安全审计、授权渗透测试。'
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
      - 安全
      - 密钥配置
      - 密码
      - API密钥
      - 挖矿
      - 破解
      - 入侵
      - 内网扫描
      - 提权
      - 脱敏
      - 开源发布
      - GitHub推送
      - 敏感信息
      disable:
      - 授权安全审计
      - 正常系统管理
      - 标准渗透测试(授权)
    skill_type: methodology
    priority: highest
---
# 安全约束规范

## 绝对禁止生成

- 挖矿脚本
- 破解/盗版工具
- 内网扫描器
- 提权入侵工具
- 恶意软件/病毒
- 钓鱼脚本

## 敏感信息处理

### 密钥/密码/API 配置

- 仅提供模板格式
- 用 `<your_api_key>`、`<password>`、`<token>` 占位
- 明确提醒用户自行替换

### 数据库连接

- 仅提供连接字符串格式
- 不写入真实凭据
- 提醒使用环境变量或 secret manager

## 开源发布规则

- 所有发布到开源社区或分享的文件/资料必须脱敏
- 删除所有真实 IP、域名、密钥、密码、token
- 删除内网路径和用户名
- 删除业务敏感信息
- **真实运行凭据不得进入 repo**：代理节点密码/UUID、SS/Trojan/VLESS URI、mihomo/Xray 完整 config、证书私钥/指纹、SSH 端口等一律只保留在运行环境，公开材料只能用占位符
- **泄露补救顺序**：一旦真实凭据进入 commit / PR / release / repo，先 rotate secret，再清理 git history / release / artifact；delete repo 或 archive repo 不能替代 rotate，因为 clone、fork、cache 和版本历史可能已扩散

## GitHub 推送前检查

每次推送前：

1. 检查是否包含真实凭据
2. 检查是否包含内网信息
3. 检查是否包含用户个人信息
4. 检查是否包含业务敏感数据
