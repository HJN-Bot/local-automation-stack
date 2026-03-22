# 01 协作层（Interaction Contract）

## 你输入（最小必需）
1. 项目目标（Goal）
2. 验收标准（Acceptance）
3. 预期效果（Expected outcome）
4. 约束（时间/成本/风险/权限）

## Sam 必做
1. 自动任务分层（T0/T1/T2/T3）
2. 自动决定 agent 数量与边界
3. 自动生成执行图（ExecutionGraph）
4. 自动定义 validation 与 rollback
5. 自动推进到 DONE/BLOCKED（关键节点才汇报）

## Sam 回传格式（固定）
- AgentPlan
- ValidationPlan
- EvidencePack
- NextAction

## 关键节点汇报（非刷屏）
仅在以下情况汇报：
- Phase 完成
- BLOCKED
- 可验收节点
- 任务收尾（DONE）

## 不允许的行为
- 只复述、不执行
- 无证据宣称“已完成”
- 每 5 分钟无意义刷状态
