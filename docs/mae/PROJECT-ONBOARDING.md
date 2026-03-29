# MAE 项目完整 Onboarding 文档

> 给 OpenClaw / 新 Agent 读的项目全景手册
> 仓库：https://github.com/HJN-Bot/local-automation-stack
> 更新：2026-03-29

---

## 一句话描述

这是 Jianan 的本地多 Agent 自动化框架（MAE）。用户在 Discord 对 Sam 说任务，Sam 触发 MAE，多个 Agent 在飞书群里可见地协作执行，结果回到 Discord。Airtable 只存任务起止，不存执行过程。

---

## 系统全景图

```
Jianan
  │  Discord: "@Sam 帮我做 XX"
  ▼
Sam · Andrew（OpenClaw，主脑）
  │  出 AgentPlan → 用户确认
  │  exec: python3 scripts/create_task.py --goal "..." --eta "2小时"
  │
  ├─→ Airtable TaskStateLog（写入 Status=LOADED）← 第1次写，也是触发信号
  └─→ 飞书群「MAE Workspace」← Andrew Bot 发🚀任务锁定卡片，建立 Thread
            │
            ▼（Harness cron 每10分钟扫一次）
  runtime/task_poller.py
  │  认领任务 → LOADED → RUNNING
  │  Andrew Bot 在飞书线程：🟡 任务已认领
  │
  ├─ Rex Bot  ⚙️  工程执行（数据抓取、脚本、构建）
  ├─ Lulu Bot ✏️  内容产出（总结、写文档、写飞书页面）
  └─ Alex Bot 🌿  辅助支持
            │
            ▼（任务完成）
  Airtable（写 Status=DONE + evidence_pack）← 第2次写，也是最后一次写
  飞书线程（✅ DONE 卡片 + 产出链接）
  Discord（[DONE] task-xxx 推送通知）
            │
            ▼
Sam 收到 Discord 通知 → 在 Discord 回复 Jianan
```

---

## 仓库结构

```
local-automation-stack/
├── runtime/                 ← 核心执行引擎（Python）
│   ├── task_poller.py       ← 主循环：扫 Airtable → 执行 → 通知
│   ├── task_creator.py      ← Sam 调用：创建任务 + 建飞书线程
│   ├── state_machine.py     ← 状态转换（LOADED/RUNNING/DONE/BLOCKED）
│   ├── lock_manager.py      ← 幂等锁（防重复执行）
│   ├── task_context.py      ← 滚动 messages[] 上下文
│   ├── llm_caller.py        ← LLM 调用（claude/openai/mock）
│   ├── validation.py        ← LENS 机械门控
│   ├── notify.py            ← 飞书富文本卡片 + Discord embed 推送
│   └── config.py            ← 所有环境变量定义
│
├── scripts/
│   └── create_task.py       ← CLI：Sam 用 exec 工具调用这个来创建任务
│
├── docs/mae/
│   ├── PROJECT-ONBOARDING.md         ← 本文件
│   ├── mae-v1-agent-framework-and-visible-collab-template.md  ← 完整设计文档
│   └── （其他设计文档）
│
├── mae-design/              ← 架构设计文档
│   ├── architecture.md      ← 三层架构详解
│   ├── interaction_contract.md ← AgentPlan 协议
│   └── gap-and-roadmap.md
│
├── deploy/
│   ├── sam_openclaw_system_prompt.md ← Sam 的 systemPrompt 补丁（必读）
│   ├── openclaw_session_protocol.md  ← Route B：EC2 部署手册
│   └── airtable_schema_patch.md      ← Airtable 字段清单
│
├── cron/setup_cron.sh       ← 安装定时任务（每10分钟跑 task_poller）
└── .env.example             ← 所有需要填写的环境变量
```

---

## 关键设计决策（已定稿）

### 1. Airtable 只存任务起止，不存执行过程
- 每个任务 **只写 2 次 Airtable**：创建（LOADED）+ 完成（DONE/BLOCKED）
- 执行日记、heartbeat、agent 间 handoff → 全部在飞书线程里
- 原因：Airtable 免费版 records 数量有限，且执行过程不需要持久化

