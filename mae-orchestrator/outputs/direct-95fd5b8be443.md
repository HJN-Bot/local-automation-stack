使用 `architecture-designer` skill。

**Agent 编排系统架构图**

```text
┌────────────────────────────────────────────────────────────┐
│                    1. 接入层 / Interface Layer              │
│  Web UI │ API Gateway │ CLI │ Webhook │ Chat Interface      │
└──────────────────────────────┬─────────────────────────────┘
                               │
                               │ HTTP / WebSocket / gRPC
                               ▼
┌────────────────────────────────────────────────────────────┐
│                  2. 编排控制层 / Orchestration Layer        │
│                                                            │
│  ┌──────────────┐   ┌──────────────┐   ┌────────────────┐ │
│  │ Task Router  │→→│ Planner       │→→│ Scheduler       │ │
│  └──────────────┘   └──────────────┘   └────────────────┘ │
│          │                  │                  │            │
│          ▼                  ▼                  ▼            │
│  ┌──────────────┐   ┌──────────────┐   ┌────────────────┐ │
│  │ State Manager│   │ Policy Engine│   │ Retry/Recovery │ │
│  └──────────────┘   └──────────────┘   └────────────────┘ │
└──────────────────────────────┬─────────────────────────────┘
                               │
                               │ Task Protocol / Event Bus
                               ▼
┌────────────────────────────────────────────────────────────┐
│                    3. Agent 执行层 / Agent Layer            │
│                                                            │
│  ┌────────────┐ ┌────────────┐ ┌────────────┐ ┌─────────┐ │
│  │ Researcher │ │ Coder      │ │ Reviewer   │ │ Operator│ │
│  └────────────┘ └────────────┘ └────────────┘ └─────────┘ │
│                                                            │
│  Agent Runtime: prompt context, tools, memory, sandbox      │
└──────────────────────────────┬─────────────────────────────┘
                               │
                               │ Tool Call Protocol
                               ▼
┌────────────────────────────────────────────────────────────┐
│                  4. 工具与能力层 / Tool Layer               │
│                                                            │
│  Browser │ Code Executor │ DB Client │ File System │ APIs   │
│  Search  │ GitHub        │ Slack     │ Calendar    │ RPA    │
└──────────────────────────────┬─────────────────────────────┘
                               │
                               │ Read / Write / Query / Action
                               ▼
┌────────────────────────────────────────────────────────────┐
│                  5. 状态与知识层 / State & Memory Layer     │
│                                                            │
│  Task DB │ Event Log │ Vector Store │ Artifact Store        │
│  Config  │ Secrets   │ Audit Logs   │ User Profiles         │
└────────────────────────────────────────────────────────────┘

┌────────────────────────────────────────────────────────────┐
│              横切能力 / Cross-cutting Concerns              │
│  AuthN/AuthZ │ Observability │ Cost Control │ Guardrails     │
│  Rate Limit  │ Evaluation    │ Human Review │ Compliance     │
└────────────────────────────────────────────────────────────┘
```

**各层职责**

**1. 接入层**

负责接收用户、系统或外部服务发来的任务请求。

核心职责：

- 统一入口：Web UI、API、CLI、Webhook、聊天界面。
- 身份认证与权限校验。
- 请求标准化，把自然语言、API 参数或事件转成统一任务格式。
- 支持同步请求和长任务异步回调。

典型输入：

```json
{
  "user_id": "u_123",
  "task": "分析这个仓库并修复测试失败",
  "priority": "normal",
  "constraints": {
    "max_cost": 5,
    "requires_approval": true
  }
}
```

**2. 编排控制层**

这是系统核心，负责把用户目标拆成可执行任务，并协调多个 Agent 完成。

核心组件：

- `Task Router`：判断任务类型，选择合适的执行策略。
- `Planner`：把目标拆成任务 DAG，例如调研、实现、测试、总结。
- `Scheduler`：决定任务顺序、并发度、超时、优先级。
- `State Manager`：维护任务状态、Agent 状态、上下文状态。
- `Policy Engine`：控制权限、预算、工具访问、人类审批。
- `Retry/Recovery`：处理失败重试、降级、恢复、补偿动作。

任务状态示例：

```text
created → planned → assigned → running → waiting_approval → completed
                                  │
                                  └→ failed → retrying / escalated
```

**3. Agent 执行层**

负责实际推理和执行子任务。每个 Agent 可以是专用角色，也可以是动态生成的临时 Agent。

常见 Agent 类型：

- `Planner Agent`：拆解任务、制定执行计划。
- `Research Agent`：搜索、阅读、归纳信息。
- `Coding Agent`：修改代码、运行测试、提交 patch。
- `Review Agent`：检查风险、审查代码、验证结果。
- `Operator Agent`：调用外部系统、执行工作流。
- `Critic Agent`：做反思、找漏洞、评估输出质量。

每个 Agent Runtime 应包含：

- 当前任务上下文。
- 可用工具列表。
- 权限边界。
- 短期记忆。
- 长期记忆检索。
- 执行日志。
- 输出 schema。

