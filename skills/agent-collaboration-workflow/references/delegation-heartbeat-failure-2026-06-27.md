# Delegation Heartbeat Failure Report — deleg_090439bc

**日期**: 2026-06-27  
**故障 ID**: deleg_090439bc  
**影响**: 父 Agent 心跳停止 27 分钟，子 Agent 结果无法交付

---

## 事件时间线

| 时间 | 事件 |
|------|------|
| 07:17:47 | `deleg_090439bc` 分发 (2 个子任务并行) |
| 07:17:47~07:42:45 | sa-2 (20260627_071736_a55a08) 开始遭遇流式超时 |
| 07:42:45 | sa-2 触发 `Stream stale for 180s` 警告 |
| 07:42:45~08:05:00 | sa-2 陷入超时重试循环，会话未正常结束 |
| 08:05:00 | sa-1 (20260627_071742_6fc704) 正常完成 (22 API 调用) |
| 08:05:00~08:45:19 | batch 等待 sa-2，`_finalize_batch()` 未执行 |
| 08:45:19 | 父 Agent 强制中断 deleg_090439bc |

**总耗时**: 1663 秒 (27 分 43 秒)  
**实际有效工时**: sa-1 (692s) + sa-2 (~700s) = ~1392s  
**浪费等待时间**: 271 秒 (4.5 分钟)

---

## 根因分析

### 1. async_delegation 架构缺陷

**源码位置**: `tools/async_delegation.py`

```python
def dispatch_async_delegation_batch(...):
    def _worker() -> None:
        combined = runner() or {}  # ← 问题点 1：runner() 无超时保护
        status = "completed"
        # ...
        _finalize_batch(delegation_id, combined, status)  # ← 问题点 2：永不执行
    
    executor.submit(_worker)
```

**问题点 1**: `runner()` 内部子 Agent 卡住时，无 timeout 机制强制终止  
**问题点 2**: `_finalize_batch()` 依赖 `runner()` 返回 → 永不执行 → completion_queue 无事件  
**问题点 3**: 父 Agent 被动等待 completion_queue，无主动心跳检测

### 2. 子 Agent 流式超时

**源码位置**: `agent/chat_completion_helpers.py`

```python
# Stream stale detection (180s 阈值)
if time.time() - last_chunk_time > 180:
    log.warning(f"Stream stale for 180s — no chunks received. Killing connection.")
    # 自动重连 → 继续跑 → 可能真需要时间，也可能死循环
```

**不可观测性**: 父 Agent 无法区分:
- ✅ "子 Agent 在读大文件/跑慢测试/等网络" (legitimate long task)
- ❌ "子 Agent 死循环/无限重试/连接丢失" (stuck)

### 3. Session 状态异常

**数据库查询**:
```sql
SELECT id, started_at, ended_at, end_reason 
FROM sessions 
WHERE id IN ('20260627_071742_6fc704', '20260627_071736_a55a08');
```

**结果**:
| session_id | ended_at | end_reason |
|------------|----------|------------|
| 20260627_071742_6fc704 | 1782545359.88 | agent_close |
| 20260627_071736_a55a08 | NULL | NULL |

**解读**: sa-2 会话**未正常结束** → `ended_at=null` → 批处理无法完成

---

## 故障传播链路

```
deleg_090439bc (batch)
  └─ runner()
       ├─ sa-1 (正常完成) ✅
       └─ sa-2 (流式超时 → 重连 → 卡住) ❌
            └─ runner() 永不返回
                 └─ _finalize_batch() 永不执行
                      └─ completion_queue.put() 永不发生
                           └─ 父 Agent 永远收不到完成通知
                                └─ 27 分钟后强制中断
```

---

## 临时修复 (已执行)

### 1. 手动清理卡住会话

```bash
# 查找未结束的会话
sqlite3 ~/.hermes/state.db "
  SELECT id, started_at, ended_at, end_reason 
  FROM sessions 
  WHERE ended_at IS NULL 
  ORDER BY started_at DESC;
"

# 强制结束 (替换 <session_id>)
sqlite3 ~/.hermes/state.db "
  UPDATE sessions 
  SET ended_at=strftime('%s','now'), end_reason='manual_kill' 
  WHERE id='20260627_071736_a55a08';
"
```

