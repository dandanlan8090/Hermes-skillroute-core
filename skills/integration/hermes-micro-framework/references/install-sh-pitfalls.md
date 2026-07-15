# install.sh 致命 Bug 复现与修法（2026-07-12 实测）

本会话给 micro-framework 仓库补 install.sh 的 context 建表步骤时，发现 install.sh
在**空白 agent 直接 clone 安装**场景下静默失败（只打印到第 3 步标题就退出，不复制任何文件）。
在真机（~/.hermes 已存在）因走存量分支、跳过关键路径，bug 被掩盖。

## 三个真实 Bug

### Bug 1: bash 布尔变量误用（最致命）
原代码：
```bash
DRY=false
do_cp() {
    if $DRY; then          # ← BUG: 执行字符串 "false" 当命令
        echo "  [DRY] ..."
        return
    fi
    cp -r "$src" "$dst"    # 永远到不了
}
```
`if $DRY` 把 `"false"` 当命令执行，`false` 返回 0（成功）→ 永远进 then 分支 return →
零复制。同理 `if $IS_NEW` / `if $FORCE` 把 `"true"` 当命令执行（碰巧成功，但语义错）。

**修法**：一律用 `[ "$VAR" = true ]` 形式：
```bash
if [ "$DRY" = true ]; then ...
if [ "$IS_NEW" = true ] || [ "$FORCE" = true ]; then ...
```

### Bug 2: set -e 过脆
原 `set -euo pipefail`。Bug 1 导致 cp 实际未执行，但更早的 `count_before=$(find ...|wc -l)`
在 pipefail 下若 find 有 stderr 即非零退出 → 整个脚本终止。输出缓冲让你只看到
"第 3 步"标题，实际第 1/2 步的 cp 已失败退出。

**修法**：去掉 `-e`（保留 `set -u` 防未定义变量）；do_cp 用 `cp -rn`（不覆盖已存在）；
关键步骤尾加 `|| true`。安装脚本是非原子多步任务，不应因非致命错误全退。

### Bug 3: REPO_DIR 依赖调用时 cwd
原代码：
```bash
REPO_DIR="$(cd "$(dirname "$0")" && pwd)"
```
当 `bash install.sh`（相对路径 `$0=install.sh`）且调用前 cwd 非仓库根时，
`dirname` 得 `.`，`cd .` 得当前 cwd → REPO_DIR 错。实测报错：
`cp: cannot stat '/tmp/.env.example'`（REPO_DIR 变成了 /tmp）。

**修法**：用 absolute path 解析，不依赖 cwd：
```bash
SCRIPT_PATH="$(readlink -f "$0" 2>/dev/null || realpath "$0")"
REPO_DIR="$(cd "$(dirname "$SCRIPT_PATH")" && pwd)"
```

## 验证方法（修完后必跑）
模拟空白 agent（不碰真 ~/.hermes）：
```bash
rm -rf /tmp/test-hermes && mkdir -p /tmp/test-hermes
HOME=/tmp/test-hermes bash install.sh
# 期望: 打印 "类型: 全新安装" + 各步 ✓ + "安装完成"
# 验证产物:
find /tmp/test-hermes/.hermes/skills -name SKILL.md | wc -l   # 应 = 66
ls /tmp/test-hermes/.hermes/scripts/context-processor.py     # 应存在
ls /tmp/test-hermes/.hermes/scripts/message_tags.db          # 应已建表
```
`bash -n install.sh` 仅查语法，查不出上述运行时 bug——必须真跑空白 HOME 安装。

## 存量用户路径
原步骤 3 的存量分支用 `for cat_dir in skills/*/; do for skill_dir in cat_dir*/` 会把
`skills/foo/references/`、`skills/foo/scripts/` 当 skill 复制（路径错乱）。
改法：直接 `find skills -name SKILL.md` 取父目录，新增的才复制：
```bash
while IFS= read -r skill_md; do
    skill_dir=$(dirname "$skill_md")
    name=$(basename "$skill_dir")
    [ "$name" = "templates" ] && continue
    [ -d "$HERMES_DIR/skills/$name" ] || cp -r "$skill_dir" "$HERMES_DIR/skills/$name"
done < <(find "$REPO_DIR/skills" -name SKILL.md -not -path "*/templates/*")
```
