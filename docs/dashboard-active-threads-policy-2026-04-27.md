# Dashboard Active Threads Policy

Date: 2026-04-27
Owner: SAM / Andrew

## Problem

The previous Dashboard Active Threads rule only showed Airtable Ideas/Tasks updated in the last 14 days. After OpenClaw downtime or a quiet operations period, genuinely unfinished mainlines disappeared from the dashboard even though their Airtable state was still Doing/ToDo.

## Updated selection rule

Active Threads should include:

1. Recently updated items from the last 14 days.
2. Doing items updated in the last 90 days.
3. Named strategic mainline ToDo items, especially:
   - MAE mainline / MAE主线
   - AI content collection pipeline / 内容采集流水线
   - AI video production pipeline / 视频生产流水线
   - OpenClaw EC2 → Mini Mac migration record

## Current visible mainlines after sync

- OpenClaw 从 EC2 迁移到 Mini Mac
- 长任务三端回流协议
- MAE主线：任务可视化、群聊可视化与状态回写系统 v1
- AI主线：内容采集流水线 v1
- AI主线：视频生产流水线 v1

## Follow-up operating rule

If a task is strategically important but quiet, update its Airtable progress note instead of relying on recency. The dashboard should show the work Jianan truly needs to pick up, not merely the work touched most recently.
