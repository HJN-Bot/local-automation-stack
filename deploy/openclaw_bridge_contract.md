# MAE ↔ OpenClaw Bridge Contract

> 版本：v1
> 更新：2026-03-29
> 目标：把 task_poller 的 LLM 执行层从 llm_caller.py 迁移到 OpenClaw 四个子 Agent

---

## 架构决策

| 层 | 职责 | 实现 |
|---|------|------|
| MAE Harness | 任务状态、锁、Feishu 可视化、工具执行 | local-automation-stack |
| OpenClaw Agents | 真正的 LLM 推理、技能、记忆、人格 | OpenClaw sessions |
| Bridge | 把 Harness 的任务调用路由到正确的 Agent | runtime/openclaw_bridge.py |

---

## 两条执行路径

### Path A — sessions_send（SAM 主脑）

**何时用：** 父任务 / AgentPlan / 任何需要保留长期上下文的场景

```
MAE Harness
  owner_agent = "SAM"
       ↓
openclaw_bridge._sessions_send()
       ↓
POST {OPENCLAW_API_URL}/sessions/{OPENCLAW_SESSION_SAM}/messages
Body: { "content": "<task context>", "role": "user" }
       ↓
OpenClaw Sam session 推理 → 返回结构化 JSON
       ↓
Harness 解析 status / tool_calls / evidence
```

**配置：**
```env
OPENCLAW_SESSION_SAM=<Sam session ID，在 OpenClaw session 面板里找>
```

---

### Path B — sessions_spawn（Rex / Lulu / Alex 执行层）

**何时用：** 子任务 / 独立执行单元 / 不需要长期上下文的场景

```
MAE Harness
  owner_agent = "REX" / "LULU" / "ALEX"
       ↓
openclaw_bridge._sessions_spawn()
       ↓
POST {OPENCLAW_API_URL}/sessions/spawn
Body: {
  "agent_id":      "rex",
  "system_prompt": "<task-specific instructions>",
  "messages":      [...],
  "wait":          true
}
       ↓
OpenClaw 新开 Rex sub-session → 执行 → 返回 output
       ↓
Harness 解析结果
```

**配置：**
```env
OPENCLAW_SESSION_REX=<Rex session ID（spawn 时作为 agent_id 参照）>
OPENCLAW_SESSION_LULU=<Lulu session ID>
OPENCLAW_SESSION_ALEX=<Alex session ID>
```

---

## 需要填写的 .env 内容

### MAE 侧（local-automation-stack/.env）

```bash
# Adapter URL（填完即切换，留空则继续用 llm_caller.py）
OPENCLAW_ADAPTER_URL=http://localhost:8765   # adapter 的运行地址
OPENCLAW_ADAPTER_KEY=your-secret-token      # 可选，留空则不鉴权
```

### Adapter 侧（adapter 运行环境的 .env）

```bash
# Adapter 自身鉴权（和 MAE 侧 OPENCLAW_ADAPTER_KEY 保持一致）
OPENCLAW_ADAPTER_KEY=your-secret-token

# Agent session IDs（在 OpenClaw 的 Sessions 面板里找）
OPENCLAW_SESSION_SAM=sess_xxxxxxxxxxxxxxxx
OPENCLAW_SESSION_REX=sess_xxxxxxxxxxxxxxxx
OPENCLAW_SESSION_LULU=sess_xxxxxxxxxxxxxxxx
OPENCLAW_SESSION_ALEX=sess_xxxxxxxxxxxxxxxx
```

---

## Agent → 路径映射

| Agent | 路径 | 原因 |
|-------|------|------|
| SAM / ANDREW | sessions_send | 主脑，需要保留长期上下文，每次任务在同一个 session 里延续 |
| REX / FORGE  | sessions_spawn | 独立执行单元，coding/research 任务互不污染 |
| LULU / INK   | sessions_spawn | 独立写作 run，每个内容任务上下文隔离 |
| ALEX / AUX   | sessions_spawn | 辅助任务，按需新开 |

---

## Agent 返回格式要求

OpenClaw Agent 的 system prompt 里需要加一段，让它们返回 MAE 标准 JSON：

```
当你在 MAE 任务执行模式下被调用时，必须返回纯 JSON（不加 markdown 包裹）：
{
  "status": "RUNNING | DONE | BLOCKED | REVIEW",
  "action_taken": "...",
  "tool_calls": [],
  "evidence": {
    "run_id": "...",
    "log_summary": "...",
    "artifact_link": null,
    "writeback_ts": "..."
  },
  "next_step": "...",
  "needs_human": false,
  "blocked_reason": null,
  "next_recovery_step": null
}
```

这段已经在 deploy/sam_openclaw_system_prompt.md 里，把它追加到各 Agent 的 systemPrompt。

---

## 迁移策略（渐进式，不破坏现有流程）

| 阶段 | 做什么 | OPENCLAW_API_URL |
|-----|-------|-----------------|
| 现在 | llm_caller.py 继续跑，bridge 代码已在仓库 | 空（不填） |
| Phase 1 | 填写 OPENCLAW_API_URL + SAM session，只迁移父任务 | 填写 |
| Phase 2 | 填写 REX / LULU session，子任务通过 spawn 执行 | 填写 |
| Phase 3 | 移除 llm_caller 中的 claude/openai 配置（不再需要） | 填写 |

**随时可以通过清空 OPENCLAW_API_URL 回退到 llm_caller 模式，不影响任何现有任务。**

---

## Adapter 启动方式

```bash
# 在 OpenClaw 运行环境里
cd local-automation-stack
pip install -r adapters/requirements.txt
uvicorn adapters.openclaw_adapter:app --host 0.0.0.0 --port 8765
```

健康检查：
```bash
curl http://localhost:8765/health
# {"status":"ok","openclaw_available":true,"agents_configured":{...}}
```

## 接入 OpenClaw SDK

打开 `adapters/openclaw_adapter.py`，找到 `# TODO` 注释，把这两行换成你的实际 import：

```python
# 把这行：
from openclaw.tools import sessions_send as _sessions_send
from openclaw.tools import sessions_spawn as _sessions_spawn

# 改成 OpenClaw 实际暴露的 import 路径，例如：
from openclaw.client import sessions_send as _sessions_send
from openclaw.client import sessions_spawn as _sessions_spawn
```

函数签名约定（如果 SDK 签名不同，只需修改 `_do_sessions_send` / `_do_sessions_spawn` 两个函数）：

| 函数 | 期望入参 | 期望返回 |
|------|---------|---------|
| `sessions_send` | `session_id: str, content: str` | `{"content": "<reply>"}` |
| `sessions_spawn` | `agent_id: str, system_prompt: str, messages: list, wait: bool` | `{"output": {"content": "<reply>"}}` |
