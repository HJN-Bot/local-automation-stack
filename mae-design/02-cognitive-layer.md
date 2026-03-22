# 02 认知层（MAE Protocol v3 执行裁剪）

认知层来源：`agents/MAE-PROTOCOL.md`

## 核心认知
- Harness Engineering：模型负责推理，系统负责驱动
- 状态机优先：LOADED → RUNNING → REVIEW → DONE/FAILED
- Tier 决策：先判断任务复杂度，再决定 agent 结构

## 标准角色库
- SAM（主脑/PM）
- SCOUT（信息采集）
- FORGE（工程实现）
- LENS（质量审阅）
- INK（内容生产）
- AUX（工具辅助）
- SWEEP（GC/熵增治理）

## 质量系统（Q-system）
- Q1~Q5 分层验收
- LENS 给机械化审阅结论
- Sam 最终裁决 PASS / FIX / ROLLBACK

## 认知层落地原则
- 不把整份协议原样塞给执行器
- 执行器仅注入“与当前任务强相关”的裁剪版 system prompt
- 状态、上下文、通知、回退由执行层保证，不依赖模型自觉
