# vdb 检索命中率演化记录（2026-07-11）

离线 benchmark：61 条正式集（中英混合，有精确期望技能）+ 17 条 harder 集（信息密度低的自然语言 query）。
索引技能数 62（framework-loader/architecture/changelog/evolution 已归档，由超集技能 `hermes-framework` 取代）。

## 演化线（Top-1 命中率）

| 阶段 | 方法 | 61条正式集 T1 | 17条 harder T1 | 备注 |
|------|------|--------------|---------------|------|
| P0 基线 | 0.6/0.4 加权 + TF-only | 75.4% | — | 起点 |
| P1 | RRF 融合 (RRF_K=60) | 78.7% | — | 中文 +6.6pp vs 0.6/0.4 |
| P2 | + IDF 增强 (trigger TF-IDF) | 78.7% | — | 修复 dogfood/shipping/yuanbao 3 个中文 case |
| P2+ | + description 中文短语入 sparse | 82.0% | — | token 657→~1126 |
| P2+F(乘法) | + trigger ×1.05 命中加成 | 85.2% | 47.1% | 乘法对 dense 主导 case 无效 |
| P2+F(加法) | + trigger +0.010 加法加成 | 85.2% | 47.1% | 同 61集，harder 待 trigger 补全 |
| 阶段一 | trigger 补全 + disable 加强 | 93.3%* | 70.6% | *60条口径；修复 9 条 case 中 6 条 |
| 阶段二 | 全量 trigger ≥7 覆盖 | 88.3%* | 70.6% | hermes-framework disable 微调致轻微回落 |

正式集口径：早期 61 条含 1 条期望名与实际索引名不符（segment-anything→segment-anything-model 等），修正后按 60 条计。

## 关键负结果（不要再踩）

1. **desc 字段降权 trig×1.2/desc×0.8**：harder set 从 47.1% 暴跌到 35.3%。缺 trig 全依赖 desc 的 query 被压死。已回退 1.0/1.0。
2. **trigger 乘法加成 ×1.05**：对 dense_rank=1 vs dense_rank=7 的 case 完全无效（base 差 ~0.0010，乘法按比例缩放两边差距不变）。改加法 +0.010 才翻得动。
3. **+0.005 加法加成**：翻了 debug case 但引入 2 条回归（"同步配置文件"→framework、"self-optimize"→performance）。+0.010 稳定。
4. **execute_code 批量插入 YAML frontmatter trigger**：插入逻辑把 trigger 行写到了 `---` 关闭符**之后**（frontmatter 外），frontmatter 内 trigger 数没变，索引读到旧值。必须用 `patch` 工具以完整 old/new 上下文精确修改，不要用 execute_code 字符串插入改 YAML。
5. **disable 拼短语无效**："排查报错" 在 "排查一下为什么报错" 中不是连续子串 → `d in query` 不匹配 → disable 失效。disable 必须是用户 query 中真实出现的连续子串（如 "排错"）。

## 当前天花板

harder set 卡在 ~70% 是 **embedding 质量上限**：信息密度低的自然语言 query（"帮我部署一下这个服务"、"配置一下这个环境"）dense 向量偏泛化，sparse + trigger 加成翻不动 dense_rank=1 的干扰技能。进一步突破需要：
- 更好的 prose 模板 / 更强 dense 模型
- 或给干扰技能加更精确的 disable（仅当干扰技能 dense 也高时有效）

## 复跑命令

```bash
cd ~/.hermes/vdb && source .venv/bin/activate
python3 -c "from indexer import build_index; build_index(force=True)"
# 然后用 eval/benchmark_rrf.py 或 matcher.search() 逐条核对
```
