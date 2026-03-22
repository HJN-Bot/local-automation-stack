# 03 执行层（Runtime Machines）

## 架构（当前）
- Trigger: cron (*/10)
- Loop A: `t5_refresh_sessions.py`（刷新会话追控状态）
- Loop B: `t5_watchdog_loop.py`（关键节点心跳/BLOCKED检测）
- Loop C: `t5_sync_airtable_log.py`（状态写入 Airtable）

## 数据与回流
- Dashboard API: `/api/sessions-tracker`
- Airtable: `TaskStateLog`（执行状态）
- Airtable: `日期`（习惯打卡）

## 新增能力（已落地）
- `GET /api/habits`
- `POST /api/habits/toggle`
- 首页习惯点选直接写 Airtable（非本地临时）

## 目标架构（下一步）
- Trigger: EventBridge / TaskPoller（云端无状态）
- Executor: TaskExecutor（含 LLM 微控 + validation + lock/lease）
- Notify: BLOCKED webhook 主动推送
- Store: Airtable task_context（messages JSON）

## 证据包标准
- run_id
- log summary
- artifact link
- dashboard/airtable writeback timestamp