### 2. 验证清理

```bash
sqlite3 ~/.hermes/state.db "
  SELECT id, ended_at, end_reason 
  FROM sessions 
  ORDER BY started_at DESC 
  LIMIT 5;
"
```

---

## 永久修复方案 (待实施)

### Phase 1: 心跳上报机制 (P0)

**修改**: `tools/async_delegation.py` + `tools/process_registry.py`

```python
# 子 Agent 心跳线程 (process_registry.py)
def update_heartbeat(session_id):
    session = registry.get(session_id)
    session.last_heartbeat_at = time.time()

# 心跳线程 (async_delegation.py)
def _heartbeat_thread(session_id, interval=30):
    while not done:
        process_registry.update_heartbeat(session_id)
        time.sleep(interval)

# 父 Agent 心跳检测循环
def _monitor_batch_health(delegation_id):
    while not batch_complete:
        for sa in subagents:
            heartbeat_age = time.time() - sa.last_heartbeat_at
            if heartbeat_age > 300:  # 5 分钟
                log.warning(f"Subagent {sa.id} 超过 300s 无心跳")
            if heartbeat_age > 600:  # 10 分钟
                ask_user(f"要 kill 掉 {sa.id} 吗？")
        time.sleep(120)  # 每 2 分钟检查一次
```

### Phase 2: 分级超时配置 (P1)

**修改**: `config.yaml` + `tools/async_delegation.py`

```yaml
delegation:
  soft_timeout_seconds: 600   # 10 分钟 → 警告
  hard_timeout_seconds: 1800  # 30 分钟 → 询问用户
  max_timeout_seconds: 3600   # 60 分钟 → 强制 kill
  heartbeat_interval_seconds: 30
  heartbeat_timeout_seconds: 300  # 5 分钟无心跳 = stuck
```

**runner() 超时保护**:
```python
from concurrent.futures import ThreadPoolExecutor, TimeoutError

def _worker():
    with ThreadPoolExecutor(max_workers=1) as timeout_executor:
        try:
            combined = timeout_executor.submit(runner).result(timeout=3600)
            _finalize_batch(delegation_id, combined, "completed")
        except TimeoutError:
            log.error(f"Batch {delegation_id} 超时 3600s，强制终止")
            for sa in subagents:
                process_registry.kill(sa.session_id)
            _finalize_batch(delegation_id, {"results": [], "error": "timeout"}, "error")
```

### Phase 3: 进度上报机制 (P2)

**API 设计**:
```python
# 子 Agent 调用
report_progress({
    "step": "reading_large_file",
    "progress_percent": 45,
    "eta_seconds": 180,
    "current_file": "/path/to/large.log"
})

# 父 Agent 展示
[███░░░░░] 45% - Reading large file... (剩 3 分钟)
```

---

## 经验教训

1. **Batch completion 不能依赖单一 `runner()` 返回**  
   → 需要独立的心跳线程 + 超时保护

2. **子 Agent 必须有可观测性**  
   → 心跳 + 进度双上报，区分"真在跑"vs"死了"

3. **父 Agent 不能被动等待**  
   → 必须主动 poll completion_queue + 心跳检测

4. **长任务需要特殊处理**  
   → 10 分钟：警告，30 分钟：询问，60 分钟：强制 kill

5. **健康检查脚本必备**  
   → 自动检测卡住会话，提前报警

---

## 相关脚本

- **健康检查**: `~/scripts/check-delegation-health.sh` (已添加到 `agent-collaboration-workflow` skill)
- **服务检查**: `~/scripts/check-agent-services.sh`

---

## 配置建议

在 `~/.hermes/config.yaml` 添加:

```yaml
delegation:
  # 心跳配置
  heartbeat_interval_seconds: 30
  heartbeat_timeout_seconds: 300  # 5 分钟无心跳 = stuck
  
  # 超时配置
  soft_timeout_seconds: 600   # 10 分钟警告
  hard_timeout_seconds: 1800  # 30 分钟询问
  max_timeout_seconds: 3600   # 60 分钟强制 kill
  
  # Batch 配置
  max_async_children: 3       # 同时运行的子Agent 上限
  batch_timeout_seconds: 7200 # batch 总超时 (2 小时)
```

---

*Report generated by Hermes, 2026-06-27*