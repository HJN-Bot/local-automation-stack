# MAE ↔ Feishu Thread Workflow

## Why this file exists
There is evidence that the system already explored Feishu thread-linked MAE workflows, but the logic is not yet documented in one stable place.

## Known references
- task sample mentioned by user:
  - `task-20260329-0905-d044`
  - goal: `测试：FeishuThreadId 字段补上后二次冒烟`
- memory indicates ongoing MAE visualization / Feishu group visualization / state writeback work

## Intended workflow model
1. A task is created in Airtable / Dashboard.
2. Task is routed by tag to the correct owner agent.
3. A Feishu thread or linked collaboration surface is created / mapped.
4. Deliverable progress is written to Feishu and/or GitHub.
5. Evidence is written back into Airtable Task Desc.
6. Dashboard reflects the updated state.

## Role of FeishuThreadId
FeishuThreadId acts as the bridge between:
- MAE task identity
- Feishu group/thread conversation
- agent-visible collaboration context
- evidence writeback and status traceability

## Current maturity judgment
### Strongly likely already explored
- task → Feishu collaboration linkage
- thread-based smoke tests
- MAE visualization concept connected to Feishu

### Still needs explicit tracing
- exact successful thread command path
- exact bot identity for group messaging path
- stable production-grade thread writeback workflow

## Recommendation
This workflow should remain inside `local-automation-stack` as system design, not scattered across chat memory or separate loose notes.
