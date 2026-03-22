# Route B — OpenClaw Session Protocol

## 核心改造思路

**现状问题：**
```
Discord 消息 → OpenClaw 单次响应 → 停止
```

**目标架构：**
```
EC2 cron → harness.py → 读 Airtable (LOADED tasks)
                      → 构建 session (system_prompt + messages[])
                      → 调用 OpenClaw API (或 Claude API)
                      → 解析结构化输出
                      → 写回 Airtable (状态 + task_context)
                      → 条件推送 Discord/Feishu 通知
```

**关键原则：Discord 变通知出口，不再是触发源。**

---

## Step 1: 把 harness 代码部署到 EC2

```bash
# 在 EC2 上
git clone https://github.com/HJN-Bot/local-automation-stack.git
cd local-automation-stack
pip3 install -r requirements.txt
cp .env.example .env
# 填入真实的 AIRTABLE_API_KEY / CLAUDE_API_KEY (或 OPENAI_API_KEY) / webhooks
```

---

## Step 2: 配置 LLM_PROVIDER

OpenClaw 自身是 `gpt-5.3-codex`，有两种接入方式：

### 方式 A（推荐）：直接用 Claude API，绕过 OpenClaw 对话层
```env
LLM_PROVIDER=claude
LLM_MODEL=claude-opus-4-6
CLAUDE_API_KEY=sk-ant-...
```
优点：更可控，输出格式稳定，不依赖 Discord 通道。

### 方式 B：让 OpenClaw 成为 harness 的 LLM 后端
```env
LLM_PROVIDER=openai
LLM_MODEL=gpt-5.3-codex
OPENAI_API_KEY=<openclaw-compatible-key>
OPENAI_BASE_URL=<openclaw-api-endpoint>  # 如果 OpenClaw 暴露了 /v1/chat/completions
```
在 `runtime/llm_caller.py` 的 `_call_openai()` 中已支持 base_url 覆盖，只需加：
```python
client = OpenAI(api_key=OPENAI_API_KEY, base_url=os.getenv("OPENAI_BASE_URL"))
```

---

## Step 3: 安装 EC2 cron

```bash
bash cron/setup_cron.sh
# 或直接用 crontab -e 写入：
*/10 * * * * cd /home/ubuntu/local-automation-stack && python3 -m runtime.task_poller >> logs/harness.log 2>&1
```

EC2 是常驻服务器，不会像 Mac 一样睡眠，cron 更可靠。

---

## Step 4: Discord bot 改为纯通知模式

Discord bot 不再触发 OpenClaw 执行任务，只接收 harness 推送的通知。

原先的 bot 触发逻辑：
- 用户发消息 → bot 转发给 OpenClaw → 等待响应 → 发回 Discord

改造后：
- bot 只监听 webhook 入站消息（BLOCKED / DONE 通知）
- 所有任务执行由 harness cron 驱动
- 如需手动触发，在 Airtable 中把任务状态改为 LOADED 即可（harness 10分钟内自动认领）

---

## Step 5: OpenClaw system_prompt 重写

如果你仍然希望 OpenClaw 的对话能力（chat interface）参与执行，
把 OpenClaw channel 的 `systemPrompt` 替换为以下 Harness 指令集：

```
You are an execution agent in a multi-agent harness system.
You will receive a task_context (messages[]) and a system prompt describing your current task.

IMPORTANT RULES:
1. Always respond with a single valid JSON object — no markdown, no explanation outside JSON.
2. The JSON must match this exact schema:
   {
     "status": "RUNNING | DONE | BLOCKED | REVIEW",
     "action_taken": "<what you just did>",
     "evidence": {
       "run_id": "<string>",
       "log_summary": "<1-3 sentences>",
       "artifact_link": "<url or null>",
       "writeback_ts": "<ISO 8601 timestamp>"
     },
     "next_step": "<what should happen next>",
     "needs_human": false,
     "blocked_reason": null,
     "next_recovery_step": null
   }
3. Do NOT claim DONE unless all 4 evidence fields are populated.
4. Do NOT narrate. Do NOT say "I will". Just do it and report.
5. If you cannot proceed without human input: status=BLOCKED, needs_human=true.
```

---

## 验收标准（Route B）

与 Route A 相同：
- [ ] RUNNING 任务 30 分钟内自动推进（无人干预）
- [ ] BLOCKED 时 Discord + Feishu 收到推送（含 next_recovery_step）
- [ ] DONE 时 Airtable 写回完整证据包（4 件套）
- [ ] 幂等锁防止重复执行（测试：手动触发两次 task_poller，确认只执行一次）

---

## 迁移检查清单

- [ ] EC2 上 `.env` 已填写正确凭证
- [ ] Airtable LockToken / LeaseUntil / LeaseOwner 三字段已添加（见 airtable_schema_patch.md）
- [ ] `cron/setup_cron.sh` 已在 EC2 上运行
- [ ] Discord webhook URL 已配置（主推）
- [ ] Feishu webhook URL 已配置（备份）
- [ ] 至少跑通一个完整任务（LOADED → RUNNING → DONE + 证据包）
- [ ] 至少触发一次 BLOCKED 并确认推送到达
