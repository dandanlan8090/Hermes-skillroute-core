# 辅助任务(auxiliary)推理 token 泄漏与抑制

## 现象（实测 2026-07-14）
后台自动任务——最典型是会话标题生成 `title_generation`——走推理模型（实测
`openrouter/tencent/hy3:free`）时，给一个 7 词标题偷偷想了 **1,154 个 reasoning token**
（Output 1,161，Reasoning 1,154）。该调用独立于主会话、**不命中主会话前缀缓存**
（In 95 / Cache Read 0，无 38k 系统前缀），是纯额外开销，且会进入下一轮输入滚雪球。

## 根因（源码实测，非推测）
- 主会话的推理档位由 `agent.reasoning_effort`（config.yaml，默认 `high`）控制，
  路径是 `gateway/run.py::_load_reasoning_config()` → **只作用在主会话主模型**
  （如 你的模型名 / 你配的 custom provider）。
- 所有辅助任务统一走 `agent/auxiliary_client.py::call_llm(task=...)`，
  与 `_load_reasoning_config` 是**两条独立通道**，互不读取。
- `agent/title_generator.py::generate_title()` 只传 `max_tokens=500, temperature=0.3`，
  **不传 reasoning_effort、不读 `agent.reasoning_effort`**。
- `call_llm` 组装请求时调 `_get_task_extra_body(task)`（读 `auxiliary.<task>.extra_body`）；
  没配 `auxiliary.title_generation` → 返回 `{}` → 不注入任何 reasoning 抑制。
- 推理模型在 OpenRouter 上默认开 thinking；`reasoning_effort` 字段不传 → 模型侧默认档生效
  → 整段隐形推理。源码里那段 `strip_think_blocks` 就是在擦推理模型漏进标题的 `<think>` 残块。

## 关键结论
**调低 `agent.reasoning_effort` 治不了辅助任务的推理浪费**（两条通道独立，
且会拉低主会话思考质量）。正确做法是针对具体辅助任务在 `auxiliary.<task>` 里抑制推理。

## 修复配方（config.yaml）

### A. 关掉标题任务的推理（最精准，只影响标题）
```yaml
auxiliary:
  title_generation:
    extra_body:
      reasoning:
        enabled: false   # OpenRouter 原生关闭思考字段（经源码确认的形状，本次实测生效）
```
边际成本从 ~1.2k 掉到几十 token；不影响主会话。
> 字段形状实测确认：`agent/auxiliary_client.py` line 956-978 的 Codex 分支读 `extra_body.reasoning`
> 并构造 `{"effort": effort, "summary": "auto"}` 字典；`enabled: false` 分支跳过设置 = 关闭。
> 故 `reasoning: {enabled: false}` 是匹配源码的写法。**本次实测即采此写法并验证 load_config 读到**。
> 若某模型不认嵌套 `reasoning`，退路是 `reasoning_effort: none`（OpenAI 兼容形状）——但优先用前者。

### B. 给标题换非推理轻量模型（根治 + 更稳）
```yaml
auxiliary:
  title_generation:
    provider: openrouter
    model: <非推理 instruct 模型，如 openai/gpt-4o-mini>
```
理由：推理模型偶尔把 `<think>` 残块漏进标题（代码里 `strip_think_blocks` 才在擦屁股）；
换 instruct 模型从根上避免，标题质量也更可控。

### 通用化
`auxiliary.<task>.extra_body` 对所有辅助任务生效：
`vision` / `compression` / `web_extract` / `session_search` / `skills_hub` / `mcp` /
`title_generation`。哪个任务误用推理模型，就给哪个加 `reasoning_effort: none`。

## 源码定位速查
- `agent/title_generator.py` — 标题生成调用点（无 reasoning 注入）
- `agent/auxiliary_client.py` —
  `_get_task_extra_body()` / `_get_auxiliary_task_config()` / `_resolve_task_provider_model()` / `call_llm()`
- `gateway/run.py::_load_reasoning_config()` — 主会话 reasoning 档位（仅主模型）
- `config.yaml` 的 `agent.reasoning_effort` 与 `auxiliary.*` 两段**互不继承**

## 验证
改完发一条 `hi` → 观察后台标题生成的 Usage：Reasoning 应从 ~1,154 降到接近 0，
Output 从 ~1,161 降到几十。若仍高，确认 `auxiliary.title_generation.extra_body` 已落盘
且任务解析到了该段（`_get_auxiliary_task_config` 读 `config.yaml` 的 `auxiliary.title_generation`）。
