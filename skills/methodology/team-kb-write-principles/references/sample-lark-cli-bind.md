# 示范样本：lark-cli 飞书认证绑定

> 本条目是 `知识条目模板` 的填充示范，展示如何把一条真实知识写成合规团队 KB 条目。

---

## 条目头部（frontmatter）

```yaml
---
id: kb-lark-cli-feishu-bind
title: lark-cli 飞书认证绑定（user 身份）
category: 飞书集成
author: Hermes（AI Agent）  # 初版 2026-07-11
version: 1.0.0
verified_on: 2026-07-11
expires_when: 飞书或 lark-cli 升级改版、认证流程变更、端点划分调整
confidence: verified        # 实测确认
scope:
  source_device: x86 [HOSTNAME] (Ubuntu 26.04) + 局域网飞书账号 dandanlan
  env: 飞书国内端点 (feishu brand)；Node 运行环境（非 Go）
trigger_tags:
  - 飞书命令行绑定
  - lark-cli 登录
  - 飞书认证怎么配
  - lark-cli user 身份
  - 飞书机器人配置
  - 知识库访问认证
  - cli 绑定飞书账号
disable_tags:
  - 飞书国际版 lark 端点
  - lark-cli 旧版本初始化
---
```

## 正文

### 第一性原理
- **命令名是 `lark-cli`，不是 `larksuite`**：安装包名 `@larksuite/cli`，二进制名 `lark-cli`。误用 `larksuite` 会 command not found。
- **绑定须走 `config bind`，不能用 `config init`**：`init` 会被拒（提示会创建并行 app），必须用 `config bind --source hermes --identity user-default`。
- **brand 区分国内外**：国内飞书 = feishu，国际 = lark，端点与回调不同。本条目仅限 feishu。

### 工作流 / 操作步骤
1. 安装（需 Node，不需 Go）：`npx @larksuite/cli@latest install`
2. 绑定 Hermes 上下文 + user 登录：`lark-cli config bind --source hermes --identity user-default`
3. 查看认证状态：`lark-cli auth status`（确认 `identity: user`、`brand: feishu`）
4. 完成标准：status 显示 user `available: true` 且 `brand: feishu`。

### 规则 / 约束
- 禁用 `config init`（会创建并行 app 被拒）。
- 知识库/文档操作默认 `--as user`（bot 身份列出的是应用空间，非用户个人/团队空间）。
- 凭证存 Hermes 凭据文件：`FEISHU_APP_ID`(cli_ 开头) / `FEISHU_APP_SECRET` / `FEISHU_DOMAIN`。

### 失败模式
| tell | fix |
|------|-----|
| `larksuite: command not found` | 改用 `lark-cli` |
| `config init` 报"会创建并行 app" | 改 `config bind --source hermes` |
| 列知识库只看到 bot 空间 | 命令加 `--as user` |

## 时效与真实性护栏
- verified_on=2026-07-11，失效条件：飞书/lark-cli 升级改版、端点划分调整。
- 来源：实测 `lark-cli auth status` 输出（appId `cli_aad883552478dcc7`、brand feishu、user openId `ou_f3...`）。
- 对易变事实（品牌端点、权限范围）采取行动前先重验 `auth status`。

## 变更记录表
| 日期 | 修改人 | 版本 | 变更说明 |
|------|--------|------|----------|
| 2026-07-11 | Hermes（AI Agent） | 1.0.0 | 初版：基于实测 auth status 落地 |

## 对照模板"反例"
- ❌ 泛化写法："lark-cli 用 config bind 即可"（无 scope、无时效、无来源）。
- ✅ 本条目：带 feishu 端点 scope + verified_on + 实测来源，正是模板要求的合规形态。

---

落地日期：2026-07-11 ｜ 作者：Hermes（AI Agent）｜ 示范遵循 `team-kb-write-principles` 四闸门与 scope 纪律。
