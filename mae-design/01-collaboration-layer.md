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
- 无证据宣称"已完成"
- 每 5 分钟无意义刷状态

---

## Harness 执行流程（已跑通，2026-03-22）

### 触发方式（渐进式）

**Phase 1 — Sam 手动触发（当前阶段）**
> 你告诉 Sam "跑任务" / "扫一次" → Sam 执行 `python3 -m runtime.task_poller` → 实时日志可见

**Phase 2 — Cron 自动触发（就绪后启用）**
> `bash cron/setup_cron.sh` → 每 10 分钟自动扫 Airtable → 无人干预持续推进

### 任务触发方式
在 Airtable **TaskStateLog**（`tblmb8402TJiPz5h9`）中：
- 把任意记录的 `Status` 改为 `LOADED` → harness 下次 poll 时自动认领并执行

### 完整执行链路
```
Status=LOADED（Airtable）
  → task_poller.py 扫描发现
  → lock_manager.claim()          锁定任务（防重复）
  → state_machine: LOADED→RUNNING
  → task_context.load_with_raw()  读取历史 messages[]
  → llm_caller.call()             调用 LLM（mock/claude/openai）
  → validation.check_status_claim() LENS 门控
  → task_context.save()           写回 messages[]（自动裁剪 >40 条）
  → state_machine: RUNNING→DONE/BLOCKED/REVIEW
  → notify.send_done/blocked()    Discord 推送
  → lock_manager.release()        释放锁
```

### 状态机六态
```
LOADED → RUNNING → DONE      ← 正常完成
                 → BLOCKED   ← 需人工介入（Discord 推送 + next_recovery_step）
                 → REVIEW    ← evidence_pack 不完整，等修复
                 → FAILED    ← 未处理异常
BLOCKED → RUNNING            ← 人工恢复后，重置 Status=LOADED 即可
```

### 证据包标准（DONE 必须满足）
```json
{
  "run_id":       "唯一执行 ID",
  "log_summary":  "1-3 句执行摘要",
  "artifact_link": "产出物链接或路径",
  "writeback_ts": "ISO 8601 时间戳"
}
```

### LLM 配置（.env）
| 参数 | 说明 |
|---|---|
| `LLM_PROVIDER=mock` | 本地测试，不调真实 LLM |
| `LLM_PROVIDER=claude` | 接 Anthropic API |
| `LLM_PROVIDER=openai` | 接 OpenAI / 兼容接口 |
| `LLM_MODEL` | 模型名，如 `claude-opus-4-6` |

### 关键文件位置
| 文件 | 作用 |
|---|---|
| `runtime/task_poller.py` | 主循环入口 |
| `runtime/config.py` | 环境变量 + 字段映射 |
| `runtime/state_machine.py` | 状态转换 |
| `runtime/lock_manager.py` | 幂等锁 |
| `runtime/task_context.py` | 滚动 messages[] |
| `runtime/llm_caller.py` | LLM 调用（mock/claude/openai） |
| `runtime/validation.py` | LENS 机械门控 |
| `runtime/notify.py` | Discord + Feishu 通知 |
| `cron/setup_cron.sh` | Phase 2 cron 安装 |
| `deploy/openclaw_session_protocol.md` | Route B 迁移到 EC2 手册 |

### Airtable 新增字段（已添加）
| 字段 | Field ID | 作用 |
|---|---|---|
| `LockToken` | `fldL0THRubr3BlnnS` | 幂等锁 token |
| `LeaseUntil` | `fldlR87IVt0fw26Zx` | 锁过期时间 |
| `LeaseOwner` | `flddIcjTwghJRRgpG` | 持锁进程标识 |
