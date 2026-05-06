# CHANGELOG

## 2026-05-06 — P2 可扩展性修复

### P2-3: 结构化日志（JSON + task_id 注入）

**修改原因**
所有日志为纯文本，task_id 混在消息字符串里。无法用 `jq '.task_id'` 过滤或接入 Datadog/Loki/CloudWatch 等日志系统。每行日志都有一个 task_id，但它是"消息内容的一部分"而非"结构化字段"。

**修改方法**
- 文件：`runtime/task_poller.py`
- 新增 `_StructuredFormatter`：terminal 环境输出人类可读文本，cron/pipe 环境输出 JSON（自动检测 `sys.stderr.isatty()`）
- `_execute_task` 启动时创建 `logging.LoggerAdapter(log, {"task_id": task_id})`，函数内所有 `_log.info()` 自动携带 task_id 字段
- 输出示例（非terminal）：`{"ts":"2026-05-06T08:00:00Z","level":"INFO","logger":"task_poller","msg":"status: RUNNING | agent: SAM | feishu_thread: om_xxx","task_id":"task-20260506-0800-abcd"}`

**是否验证**
- ✅ 代码审查通过：`LoggerAdapter` 是 Python 标准库组件，行为稳定
- ✅ 终端/非终端两路已测试（两个 branch 各走对格式化方式）
- ⚠️ 未在实际 cron 环境跑完整性测试

---

### P2-1: 聚合时直接从 Airtable fields 提取 summary（零额外 API）

**修改原因**
`_check_aggregation()` 中对每个兄弟子任务分别调用 `load_with_raw(sib["id"])`，N 个子任务 = N 次额外 Airtable API 调用。但 `tbl.all()` 已经返回了所有 fields（包括 TaskContext JSON）。

**修改方法**
- 文件：`runtime/task_poller.py`
- 从 `sib_fields[FIELDS["task_context"]]` 直接解析 JSON（已在 `tbl.all()` 返回中），不再调用 `load_with_raw()`
- BLOCKED/FAILED 的兄弟优先用 `blocked_reason` 字段作为 summary
- 当前子任务优先用传入的 `evidence["log_summary"]`
- N 次 API 调用 → 0 次额外 API 调用

**是否验证**
- ✅ 代码审查通过：`tbl.all()` 返回所有字段（Airtable API 默认行为），TaskContext 字段存在且格式正确
- ✅ 逻辑等价：提取 summary 的路径一致（找最后一条 assistant 消息 → 解析 evidence.log_summary）
- ⚠️ 未在实际多子任务场景做端到端测试

---

### P2-2: sessions_send system_prompt 注入位置优化

**修改原因**
`sessions_send` 不支持独立传 system_prompt（仅 sessions_spawn 支持）。MAE 的 system_prompt 被嵌入用户消息体作为 `[TASK CONTEXT]`，优先级低于 agent 自身的系统指令。

**修改方法**
- 文件：`adapters/openclaw_adapter.py`
- `[TASK CONTEXT]` → `[HIGH-PRIORITY TASK — execute these instructions as your primary objective]`
- 添加完整文档注释说明限制，引用 `deploy/sam_openclaw_system_prompt.md`
- Agent 的 OpenClaw system prompt 建议加入："当收到以 [HIGH-PRIORITY TASK] 开头的消息时，将其指令作为首要目标执行"

**是否验证**
- ✅ 代码审查通过：纯文本格式变更，不影响协议结构
- ⚠️ 需手动更新 OpenClaw agent 的 system prompt（见 deploy/sam_openclaw_system_prompt.md）
- ⚠️ 未在真实 sessions_send 链路测试

---

## 2026-05-06 — P1 可靠性修复

### P1-1: 减少 Airtable 写入次数（工具循环优化）

**修改原因**
工具循环（`_execute_task` 的 5b 段）每次 LLM 工具调用迭代都执行一次 `task_context.save()`。
一个工具密集型任务最多 5 次迭代 → 5 次 Airtable API 写入。文档承诺的目标是"2 writes per task"（起+DONE），实际可能达到 7+。

**修改方法**
- 文件：`runtime/task_poller.py`
- 删除工具循环内部的 `task_context.save(record_id, messages)` 调用
- 消息只在内存中 `task_context.append()` 累积
- 循环结束后，在步骤 7（Append LLM response）统一执行一次 `task_context.save()`
- 不影响正确性：工具循环的中间状态不需要持久化（下次 cron 轮询会重新执行，且锁已释放给下一轮 RUNNING）

**是否验证**
- ✅ 代码审查通过：控制流正确，所有消息路径（工具结果 + LLM 最终输出）都最终到达唯一的 save() 调用点
- ✅ 逻辑等价：假设之前 3 次迭代 → 3 次 save，现在 3 次 append + 1 次 save，最终 Airtable 内容完全一致
- ⚠️ 未做端到端跑测试（需 Airtable API key 和真实飞书群环境）

---

### P1-2: BLOCKED 状态时 Agent 主动提问

**修改原因**
任务进入 BLOCKED 后，飞书只会收到一条 `send_blocked()` 通知。用户需要自己理解 `blocked_reason` 并手动干预，而不知道该回复什么信息、在哪里回复才能解锁。缺少互动闭环。

**修改方法**
- 文件：`runtime/task_poller.py`
- 在 BLOCKED 分支的 `send_blocked()` 之后，增加 `notify.send_agent_update()` 调用
- 新卡片类型：`msg_type="BLOCKED"`，标题 "需要你的帮助才能继续 ⚠️"
- 卡片内容：任务ID + 卡点（blocked_reason）+ 解锁方式（具体到"在 Discord 或飞书回复，说明：{recovery}"）
- 如果 recovery 为空，fallback 为"请提供更多信息或指示下一步方向"

**是否验证**
- ✅ 代码审查通过：消息格式兼容现有 `notify.py` 的 `send_agent_update()` 接口
- ✅ API 兼容：`send_agent_update` 只用到 `thread_id`、`agent_name`、`msg_type`、`title`、`fields`，这些都是已有参数
- ⚠️ 未做端到端飞书卡片渲染验证（依赖飞书真实环境）

---

### 附：.gitignore 补充

**修改原因**
`mae-orchestrator/venv/` 目录（Python 虚拟环境，含数十万文件）未被 `.gitignore` 排除，导致 `git add -A` 时意外提交。

**修改方法**
- 文件：`.gitignore`
- 新增规则：`mae-orchestrator/venv/`、`__pycache__/`、`*.pyc`
- 撤销了误提交，重新只提交源码变更

---

## 2026-03-29 — 初始基线

见 `git log origin/main..origin/master`（20 commits），主要包含：
- MAE Runtime 引擎（task_poller / state_machine / lock_manager / validation / notify / config）
- OpenClaw Bridge / Adapter
- 多 Agent 支持（ANDREW/REX/LULU/ALEX）
- 飞书完整集成
- P0 修复：REVIEW 死循环 + artifact_link 强制验证
- 部署文档（PROJECT-ONBOARDING / bridge_contract / session_protocol / sam_openclaw_system_prompt）
- 优化 Backlog（mae_optimization_backlog.md）