**4. 工具与能力层**

负责把 Agent 的意图变成真实操作。

工具可以包括：

- 浏览器访问。
- Shell / 代码执行。
- 文件系统读写。
- GitHub / GitLab。
- 数据库查询。
- Slack / Discord / 邮件。
- 日历和任务系统。
- 内部业务 API。
- 向量检索。
- OCR、语音、图像生成等模型能力。

工具层要做强隔离：

- 每个工具声明输入输出 schema。
- 每次调用都记录审计日志。
- 高风险工具需要审批。
- Secret 不直接暴露给 Agent。
- 文件、网络、系统命令需要沙箱限制。

**5. 状态与知识层**

负责存储任务运行过程中的所有状态和知识。

核心存储：

- `Task DB`：任务、子任务、状态、依赖关系。
- `Event Log`：所有事件的不可变日志。
- `Vector Store`：语义记忆、文档片段、历史经验。
- `Artifact Store`：代码 patch、报告、截图、文件、运行结果。
- `Config Store`：Agent 配置、策略、工具权限。
- `Secrets Manager`：API key、token、凭证。
- `Audit Logs`：合规与追踪。

建议把 `Event Log` 作为系统事实源，其他状态可以从事件重建。

**通信协议**

**1. 用户到编排层**

推荐协议：

- 外部 API：`HTTP REST` 或 `GraphQL`
- 实时任务状态：`WebSocket` 或 `Server-Sent Events`
- 内部高性能调用：`gRPC`

请求格式建议统一为：

```json
{
  "type": "task.create",
  "trace_id": "tr_abc",
  "user_id": "u_123",
  "payload": {
    "goal": "修复测试失败",
    "context": {},
    "constraints": {}
  }
}
```

**2. 编排层到 Agent 层**

推荐使用事件驱动协议：

- `NATS`、`Kafka`、`Redis Streams` 或 `RabbitMQ`
- 消息格式使用 `JSON Schema` 或 `Protobuf`
- 每个任务有 `trace_id`、`task_id`、`parent_task_id`

任务分发消息：

```json
{
  "type": "agent.task.assigned",
  "trace_id": "tr_abc",
  "task_id": "task_001",
  "agent_role": "coder",
  "input": {
    "goal": "修复 failing tests",
    "repo_path": "/workspace/app"
  },
  "limits": {
    "timeout_seconds": 1800,
    "max_tool_calls": 100
  }
}
```

Agent 返回消息：

```json
{
  "type": "agent.task.completed",
  "trace_id": "tr_abc",
  "task_id": "task_001",
  "status": "completed",
  "output": {
    "summary": "修复了测试失败",
    "artifacts": ["patch_123", "test_log_456"]
  }
}
```

**3. Agent 到工具层**

推荐使用标准化 Tool Call 协议，类似：

```json
{
  "tool": "shell.run",
  "arguments": {
    "cmd": "npm test",
    "cwd": "/workspace/app"
  },
  "policy": {
    "requires_approval": false,
    "timeout_seconds": 120
  }
}
```

工具返回：

```json
{
  "status": "success",
  "stdout": "...",
  "stderr": "",
  "artifacts": []
}
```

高风险工具调用需要走审批：

```text
agent.tool.requested
→ policy.approval.required
→ human.approved / human.rejected
→ tool.executed / tool.blocked
```

**4. 状态同步协议**

建议采用事件溯源模型：

```text
所有状态变化先写 Event Log
→ State Manager 消费事件
→ 更新 Task DB / Cache / UI 状态
```

典型事件：

```text
task.created
task.planned
task.assigned
agent.started
tool.called
tool.completed
approval.requested
approval.granted
task.completed
task.failed
```

**5. Agent 间通信**

不建议 Agent 之间直接随意互发消息。推荐通过编排层中转。

推荐模式：

```text
Agent A → emits result/event → Orchestrator → assigns next task → Agent B
```

这样可以保证：

- 状态可追踪。
- 权限可控。
- 失败可恢复。
- 上下文不会无限膨胀。
- Agent 不会形成不可控循环。

**关键设计决策**

1. 编排层使用事件驱动架构  
   好处是可扩展、可追踪、易恢复。代价是系统复杂度高于同步调用。

2. Agent 不直接访问 Secret  
   Secret 由工具层或网关代为注入，避免模型上下文泄露敏感信息。

3. Agent 间通信经过 Orchestrator  
   牺牲一点灵活性，换来可观察性、审计和可控性。

4. 所有工具调用结构化  
   避免自然语言工具调用不可验证，也方便重试、权限控制和回放。

5. 长任务异步化  
   用户请求只创建任务，执行状态通过事件推送或轮询获取。

**最小可行版本**

如果先做 MVP，可以只保留：

```text
API Gateway
→ Orchestrator
→ Agent Runtime
→ Tool Registry
→ Task DB + Event Log
```

通信协议：

- 外部：HTTP REST
- 内部：Redis Streams
- 工具调用：JSON Schema
- 状态推送：SSE

这个版本足够支持多 Agent 任务拆解、执行、日志追踪和失败重试。
