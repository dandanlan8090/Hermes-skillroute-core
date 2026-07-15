# Troubleshooting

## vdb 检索相关问题

### 症状：检索无结果 / 结果质量差
**原因**：索引过期或从未构建。
**修复**：
```bash
cd ~/.hermes/vdb
./init-vdb.sh          # 重建 .venv + 索引
# 或仅重建索引
.venv/bin/python -c "from indexer import build_index; build_index(force=True)"
```

### 症状：新增 skill 后检索不到
**原因**：索引未增量更新。
**修复**：重跑 `build_index(force=True)`，或等 `vdb-autoload.py` 自动检测过期。

### 症状：中文 query 召回率低
**原因**：sparse 词表缺中文 trigger。
**修复**：给 skill 的 frontmatter 加 `metadata.hermes.tags.trigger`（≥7 个中文词），再重建索引。

## MCP 服务器接入

### 症状：MCP 工具在会话中不可见
**原因**：改 `config.yaml` 后需重载。
**修复**：`/reset` 或开新会话。老会话会报 "No MCP tools available"。

### 症状：`hermes config set` 把 args/env 存成字符串
**原因**：`hermes config set` 对嵌套字典/list 支持不佳。
**修复**：用 `python` 直接改 `config.yaml` 为原生 list/dict，再 `hermes mcp test <name>`。

### 症状：MCP 服务器变"摆设"
**原因**：只放 `mcp.json` 独立配置，未接入 Hermes 原生 `config.yaml mcp_servers`。
**修复**：在 `config.yaml mcp_servers` 注册（command/args/env），`hermes mcp list` 应能看到，再 `hermes mcp test`。

## 安装问题

### 症状：`install.sh` 静默退出、零文件复制
**原因**：`set -e` 下非致命命令失败即全退；或布尔变量误用（`if $DRY` 把 "false" 当命令执行）。
**修复**：用真实 profile 测试（`--profile installtest`），不用 `HOME=/tmp/xxx` 模拟；脚本内部用 `if [ "$DRY" = true ]`。

### 症状：路径解析错误（cannot stat '/tmp/.env.example'）
**原因**：`REPO_DIR` 依赖调用时 cwd。
**修复**：脚本用 `SCRIPT_PATH="$(readlink -f "$0")"` 解析绝对路径。

## 门禁误触发

### 症状：业务 query 注入数千 token 的重型文档 skill
**原因**：未登记门禁。
**修复**：在 `vdb/routing.py` 的 `STATIC_GATED_SKILLS` 加一行，或在 skill frontmatter 声明 `metadata.hermes.gate.enabled: true`。门禁词须是业务 query 不会出现的专名（如 `SOUL.md`/`vdb`/`铁律`），禁用裸词 `hermes`。
