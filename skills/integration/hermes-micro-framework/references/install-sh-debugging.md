# install.sh 调试实录（2026-07-12）

背景：对 `github.com/dandanlan8090/hermes-micro-framework` 的 install.sh 做"agent 直接 clone 安装"可用性验证时，发现全新安装必崩。以下是逐层定位过程，可作为同类"脚本跑到某步标题就静默退出"问题的通用排查法。

## 症状
`bash install.sh`（或 `--profile xxx`）跑到 `── 第 3 步: 技能目录 ──` 后无任何输出直接结束，exit code 1。存量用户（~/.hermes 已存在）正常，全新安装必崩。

## 排查顺序（从粗到精）

### 1. 先排除 `set -e` 干扰
`sed 's/^set -euo pipefail/set -uo pipefail/' install.sh > /tmp/t.sh` 后重跑。
- 若去掉 `-e` 后跑通 → 确认是某个非致命命令触发 `set -e` 退出。
- 本会话去掉 `-e` 后虽跑通但暴露 `cp: cannot stat '/tmp/.env.example'` → 指向 REPO_DIR 解析错误。

### 2. 打印关键变量定界
在卡住的步骤前加调试 echo：
```bash
echo "DBG REPO_DIR=$REPO_DIR skills_exists=$([ -d "$REPO_DIR/skills" ] && echo yes || echo no)"
```
- 显示 `REPO_DIR=/tmp`（应为 `/tmp/hermes-micro-framework`）→ REPO_DIR 解析 bug。

### 3. 逐行 trace
`bash -x install.sh 2>&1 | sed -n '/第 3 步/,/第 4 步/p'` 看哪一行是最后执行的。
- 发现 `count_before=$(find "$HERMES_DIR/skills" -name SKILL.md 2>/dev/null | wc -l)` 后无后续 trace → 该行在 `set -e` + `pipefail` 下因目标目录不存在、find 返回非零而退出。

### 4. 验证变量无隐藏字符
`[ "$VAR" = true ]` 不进分支但 echo 显示 `true` 时，用 xxd 确认无 `\r`：
```bash
printf "%s" "$IS_NEW" | xxd   # 正常应为 7472 7565 = "true"，无 0d(\r)
```
- 本会话变量干净，排除 CRLF。最终定位到布尔判断反模式（见下）。

## 三个真 bug（已修）

| # | 症状 | 根因 | fix |
|---|------|------|-----|
| 1 | `cannot stat '/tmp/.env.example'` | `REPO_DIR="$(cd "$(dirname "$0")" && pwd)"` 依赖 cwd；脚本被 copy 到 /tmp 或从非仓库 cwd 调用时解析错 | `readlink -f "$0"` 定位真实路径 |
| 2 | 跑到第 3 步标题即静默退出 | `count_before=$(find ... | wc -l)` 在目标不存在时 find 非零 → pipefail 下 pipeline 非零 → `set -e` 终止 | 末尾加 `|| true` |
| 3 | 布尔判断逻辑错乱（DRY/IS_NEW 不生效） | `if $IS_NEW` 把字符串 `true`/`false` 当命令执行（`false` 命令 exit 0 → 误进 then） | 统一改 `[ "$VAR" = true ]` |

## 测试纪律（重要）
**禁止 `HOME=/tmp/xxx bash install.sh` 模拟测试**——假 HOME 本身引入路径偏差，测出的问题可能是模拟造成的而非真 bug。
正确：`bash install.sh --profile installtest` → 验证完 `rm -rf ~/.hermes/profiles/installtest`。真实 HOME 结构、真实 REPO_DIR 解析，零污染。

## 真实验证结果（修复后）
```
bash install.sh --profile installtest
→ 技能总数: 0 → 66
→ ✓ scripts/context-processor.py / init-context-tables.sql
→ ✓ message_tags.db 建表
→ 安装完成，无崩溃
```
