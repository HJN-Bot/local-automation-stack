# MAE 优化 Backlog

> 更新：2026-03-29
> P0 bug 已在同日修复（commit 见 git log）。
> 本文件追踪 P1 / P2 / P3 级别的改进点，按优先级排序，可以作为 Sprint 计划的输入。

---

## P1 — 可靠性（应该尽快做）

### P1-1：减少 Airtable 写入次数

**现状**
工具循环每次迭代都调用 `task_context.save()`，一个工具密集型任务最多产生 7+ 次 Airtable 写入。
文档承诺"2 writes per task"目前是理想状态，不是实现现状。

**改进方案**
工具循环内只在内存里追加 messages，循环结束后一次性调用 `task_context.save()`。

```python
# 当前（每次迭代写一次）
tool_results = tool_runner.execute_all(...)
messages = task_context.append(messages, ...)
task_context.save(record_id, messages)   # ← 循环内

# 改进后（循环外一次写）
tool_results = tool_runner.execute_all(...)
messages = task_context.append(messages, ...)
# ... 循环结束后
task_context.save(record_id, messages)   # ← 循环外
```

**影响文件**：`runtime/task_poller.py`（`_execute_task` 的工具循环部分）

---

### P1-2：BLOCKED 状态时 Andrew 主动提问

**现状**
任务进入 BLOCKED 后，Feishu 会收到一条通知，但 Andrew 不会主动追问用户需要哪些信息来解锁。用户需要自己理解 blocked_reason 并手动干预。

**改进方案**
在 `notify.send_blocked()` 之后，让 Andrew 在 Feishu 线程里发一条互动消息，提示用户具体需要提供什么信息，以及如何通知 Andrew 继续（例如在 Discord 里 @Andrew 并提供答案）。

**实现思路**
```python
# task_poller.py，BLOCKED 分支
notify.send_blocked(...)
notify.send_agent_update(
    thread_id=feishu_thread_id,
    agent_name="ANDREW",
    msg_type="BLOCKED",
    title="需要你的帮助才能继续",
    fields={
        "卡点": blocked_reason,
        "解锁方式": f"在 Discord @Andrew，说明：{recovery or '请提供更多信息'}",
    },
)
```

**影响文件**：`runtime/task_poller.py`、`runtime/notify.py`（可能需要新增 BLOCKED 消息类型的卡片样式）

---

## P2 — 可扩展性（空闲时优化）

### P2-1：聚合时批量拉取子任务 context

**现状**
`_check_aggregation()` 中对每个兄弟任务分别调用 `load_with_raw(sib["id"])`，N 个子任务 = N 次串行 Airtable API 调用。

**改进方案**
在获取 siblings 列表时，直接从 fields 里读已有信息（status、blocked_reason），只在真正需要 log_summary 时才拉 task_context。多数情况下可以把 N 次拉取减少到 0-1 次。

或者：在子任务 DONE 时，把 log_summary 写回 Airtable 的一个独立字段（如 `LastLogSummary`），聚合时直接读字段，不需要解析 context JSON。

**影响文件**：`runtime/task_poller.py`（`_check_aggregation`），可能需要 Airtable schema 加字段。

---

### P2-2：sessions_send 的 system_prompt 注入位置

**现状**
`_sessions_send` 通过 `_build_user_content()` 把 MAE system_prompt 嵌入 user 消息体（`[TASK CONTEXT]\n...`），它在 OpenClaw session 的消息流里是一条 user 消息，而非真正的 system 指令，优先级低于 agent 自己的 system prompt。

`_sessions_spawn` 是正确的——把 system_prompt 作为独立字段传给 spawn API。

**改进方案**
确认 OpenClaw `/sessions/{id}/messages` API 是否支持传 `system_prompt` 覆盖字段，或者在 payload 里增加 `instructions` 字段。若不支持，保持现状并在 OpenClaw agent 的 system prompt 里加一段 "当收到 `[TASK CONTEXT]` 开头的消息时，优先执行其中的任务指令"。

**影响文件**：`runtime/openclaw_bridge.py`（`_sessions_send`）

---

### P2-3：结构化日志

