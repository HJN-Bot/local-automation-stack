# Gap 与落地路线

## 现存 Gap
1. LLM 微控执行器未全量接主循环
2. validation 未机械前置
3. lock/lease 幂等锁未接入
4. task_context 未形成稳定滚动

## Roadmap（短期）
- P0：补 lock/lease + validation + LoopAt/去重
- P1：接 TaskExecutor（LLM 微控）
- P2：完成 BLOCKED 主动推送闭环验收
- P3：上线 SWEEP 周巡检

## 成功标准
- 30 分钟无人操作，状态自动推进
- BLOCKED 自动通知到人
- DONE 必带证据包
- 同类任务可重复执行且结果稳定