### 2. 飞书用 4 个独立 Bot，不是 1 个共用 Bot
- 飞书 Bot 头像/名字是 App 级别固定的，单条消息无法覆盖
- 1 个 Bot = 群里所有气泡同一个头像，无法「显影」
- 4 个独立应用 = Andrew/Rex/Lulu/Alex 各自有头像，直接可辨
- 未配置某 Agent 的专属 App 时，自动 fallback 到默认 Bot（渐进式上线）

### 3. 飞书 Thread 用 root_id 机制
- Sam 发任务锁定卡片 → 获得 message_id → 存为 feishu_thread_id
- 后续所有 Agent 更新带 root_id → 在同一线程回复，按任务聚合
- 主 timeline 只显示：锁定 / DONE / BLOCKED（保持干净）
- 线程内显示：Heartbeat、Handoff、执行细节

### 4. Discord 是 Sam 和用户的对话通道，也是最终通知出口
- Discord → Sam：用户发任务指令
- Sam → Discord：任务确认、结果汇报
- Harness → Discord：DONE/BLOCKED 通知（Sam 接收并转述给用户）

---

## 已完成的内容（截至 2026-03-29）

| 模块 | 状态 | 说明 |
|-----|------|------|
| Harness 主循环 | ✅ 完成 | task_poller + state_machine + lock + validation |
| Feishu 多 Bot 通知 | ✅ 完成 | 4 Agent 独立 Bot，富文本卡片，线程支持，token 缓存 |
| 任务创建接口 | ✅ 完成 | task_creator.py + scripts/create_task.py |
| Sam systemPrompt 补丁 | ✅ 完成 | deploy/sam_openclaw_system_prompt.md |
| 飞书 thread_id 贯通 | ✅ 完成 | config FIELDS + task_poller 传参 |
| 设计文档 | ✅ 完成 | mae-v1 完整文档含飞书设置手册 |
| Feishu App 创建（Andrew） | ⏳ 进行中 | Jianan 已建立 Sam Bot，拉入飞书群 |
| Feishu App 创建（Rex/Lulu/Alex） | ❌ 待完成 | 还需建 3 个 |
| Airtable FeishuThreadId 字段 | ❌ 待完成 | 需手动在 Airtable 添加 Text 字段 |
| .env 飞书凭证填写 | ❌ 待完成 | 需填 4 组 App ID/Secret |
| Sam systemPrompt 应用 | ❌ 待完成 | 需在 OpenClaw Andrew 里粘贴 |
| 端到端测试 | ❌ 待完成 | 跑一次完整任务验证链路 |

---

## 环境变量清单（.env 需要填写的）

```bash
# Airtable
AIRTABLE_API_KEY=pat...
AIRTABLE_BASE_ID=app...
AIRTABLE_TABLE_TASKSTATELOG=tbl...   # 默认 tblmb8402TJiPz5h9

# LLM
LLM_PROVIDER=claude                  # claude / openai / mock
LLM_MODEL=claude-opus-4-6
CLAUDE_API_KEY=sk-ant-...

# Discord（Sam 接收通知的频道）
DISCORD_BOT_TOKEN=...
DISCORD_NOTIFY_CHANNEL_ID=...

# 飞书群 Chat ID（所有 Bot 发到同一个群）
FEISHU_NOTIFY_CHAT_ID=oc_...

# 默认 Bot（fallback）
FEISHU_APP_ID=cli_...
FEISHU_APP_SECRET=...

# Andrew Bot（Sam 主脑）
FEISHU_APP_ID_ANDREW=cli_...
FEISHU_APP_SECRET_ANDREW=...

# Rex Bot（工程执行）
FEISHU_APP_ID_REX=cli_...
FEISHU_APP_SECRET_REX=...

# Lulu Bot（内容产出）
FEISHU_APP_ID_LULU=cli_...
FEISHU_APP_SECRET_LULU=...

# Alex Bot（辅助支持）
FEISHU_APP_ID_ALEX=cli_...
FEISHU_APP_SECRET_ALEX=...
```

---

## Airtable 字段清单（TaskStateLog 表）

