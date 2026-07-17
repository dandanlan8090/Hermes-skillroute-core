# names-only 死配置诊断（2026-07-17 实测）

## 一句话
`config.yaml` 的 `agent.skills_index_mode: names-only` 当前是**死配置**——写了但不被任何代码消费。本文件是可复现的诊断与测量配方。

## 可复现诊断三步
```bash
# 1) 死配置铁证：全代码树搜不到消费点
cd ~/.hermes/hermes-agent
grep -rn "skills_index_mode" . --include=*.py   # 期望 0 命中

# 2) 实测当前注入形态（full vs names-only）
venv/bin/python -c "
from agent.prompt_builder import build_skills_system_prompt
s = build_skills_system_prompt()
print('bytes', len(s.encode()))
print('names-only 降级标记?', 'names only' in s.lower())
b = [l for l in s.splitlines() if l.strip().startswith('- ')]
print('bullet 数', len(b))
"
# full 模式特征：~17.4KB，105 个 bullet 全带 description，无 names-only 标记
# names-only 模式特征：每个类只剩一行 'category [names only]: name1, name2'，描述被砍

# 3) config 残留检查
grep -n "skills_index_mode" ~/.hermes/config.yaml   # 第 71 行附近，存在但无效
```

## 根因（实证链）
- 当初实现 patch 了 `agent/system_prompt.py`（加 `skills_index_mode` 读取）+ `agent/prompt_builder.py`（加 `index_mode` 参数 + `_build_routing_index()`）。
- 2026-07-17 `hermes update` 拉官方 commit（文件 mtime 01:01，git status 干净）→ 核心文件还原 → 消费逻辑消失。
- **残留的 names-only 是同名的另一功能**：`agent.coding_context: focus` 的 posture-driven category demotion（system_prompt.py:301-304、prompt_builder.py:1634-1636）。grep 'names-only' 会命中这 3 处，但**与 `skills_index_mode` 无关**，是误导源。
- yaml 对未知字段不报错、保留原值 → `agent.skills_index_mode` 长期静默无效。

## 关键测量事实（本会话实测，非估算）
- 单次注入 full 模式 available_skills 区块：**17,480 bytes**，105 条技能 bullet。
- 真实单次会话总注入 ≈ **44–45 KB ≈ 1.5 万 tok**（框架三件套 16.2K + available_skills 15.9K + 工具 schema ~11K + 头部 1.5K）。旧公式 ~6,100t 漏算两大头。
- 路由表（SOUL.md）仅覆盖 **28** 个唯一技能；available_skills 注入 **105** 个；其中 **71** 个长尾技能也在 vdb（103 个）索引内 → 关 available_skills 不影响 vdb 召回；真正只靠 available_skills/skills_list 兜底的仅 **8** 个未进 vdb 的技能。

## vdb 召回实测（关 available_skills 等效 = 仅 vdb+路由表+skills_list）
- 15 个代表性 query，top-1 精确命中 **12/15 = 80%**。
- 3 个未命中均为近义技能（PR 影响分析→github、生成图片→gif-search、GitHub 推送→github），非真失败。
- 结论：关 available_skills 对核心技能无影响；vdb 漏召的 20% 边界 case 失去"黄页式"二次校正机会。

## available_skills 的其他实测性质
- **静态区块**：`build_skills_system_prompt()` 签名 `(available_tools, available_toolsets, compact_categories)`，不读 messages/历史/对话长度。
- **会话压缩不稀释它**：context_compressor.py 全程无 `build_skills_system_prompt`/`available_skills` 引用；system prompt 属 byte-stable（保 prompt 缓存），设计上禁止随对话漂移。
- vdb 不可用时回退路径是 `skills_list` 工具（vdb-autoload.py:139），非 available_skills 自动补位。

## 当前可用的真降级开关
`hermes config set agent.coding_context focus`：非 coding 类 → names-only，实测仅 **-792B / -5.4%**，收益极低，但官方内置、不受 update 影响。