**现状**
所有日志为纯文本，task_id 混在消息字符串里，无法在日志系统中按 task_id 过滤或聚合。

**改进方案**
使用 Python logging 的 `extra` 参数把 task_id 作为结构化字段注入：

```python
log = logging.getLogger("task_poller")
task_log = logging.LoggerAdapter(log, {"task_id": task_id})
task_log.info("status: %s | agent: %s", current_status, owner_agent)
# 输出：{"task_id": "T-001", "msg": "status: RUNNING | agent: REX", ...}
```

配合 JSON formatter（`python-json-logger`）可直接接入 Datadog / Loki / CloudWatch。

**影响文件**：`runtime/task_poller.py`（`_execute_task`）

---

## P3 — 架构演进（长期规划）

### P3-1：任务依赖图（DAG）替代单层父/子

**现状**
目前只支持一层父/子任务：一个父任务 → N 个子任务，所有子任务完成后父任务激活。无法表达"REX 完成后 LULU 才能开始"这种流水线依赖。

**改进方案**
在 Airtable 加 `DependsOn`（linked record 字段），task_creator 写入依赖关系，`_check_aggregation` 改为检查"该任务的所有依赖项是否已 terminal"，而不是"所有兄弟是否 terminal"。

```
REX: 搜集数据  ──→  LULU: 写报告  ──→  SAM: 汇总
```

**影响范围**：Airtable schema + `task_creator.py` + `task_poller._check_aggregation()`

---

### P3-2：事件驱动替代 cron 轮询

**现状**
任务依赖 cron 每 10 分钟轮询一次，导致：
- RUNNING 多轮次任务（不需要工具但需要继续推理）等待时间最长 10 分钟
- 空转 cron 调用浪费 Airtable 读取 quota

**改进方案**
OpenClaw 或外部系统（Discord bot、Feishu webhook）触发时，直接调用 `run_once()` 或通过 HTTP endpoint 推送任务。cron 保留作为 safety net（清 GC + 捡漏），主要执行路径改为事件驱动。

技术选项：
- 简单：在 `scripts/` 里加一个 Flask/FastAPI webhook endpoint，接收 POST 后调用 `_execute_task()`
- 完整：引入 Celery/Redis 或 Cloud Tasks 作为任务队列

**影响范围**：需要新增 web server 组件，不破坏现有 cron 路径。

---

### P3-3：typed state（dataclass 替代裸 dict）

**现状**
任务状态、LLM 输出、evidence 都是裸 dict，字段名靠 `FIELDS` 映射或字符串字面量，运行时才能发现拼写错误。

**改进方案**
```python
@dataclass
class EvidencePack:
    run_id: str
    log_summary: str
    writeback_ts: str
    artifact_link: str | None = None

@dataclass
class AgentOutput:
    status: Literal["RUNNING", "DONE", "BLOCKED", "REVIEW"]
    action_taken: str
    evidence: EvidencePack
    tool_calls: list[dict] = field(default_factory=list)
    next_step: str = ""
    needs_human: bool = False
    blocked_reason: str | None = None
    next_recovery_step: str | None = None
```

类型检查（mypy/pyright）即可在 CI 捕获字段拼写错误，无需等到运行时。

**影响范围**：`runtime/validation.py`、`runtime/task_poller.py`、`runtime/openclaw_bridge.py`，改动量较大，建议单独一个 PR。

---

## 待办追踪

| ID | 级别 | 状态 | 说明 |
|----|-----|------|------|
| P1-1 | P1 | 待做 | 减少 Airtable 写入次数（工具循环）|
| P1-2 | P1 | 待做 | BLOCKED 时 Andrew 主动提问 |
| P2-1 | P2 | 待做 | 聚合批量拉取 context |
| P2-2 | P2 | 待做 | sessions_send system_prompt 注入位置 |
| P2-3 | P2 | 待做 | 结构化日志 |
| P3-1 | P3 | 待做 | 任务依赖 DAG |
| P3-2 | P3 | 待做 | 事件驱动替代 cron 轮询 |
| P3-3 | P3 | 待做 | typed state dataclass |
