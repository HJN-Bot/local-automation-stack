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

## 需要在 .env 填写的内容

```bash
# OpenClaw Bridge（填完即切换，留空则继续用 llm_caller.py）
OPENCLAW_API_URL=https://your-openclaw-instance/api    # OpenClaw API 地址
OPENCLAW_API_KEY=your-openclaw-api-key                 # 认证 token

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

## OpenClaw API 端点（待确认）

以下端点格式基于 Sam 查到的 OpenClaw docs，上线前需要对照实际 API 验证：

| 操作 | 端点 | 方法 |
|-----|------|------|
| 发消息到现有 session | `/sessions/{session_id}/messages` | POST |
| 新开子 agent run | `/sessions/spawn` | POST |
| 查 session 状态 | `/sessions/{session_id}` | GET |

如果实际端点路径不同，只需修改 `runtime/openclaw_bridge.py` 里的 `_sessions_send()` 和 `_sessions_spawn()` 两个函数，其余代码不变。