| 字段名 | 类型 | 说明 | 是否已有 |
|-------|------|------|---------|
| TaskId | Text | 任务唯一 ID | ✅ |
| Status | Single select | LOADED/RUNNING/DONE/BLOCKED/REVIEW/FAILED | ✅ |
| OwnerAgent | Text | SAM/REX/LULU/ALEX | ✅ |
| TaskContext | Long text | JSON messages[]（执行上下文） | ✅ |
| Source | Text | discord/manual/feishu | ✅ |
| RunId | Text | 执行 run ID | ✅ |
| ArtifactLinks | Text | 产出物链接 | ✅ |
| BlockedReason | Text | 阻塞原因 | ✅ |
| NextRecoveryStep | Text | 恢复步骤 | ✅ |
| LockToken | Text | 幂等锁 token | ✅ |
| LeaseUntil | Text | 锁过期时间 | ✅ |
| LeaseOwner | Text | 持锁进程 | ✅ |
| UpdatedAt | Text | 最后更新时间 | ✅ |
| **FeishuThreadId** | **Text** | **飞书线程根消息 ID** | **❌ 需新增** |

---

## 接下来要做的事（优先顺序）

### 🔴 P0（现在做，30 分钟内）

**1. 获取 Andrew Bot 的 App ID 和 App Secret**
- 打开 https://open.feishu.cn/app
- 找到刚建的 Sam/Andrew 应用
- 复制 App ID 和 App Secret
- 填入 `.env` 的 `FEISHU_APP_ID_ANDREW` 和 `FEISHU_APP_SECRET_ANDREW`
- 同时填入 `FEISHU_NOTIFY_CHAT_ID`（飞书群的 oc_ 开头字符串）

**2. 在 Airtable 新增 FeishuThreadId 字段**
- 打开 Airtable → TaskStateLog 表
- 新增字段：名称 `FeishuThreadId`，类型 `Single line text`

**3. 在 OpenClaw 的 Andrew session 里应用 systemPrompt 补丁**
- 打开 `deploy/sam_openclaw_system_prompt.md`
- 把内容追加到 Andrew 的 systemPrompt 末尾

### 🟡 P1（今天内）

**4. 验证 Andrew Bot 能发消息**
```bash
cd ~/Desktop/个人开发/MAE-automation/local-automation-stack
python3 -c "
from runtime.notify import send_task_start
tid = send_task_start('test-001', '连通性验证', owner_agent='ANDREW', eta='立即')
print('thread_id:', tid)
"
```
飞书群里看到 Andrew 的卡片 = 成功

**5. 跑一次完整任务测试**
```bash
python3 scripts/create_task.py --goal "测试：确认 MAE 端到端链路" --eta "5分钟" --source discord
# 记录返回的 task_id 和 feishu_thread_id
python3 -m runtime.task_poller
# 飞书群里看到 Andrew 认领、执行、完成的卡片序列
```

### 🟢 P2（后续）

**6. 建 Rex / Lulu / Alex 的飞书 Bot**（每个约 15 分钟）
- 重复 Andrew Bot 的创建流程 3 次
- 填入对应的 `.env` 变量

**7. 安装 cron，让 Harness 自动跑**
```bash
bash cron/setup_cron.sh
```

---

## 关键文档链接

| 文档 | 链接 | 用途 |
|-----|------|------|
| 完整设计文档 | https://github.com/HJN-Bot/local-automation-stack/blob/master/docs/mae/mae-v1-agent-framework-and-visible-collab-template.md | 架构决策全记录 |
| Sam systemPrompt 补丁 | https://github.com/HJN-Bot/local-automation-stack/blob/master/deploy/sam_openclaw_system_prompt.md | 粘贴到 Andrew 的 OpenClaw 配置里 |
| Airtable 字段说明 | https://github.com/HJN-Bot/local-automation-stack/blob/master/deploy/airtable_schema_patch.md | 对照检查字段是否齐全 |
| EC2 部署手册 | https://github.com/HJN-Bot/local-automation-stack/blob/master/deploy/openclaw_session_protocol.md | Route B：把 Harness 迁移到服务器 |

---

## 给 OpenClaw 的接管指令

如果你是接管这个项目的 OpenClaw Agent，请按以下顺序理解和落地：

1. **读** `docs/mae/mae-v1-agent-framework-and-visible-collab-template.md` — 理解整体设计意图
2. **读** `runtime/` 下所有 `.py` 文件 — 理解现有代码能力边界
3. **读** `deploy/sam_openclaw_system_prompt.md` — 这是你（Sam）需要遵守的行为协议
4. **执行** P0 清单（见上方）— 完成飞书连通
5. **测试** 端到端链路 — 一次完整任务从 Discord 触发到飞书可见
6. **报告** 测试结果给 Jianan，并列出下一步 P1/P2 的执行计划
