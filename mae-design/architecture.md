# MAE 系统架构（Harness Engineering）

> 融合来源：karpathy/autoresearch × AutoResearchClaw × learn-claude-code × MAE Protocol v3

---

## 总体设计原则

```
Harness Engineering：系统驱动循环，LLM 只负责推理，不依赖模型"自觉"继续。
```

| 原则 | 说明 |
|---|---|
| 状态外化 | 所有状态存在 Airtable，进程无状态，随时可重启 |
| 模型即工具 | LLM 只是 harness 调用的一个函数，输入/输出格式由 harness 强制 |
| 机械门控 | DONE 必须通过 LENS validation，不由模型自己宣称 |
| 幂等执行 | lock_token + lease_until 防止任何重复执行 |
| 主动通知 | BLOCKED 不等人来问，直接推 Discord |

---

## 三层架构

```
┌─────────────────────────────────────────────────────────────────┐
│  LAYER 1 — 协作层（Interaction Contract）                        │
│  你 ←→ Sam（主脑）                                               │
│  输入：Goal / Acceptance / Constraints                           │
│  输出：AgentPlan / ValidationPlan / EvidencePack / NextAction    │
└──────────────────────────┬──────────────────────────────────────┘
                           │
┌──────────────────────────▼──────────────────────────────────────┐
│  LAYER 2 — 认知层（MAE Protocol v3）                             │
│  角色库：SAM / SCOUT / FORGE / LENS / INK / AUX / SWEEP         │
│  决策：Tier 判断 → Agent 结构 → system_prompt 裁剪注入           │
│  质量：Q1~Q5 分层验收，LENS 机械审阅                             │
└──────────────────────────┬──────────────────────────────────────┘
                           │
┌──────────────────────────▼──────────────────────────────────────┐
│  LAYER 3 — 执行层（Runtime Harness）                             │
│  驱动：cron / Sam 手动触发 → task_poller.py                      │
│  执行：lock → state → context → LLM → validate → writeback      │
│  通知：Discord（主）+ Feishu（备）                                │
│  存储：Airtable TaskStateLog（外部状态，进程无状态）              │
└─────────────────────────────────────────────────────────────────┘
```

---

## 执行层详细流程

```
         ┌─────────────┐
         │  Airtable   │  Status=LOADED
         │ TaskStateLog│◄──────────────── 你 / Sam 设置
         └──────┬──────┘
                │ poll (每10分钟 / 手动)
         ┌──────▼──────────────────────────────────────────┐
         │              task_poller.py                      │
         │                                                  │
         │  1. sweep_expired_locks()  GC 清理过期锁          │
         │  2. find LOADED tasks                            │
         │  3. for each task:                               │
         │                                                  │
         │     ┌─ lock_manager.claim() ───────────────┐    │
         │     │  LockToken + LeaseUntil(+30min)       │    │
         │     │  失败 → skip（另一进程在跑）            │    │
         │     └──────────────────────────────────────┘    │
         │                  │                               │
         │     ┌─ state_machine ──────────────────────┐    │
         │     │  LOADED → RUNNING                    │    │
         │     └──────────────────────────────────────┘    │
         │                  │                               │
         │     ┌─ task_context.load_with_raw() ───────┐    │
         │     │  读 TaskContext 字段                  │    │
         │     │  JSON messages[] → 接力               │    │
         │     │  纯文本 → 作为首次 goal               │    │
         │     └──────────────────────────────────────┘    │
         │                  │                               │
         │     ┌─ build_system_prompt() ──────────────┐    │
         │     │  裁剪版 MAE 认知层注入                 │    │
         │     │  仅注入当前任务强相关内容               │    │
         │     └──────────────────────────────────────┘    │
         │                  │                               │
         │     ┌─ llm_caller.call() ──────────────────┐    │
         │     │  provider: mock / claude / openai     │    │
         │     │  retry: 最多3次（指数退避）             │    │
         │     │  强制 JSON schema 输出                 │    │
         │     └──────────────────────────────────────┘    │
         │                  │                               │
         │     ┌─ validation.check_status_claim() ────┐    │
         │     │  LENS 机械门控                        │    │
         │     │  DONE → 校验 evidence_pack 四件套     │    │
         │     │  BLOCKED → 校验 blocked_reason 存在   │    │
         │     │  不通过 → 降级为 REVIEW               │    │
         │     └──────────────────────────────────────┘    │
         │                  │                               │
         │     ┌─ task_context.save() ────────────────┐    │
         │     │  append LLM response → messages[]    │    │
         │     │  自动裁剪（保留首条+最近38条）          │    │
         │     │  写回 Airtable TaskContext            │    │
         │     └──────────────────────────────────────┘    │
         │                  │                               │
         │     ┌─ state_machine.transition() ─────────┐    │
         │     │  RUNNING → DONE / BLOCKED / REVIEW   │    │
         │     └──────────────────────────────────────┘    │
         │                  │                               │
         │     ┌─ notify ─────────────────────────────┐    │
         │     │  DONE   → Discord [DONE] embed        │    │
         │     │  BLOCKED → Discord [BLOCKED] embed    │    │
         │     │           含 next_recovery_step       │    │
         │     └──────────────────────────────────────┘    │
         │                  │                               │
         │     ┌─ lock_manager.release() ─────────────┐    │
         │     │  清除 LockToken / LeaseUntil          │    │
         │     └──────────────────────────────────────┘    │
         └─────────────────────────────────────────────────┘
```

