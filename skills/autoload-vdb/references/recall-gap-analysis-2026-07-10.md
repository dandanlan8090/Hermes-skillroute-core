# Recall Gap Analysis — 2026-07-10

实测 vdb 混合检索在典型 CLI 用户 query 下的表现。数据源：`matcher.search()` on 54-index skill set, SiliconFlow BAAI/bge-m3, 0.6dense+0.4sparse.

## 测试方法

对每 query 记录：top-1 skill name、final_score、dense_score、sparse_score、实际命中 vs 预期命中。

## 覆盖场景

### 1. 报错排查
| query | top-1 | score | dense | sparse | 判定 |
|-------|-------|-------|-------|--------|------|
| "这个报错怎么修" | debugging-patterns | 0.347 | 0.506 | 0.109 | ✅ 但分数低 |
| "出错了帮我看看" | hermes-agent | 0.344 | 0.502 | 0.108 | ⚠️ 通用技能 |
| "traceback 啥意思" | openssh-server | 0.353 | 0.472 | 0.176 | ❌ 无关 |

### 2. 部署
| query | top-1 | score | dense | sparse | 判定 |
|-------|-------|-------|-------|--------|------|
| "部署一个 flask 服务" | system-admin | 0.441 | 0.475 | 0.391 | ✅ |
| "检查服务状态" | system-admin | 0.423 | 0.501 | 0.308 | ✅ |

### 3. 测试
| query | top-1 | score | dense | sparse | 判定 |
|-------|-------|-------|-------|--------|------|
| "帮我写个单元测试" | dogfood | 0.448 | 0.522 | 0.338 | ⚠️ 无 TDD skill |
| "跑一下测试看看" | codebase-memory-first | 0.397 | 0.480 | 0.276 | ❌ |

### 4. 验证/检查
| query | top-1 | score | dense | sparse | 判定 |
|-------|-------|-------|-------|--------|------|
| "验证一下部署结果" | hermes-shipping-verification | 0.410 | 0.538 | 0.218 | ✅ |
| "搞定了吗" | hermes-base-config-sync | 0.320 | 0.532 | 0.000 | ❌ 无 verification skill |
| "测试一下功能" | dogfood | 0.528 | 0.578 | 0.455 | ❌ (dogfood=QA 非 verification) |

### 5. 代码审查
| query | top-1 | score | dense | sparse | 判定 |
|-------|-------|-------|-------|--------|------|
| "code review 一下" | code-review-and-audit | 0.464 | 0.526 | 0.370 | ✅ |
| "看看代码写得对不" | codebase-memory-first | 0.434 | 0.493 | 0.345 | ⚠️ 接近但不精确 |

### 6. 计划
| query | top-1 | score | dense | sparse | 判定 |
|-------|-------|-------|-------|--------|------|
| "写个计划" | plan | 0.526 | 0.524 | 0.530 | ✅ |
| "规划一下怎么搞" | plan | 0.486 | 0.497 | 0.470 | ✅ |

### 7. 并行
| query | top-1 | score | dense | sparse | 判定 |
|-------|-------|-------|-------|--------|------|
| "同时跑两个任务" | plan | 0.392 | 0.485 | 0.256 | ❌ oracle-mode 第 3 名 |

### 8. 已知 skill 验证
| query | top-1 | score | dense | sparse | 判定 |
|-------|-------|-------|-------|--------|------|
| "oracle模式" | hermes-oracle-mode | 0.569 | 0.569 | 0.571 | ✅ 高分 |
| "主脑模式" | hermes-oracle-mode | 0.676 | 0.678 | 0.676 | ✅ 最高分 |
| "todo进度" | notion | 0.334 | 0.366 | 0.287 | ❌ 无 todo skill |

## 关键结论

### 1. 稀疏匹配是多数的弱点
约 40% query 的 sparse=0.000~0.150，分数全靠 dense 撑。原因是 trigger_tags 是抽象词（"调试""审计"），用户口语（"报错了""跑一下"）不匹配。**新 skill 的 trigger_tags 必须采用户真实语料。**

### 2. 不存在的 skill = 永远 miss
verification、TDD、git-worktree、feishu-rules、todo-progress 5 个规则类别无对应 skill。任何 query 都回不到这些规则。这是 system prompt 瘦身的直接障碍——没有 skill 就不能移出 system prompt。

### 3. priority 字段闲置
current matcher.py 无视 priority 等级。highest 的 skill 和 normal 的 skill 在排序上无差别。需要 matcher.py 改造：priority=highest 无条件保底返回 top-2。

### 4. 已有 skill 召回稳定
hermes-oracle-mode (0.57-0.68)、plan (0.49-0.53)、code-review-and-audit (0.46)、system-admin (0.42-0.44) 均有稳定表现。hermes-shipping-verification (0.41) 也不错。

## 对 system prompt 优化的影响

| 可移入 skill（已有稳定 skill） | 必须保留在 prompt | 需新建 skill |
|---|---|---|
| §4 调试 → debugging-patterns | §3 验证铁律 | §7 TDD |
| §5 code review → code-review-and-audit | §1 skill 加载铁律 | §8 并行（扩 oracle-mode tags）|
| §2 plan → plan | 信息真实性红线 | TODO 规范 |
| oracle mode → hermes-oracle-mode | 沟通约束 | 飞书规则 |

## 测试命令

```bash
cd ~/.hermes/vdb && source .venv/bin/activate && PYTHONPATH=$PWD \
  python3 -c "from matcher import search; [print(f'{q}: {r[0][\"skill_name\"]} {r[0][\"final_score\"]:.3f}') for q in ['部署服务', '报错了', '写个测试'] for r in [search(q)]]"
```

环境: Chroma hnsw, SiliconFlow BAAI/bge-m3, 54 skills indexed, v1.0.0 pipeline.
