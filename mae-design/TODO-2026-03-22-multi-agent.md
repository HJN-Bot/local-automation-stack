# TODO (2026-03-22) — Multi-Agent Auto Pipeline

来源：Dashboard 今日 8 条 ToDo/Doing（updateAt=2026-03-22）
目标：围绕「自动跑多-agent集合」主线推进。

## A. 与主线直接相关的 8 个任务（原样映射）

1. `rec3kHOWHCB80eCjS`  
   **Dashboard Task Orchestration 改为真实session事件驱动**（Doing）

2. `rec4ONr1mnTSR4ZUO`  
   **学习参考：Ruflo / SuperSet 多Agent协作机制（精华提炼）**（Doing）

3. `recHfmoTh3owXfZEK`  
   **T2 Event-driven state writeback（Rex先行）**（Doing）

4. `recQAMykgVxO1noo1`  
   **Ruflo/SuperSet多Agent机制提炼与落地**（Doing）

5. `recZoew2N4ptAQvXl`  
   **打通 Dashboard灵感入口 -> n8n抓取 -> OpenClaw总结 -> Feishu AI观点 + GitHub回链**（ToDo）

6. `recdkujVL3fJAZPmx`  
   **信息雷达迁移计划（n8n -> AWS Lambda, API-first）**（Doing）

7. `rech0JcgR4bI3T5Rs`  
   **Session可视化追控MVP（四channel）**（Doing）

8. `recpvtjMFLlGv8Ual`  
   **Hardbeat巡检与主动催办（零LLM）**（Doing）

---

## B. 遗漏补齐（已加入本地执行 TODO）

> 这些是“MAE从65%到85%”必须补的工程项，之前有协议但未完整落地。

9. **Validation 机械门控前置**（LENS/Q-system，不可口头通过）
- 执行器先跑 validation，再允许状态进 DONE。

10. **并发幂等锁**（lock_token + lease_until）
- 防止重复触发重复执行。

11. **task_context 滚动 JSON**
- 每轮执行读写 context（messages），实现跨轮次接力。

12. **DONE 证据包强制校验**
- 必含：run_id / log / artifact link / writeback_ts。

13. **BLOCKED 主动通知闭环验收**
- 真实阻塞场景下验证主动推送与恢复步骤。

14. **SWEEP/GC 周巡检上线**
- 周期清理脏状态、过期锁、孤儿任务。

---

## C. 今日执行顺序（建议）
1) #1 事件驱动编排  
2) #3 状态写回  
3) #7 会话追控  
4) #8 零LLM巡检  
5) #9/#10/#11（关键补丁）  
6) #6 信息雷达主链迁移  
7) #5 灵感入口回流  
8) #2/#4 机制提炼并固化为SOP

---

## D. 验收口径（统一）
- RUNNING 自动推进（30分钟无人干预可见进展）
- BLOCKED 主动推送（含 next_recovery_step）
- DONE 证据包完整（4件套）