---

## 状态机

```
                  ┌─────────┐
      触发入口 ──► │ LOADED  │
                  └────┬────┘
                       │ harness claim
                  ┌────▼────┐
                  │ RUNNING │ ◄─── BLOCKED 恢复后重置
                  └────┬────┘
          ┌────────────┼────────────┐
     DONE │        BLOCKED │    REVIEW │
     ┌────▼────┐  ┌─────▼────┐  ┌────▼────┐
     │  DONE   │  │ BLOCKED  │  │ REVIEW  │──► RUNNING (retry)
     └─────────┘  └──────────┘  └─────────┘
     （终态）      Discord推送    evidence
                  等人工恢复      不完整
```

---

## 三个参考项目的精华提取

| 来源 | 提取的核心机制 | 在本系统的落地 |
|---|---|---|
| **karpathy/autoresearch** | 代码即状态，指标驱动决策，不依赖人 | task_context 滚动 JSON = 执行记忆；evidence_pack = 完成指标 |
| **AutoResearchClaw** | 决策分支：成功推进/细化回退/换方向重路由；MetaClaw 跨轮次学习 | state_machine 六态；REVIEW 降级机制；BLOCKED + recovery_step |
| **learn-claude-code** | stop_reason 工具循环；任务板+心跳+异步邮箱；持久队友模式 | task_poller 主循环；Airtable 任务板；Discord 异步通知 |

---

## Route B — OpenClaw 迁移后的架构

```
现在（Route A）：
  本地 Mac → task_poller → Claude API → Airtable → Discord

迁移后（Route B）：
  EC2 cron → task_poller → OpenClaw API（或 Claude API）→ Airtable → Discord

关键改变：
  - Discord 从"触发源"变为"通知出口"
  - OpenClaw 接收 system_prompt + messages[]，返回结构化 JSON
  - Harness 在 EC2 上常驻，不依赖 Discord bot 触发
```

详见：[deploy/openclaw_session_protocol.md](openclaw_session_protocol.md)

---

## 验收标准

- [ ] RUNNING 任务 30 分钟内自动推进（无人干预）
- [ ] BLOCKED 自动推送 Discord（含 next_recovery_step）
- [ ] DONE 必有证据包（run_id / log_summary / artifact_link / writeback_ts）
- [ ] 幂等锁生效（手动跑两次 task_poller，同一任务只执行一次）
- [ ] Context 不膨胀（超 40 条自动裁剪）
