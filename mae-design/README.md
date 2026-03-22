# MAE Design (Sam 主脑执行版)

本目录用于沉淀 MAE（Multi-Agent Engineering）在 OpenClaw 的**可执行落地**，不是概念文档。

## 目标
把“你给目标/验收，我来设计与执行”变成稳定机制：
- 你提供：项目目的、验收标准、预期效果、约束
- Sam 提供：Agent 设计、脚本编排、评估门控、回退策略、证据包

## 三层结构
1. `01-collaboration-layer.md`：协作层（你给什么、我做什么、回什么）
2. `02-cognitive-layer.md`：认知层（MAE Protocol v3 的执行裁剪版）
3. `03-execution-layer.md`：执行层（触发→执行→回流→通知）

## 10 步任务总览与进度
见：`10-step-tracker.md`

## 当前阶段结论（2026-03-21）
- 已跑通：外部循环+状态回流（本机 cron + dashboard + Airtable）
- 未跑通：LLM 微控 TaskExecutor 全量闭环（validation 前置、lock/lease 幂等、完整 task_context 滚动）
- 当前综合进度：约 **65%**（从“被动响应体”向“主动执行体”迁移中）

## 最终验收标准
1. RUNNING 能自动推进（无人催促）
2. BLOCKED 能主动推送（含恢复步骤）
3. DONE 必有证据包（run_id / log / artifact / writeback_ts）

## 相关文件
- MAE 主协议：`/home/ubuntu/.openclaw/workspace/agents/MAE-PROTOCOL.md`
- 现有执行器：
  - `tools/t5_refresh_sessions.py`
  - `tools/t5_watchdog_loop.py`
  - `tools/t5_sync_airtable_log.py`
- 状态存储：Airtable `TaskStateLog`、`日期`
