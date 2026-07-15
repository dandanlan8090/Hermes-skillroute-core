# 2026-07-10 用户对 hermes-base-config 的 8 点评分析

用户在此次对话中提供了对整个仓库的外部审查反馈，要点归档如下。

## 设计原则（适用于下次自审）

1. **项目定位**：个人维护的 Hermes Agent 通用配置模板仓。一键 `bash install.sh` 铺到 `~/.hermes/`。
   - 三文件保护（SOUL/AGENTS/USER）存量跳过新装全量
   - 技能目录存量只补不删

2. **vdb 设计最核心**：Chroma + SiliconFlow BGE-M3 云端稠密 + sparse 纯本地无 torch。
   - leading word 2x boost + prose 模板 + 短 query 包装 → Top-1 命中 60%→100%

3. **与官方关系**：
   - SOUL.md 的 `Hermes` 是 fork 命名（已清除）
   - AGENTS.md "禁用 available_skills" 是对抗性设计（已标记文档）
   - vdb 是外部叠加不属于核心
   - NEW_SKILL_TEMPLATE.md 是仓库自定的规范不是上游规范

4. **实测风险点 A**：install.sh 行为与 README 描述一致（补不删 + 覆盖 vdb ✓）

5. **实测风险点 B**：SKILLS_DIR 硬编码对 profile 用户不友好 → **已修复**（`$HERMES_SKILL_DIR` 环境变量）

6. **实测风险点 C**：`build_index(force=True)` 与 SOUL.md §8 持久化边界一致 ✓

7. **实测风险点 D**：vdb-autoload 是半成品，install.sh 未调用 → **已修复**（install.sh Step 7 + autoload v2 with --force）

8. **实测风险点 E**：脱敏干净 ✓

## 2026-07-10 补充：Profile 安全修复 + README 同步

**经用户指出，Hermes 对自身所处的 profile 环境感知弱**，在非 default profile 下运行 install.sh 会装错目录。

修复（已合入）：
- `install.sh` 新增 `--profile <name>` 参数，安装到 `~/.hermes/profiles/<name>/`
- `install.sh` 自动检测 profile（`hermes profile list | grep ◆`），非 default 弹警告
- 自动导出 `HERMES_SKILL_DIR` 指向 profile 技能目录
- SOUL.md §1 新增 profile 路径说明
- README 顶部新增 profile 安全警告
- hermes-base-config-sync skill 新增 profile 安全 checklist

## 适用/不适用场景

**适用**：固化个人工作流基线、多机同步、给技能库加语义检索、plan/oracle/shipping 结构骨架
**不适用**：纯默认 Hermes 行为（本仓库强 opinionated）、不想装外部依赖、不想承担 vdb 半成品风险
