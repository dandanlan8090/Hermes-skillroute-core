# 2026-07-10: vdb Profile Path Resolution

## 问题

`vdb/indexer.py` 的 `HERMES_HOME` 和 `SKILLS_DIR` 都写死了 `Path.home() / ".hermes"` / `~/.hermes/skills/`，无视 `$HERMES_HOME` 环境变量。profile 会话下（`hermes -p work chat`）Hermes core 设了 `HERMES_HOME=~/.hermes/profiles/work/`，但 indexer 完全忽略，始终扫 `~/.hermes/skills/`，而实际技能在 `$HERMES_HOME/skills` 即 `~/.hermes/profiles/work/skills/`。

## 解法

`indexer.py` 新增 `_get_hermes_home()` 函数:

```python
def _get_hermes_home() -> Path:
    val = os.environ.get("HERMES_HOME", "").strip()
    if val:
        return Path(val).expanduser()
    return Path.home() / ".hermes"
```

路径优先级：

|优先级|来源|示例|
|------|----|------|
|1|`HERMES_SKILL_DIR` 环境变量|临时覆盖，最高优先级|
|2|`HERMES_HOME` 环境变量|profile 会话自动设|
|3|默认 `~/.hermes`|无环境变量时的回退|

`VDB_DIR` 始终固定在 `~/.hermes/vdb/`（Chroma 全局共享）。

## 配套改动

|文件|改动|
|----|----|
|`vdb/indexer.py`|`_get_hermes_home()` 替换硬编码；`VDB_DIR` 独立于 `HERMES_HOME`|
|`install.sh`|`--profile` 时导出 `HERMES_SKILL_DIR`（临时），移除旧的 `active_profile` 写入|
|`scripts/init-vdb.sh`|新增 `--profile` 参数，设 `HERMES_SKILL_DIR` 后重建索引|
|`README.md`|profile 说明从"方案B三选一"改为"$HERMES_HOME 自动跟随"|
|`SOUL.md`|profile 注意段落同步更新|

## 历史纠正

本轮会话中第一步错误的解法是写入 `~/.hermes/active_profile` 持久标记文件，被用户纠正：
用户原话"不是验证有，无的区别，而是用户处于 default 还是 profile"。

**教训：** 不要发明新的持久化状态。profile 的上下文信息已通过 `$HERMES_HOME` 环境变量传递（Hermes core 的 profile wrapper 自动设），读取环境变量比读写文件更简单、更可靠。

## 验证矩阵

|场景|期望 SKILLS_DIR|测试结果|
|----|----------------|--------|
|无环境变量，无 active_profile|`~/.hermes/skills/`|PASS|
|`HERMES_HOME=~/.hermes/profiles/work/` + 目录存在|`~/.hermes/profiles/work/skills/`|PASS|
|`HERMES_SKILL_DIR=/tmp/custom-skills`|`/tmp/custom-skills`|PASS|

## 后续维护

- 新增 profile 支持 CLI 时无需改 `_get_hermes_home()`，Hermes core 的 profile wrapper 已负责设 `HERMES_HOME`
- 如果未来 vdb 也要 per-profile 存储，才需要改 `VDB_DIR`，当前无需
