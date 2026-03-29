# MAE v1：Agent Framework & Visible Collaboration Template

> Status: draft v2 — enriched with Feishu technical setup + notify.py upgrade spec
> Updated: 2026-03-29
> Purpose: 将当前多 Agent 系统从"后台编排"升级为"用户可见、可审计、可介入"的 MAE 协作系统。

---

## 1. 背景

当前系统已经具备以下基础：
- 多 Agent 角色（Andrew / Rex / Lulu / Alex）
- OpenClaw 作为统一运行时
- ACP 作为 agent 调用与切换协议
- Dashboard 作为状态可视化面板
- GitHub / Feishu / Airtable 作为外部承载与协作层

但当前仍存在两个核心问题：
1. **Agent 框架未被重新整理清楚**：角色边界、交付边界、协作协议仍不够统一。
2. **Agent-to-Agent 协作过于隐性**：大量交互发生在 internal sessions 中，用户不可见、不可审计、不可直接介入。

因此，MAE v1 的目标是：
> 把现有多 Agent 系统梳理成一套"结构清楚 + 协作显性 + 可被用户旁观和纠偏"的执行框架。

---

## 2. 本轮两个核心任务

### Task A：现有 Agent Framework 再整理

目标：把现有 Agent 系统重新梳理清楚，明确职责、输入、输出、交接方式与系统边界。

#### 需要回答的问题
- Andrew / Rex / Lulu / Alex 分别负责什么？
- MAE / ACP / Dashboard / OpenClaw 分别扮演什么角色？
- 什么属于后台自动执行？什么必须对用户可见？
- 什么交付写 GitHub？什么写 Feishu？什么写 Airtable / Dashboard？
- Agent-to-Agent 的 handoff 应该如何标准化？

#### 预期交付物
1. **Agent 系统结构图**
2. **角色职责说明**
3. **交付边界说明**
4. **Agent-to-Agent 协作协议 v1**

---

### Task B：建立 Feishu 显性协作群

目标：让一部分 Agent-to-Agent 协作从"隐性 session"迁移到"用户可见的 Feishu 群组"。

#### 设计原则
- 不是把所有内部消息都公开，而是只公开"关键协作节点"
- 用户应能看到：任务锁定、进度 heartbeat、BLOCKED、DONE、handoff
- 用户应能在群里直接插话、纠偏、补充要求

#### Feishu 群推荐消息类型
1. **任务锁定消息**
2. **15–30 分钟 Heartbeat**
3. **BLOCKED 报告**
4. **DONE 汇报**
5. **关键 Handoff**
6. **需用户拍板的决策节点**

#### 预期交付物
1. 一个 Feishu 群组
2. 一版 Agent 群内发言规范
3. 一版可复用消息模板
4. 一版"显性 vs 隐性协作"边界定义

---

## 3. 建议的系统结构（v1）

### 3.1 角色分工

| Agent | 角色定位 | 主职责 | 典型输出 | MAE Protocol 映射 |
|------|----------|--------|---------|------------------|
| Andrew | 学习 / 框架整理 / 协议沉淀 | 学习、结构化整理、方法论、流程定义 | 学习卡片、框架文档、协议草案 | SAM（主脑/Orchestrator） |
| Rex | 工作推进 / CER / 项目执行 | 项目推进、风险跟踪、任务落地、商业与工程推进 | 周报、风险清单、推进方案 | FORGE + SCOUT |
| Lulu | 输出生产 / 内容表达 | 选题、脚本、长文稿、公众号、视频文案 | 笔记、文章、脚本、成稿 | INK |
| Alex | Personal / 情绪关系 / 生活运营 | Journal、情绪、关系、成长支持 | 复盘、计划、动作卡 | AUX |

### 3.2 系统组件角色

| 系统组件 | 角色 | 显性/隐性 |
|---------|------|----------|
| OpenClaw | 统一运行时与对话入口 | 隐性（内部调度） |
| ACP | Agent 调用协议 | 隐性（切换触发器） |
| MAE Harness | 多 Agent 执行框架（任务流转 / 生命周期） | 隐性（状态机引擎） |
| Dashboard | 可视化状态板 | 显性（状态查阅） |
| Airtable | 任务真源 / 状态存储 | 显性（任务认领/查阅） |
| GitHub | 代码 / 文档 / 版本化交付 | 显性（产出物归档） |
| Feishu | **关键协作节点** / 用户可见协作 / 显性交流 | **主要显性通道** |

---

## 4. 显性协作与隐性协作边界

### 应保留为隐性 session 的内容
- 高频内部推理
- 中间草稿协商
- 临时调试和试错
- 大量碎片化 agent 内部调度

### 应迁移到显性群的内容
- 任务锁定
- 关键 handoff
- 进度 heartbeat
- BLOCKED
- DONE 汇报
- 需要用户拍板的重大决策

> 原则：**不是所有协作都公开，而是关键状态必须公开。**

---

## 5. 群消息模板（建议）

### 5.1 任务锁定
```text
✅ 任务已锁定
任务ID: <id>
负责人: <agent>
目标: <一句话>
ETA: <时间>
下一次汇报: <时间>
```

### 5.2 Heartbeat
```text
🟡 Heartbeat
任务ID: <id>
当前步骤: <step>
已完成: <summary>
阻塞: <if any>
下一步: <next>
下一次汇报: <time>
```

### 5.3 BLOCKED
```text
🔴 BLOCKED
任务ID: <id>
阻塞原因: <reason>
需要支持: <what is needed>
恢复方案: <recovery path>
```

### 5.4 DONE
```text
✅ DONE
任务ID: <id>
结果: <summary>
证据: <GitHub/Feishu/link>
后续建议: <next>
```

### 5.5 Handoff
```text
🔁 HANDOFF
任务ID: <id>
From: <agent>
To: <agent>
交接内容: <summary>
当前状态: <state>
注意事项: <notes>
```

---

## 6. Bot 架构最终决策

### 结论：一个 Bot + 富文本卡片身份标识

**不推荐「每个 Agent 一个独立 Bot」**的原因：
- 飞书每个 App 需要独立审批（企业版需走 IT 审核），4 个 agent = 4 次审批
- 需维护 4 组 App ID/Secret，运维复杂
- 飞书 API 限速是 App 级别的，分散反而容易踩限制

**推荐「一个 Bot + 卡片身份」**的实现：

每条消息使用**飞书互动卡片（Interactive Card）**，卡片 header 带 agent 名字和颜色，视觉上每个 agent 都有独立身份，但只用一个 Bot 账号：

| Agent | 卡片颜色 | header 标识 |
|-------|---------|------------|
| Andrew (SAM) | `blue` | 🧠 Andrew · SAM |
| Rex (FORGE) | `orange` | ⚙️ Rex · FORGE |
| Lulu (INK) | `purple` | ✏️ Lulu · INK |
| Alex (AUX) | `green` | 🌿 Alex · AUX |

每个任务的所有消息都发在同一个**飞书话题线程（Thread）**里——SAM 发起 root 消息建立线程，后续所有 Agent 回复到该线程，你打开飞书看到的就是按任务线程分组的清晰对话。

---

## 7. 飞书落地技术手册（你需要配置的内容）

### Step 1：创建飞书企业自建应用

1. 打开 [飞书开放平台](https://open.feishu.cn/app)
2. 点击「创建企业自建应用」
3. 填写应用名称（建议：`MAE-Bot`）和描述
4. 记录生成的 **App ID** 和 **App Secret**

### Step 2：开通权限

在应用管理页 → 「权限管理」，开通以下权限：

| 权限名 | 权限 Key | 用途 |
|-------|---------|------|
| 获取与发送单聊、群组消息 | `im:message` | 发送消息 |
| 以应用的身份发消息 | `im:message:send_as_bot` | Bot 发言 |
| 获取群组信息 | `im:chat:readonly` | 获取 chat_id |
| 发送消息到群组 | `im:message:group:send` | 向群发消息 |

### Step 3：发布应用（让 Bot 可以加入群组）

1. 应用管理 → 「版本管理与发布」→ 创建新版本
2. 选择「适用范围」→ 全体成员（或指定你自己）
3. 申请上线（企业内部 app 通常即审即过）

### Step 4：创建协作群组

1. 在飞书客户端创建群组，命名为 `MAE Workspace`（或你喜欢的名字）
2. 把 `MAE-Bot` 加入群组（群设置 → 机器人 → 添加机器人）
3. 获取群组的 **Chat ID**：
   - 方法：在飞书开发者工具调用 `GET /open-apis/im/v1/chats` 查询群列表
   - 或：群设置页面 URL 中包含 chat_id（`oc_` 开头的字符串）

### Step 5：配置 .env

```bash
# 飞书 App OpenAPI 凭证
FEISHU_APP_ID=cli_xxxxxxxxxxxxxxxx
FEISHU_APP_SECRET=xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx

# 群组 Chat ID（oc_ 开头）
FEISHU_NOTIFY_CHAT_ID=oc_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
```

### Step 6：验证连通性

```bash
cd ~/Desktop/个人开发/MAE-automation/local-automation-stack
python3 -c "
from runtime.notify import send_heartbeat
send_heartbeat(running_count=0, blocked_count=0)
print('done')
"
```

飞书群里收到消息即为成功。

---

## 8. notify.py 升级规格（需开发）

当前 `notify.py` 只支持纯文本消息，没有线程支持。升级目标：

### 8.1 新增接口

```python
# 创建任务线程（root 消息），返回 feishu_thread_id
def send_task_start(task_id: str, goal: str, owner_agent: str, eta: str) -> str | None

# 在任务线程内发送 agent 进度更新（富文本卡片）
def send_agent_update(
    thread_id: str,         # feishu_thread_id，回复到此线程
    agent_name: str,        # "Andrew" / "Rex" / "Lulu" / "Alex"
    msg_type: str,          # "HEARTBEAT" | "BLOCKED" | "DONE" | "HANDOFF"
    title: str,
    fields: dict[str, str]  # 卡片字段 key-value
) -> None
```

### 8.2 飞书互动卡片格式（agent 卡片）

```json
{
  "schema": "2.0",
  "config": { "wide_screen_mode": true },
  "header": {
    "title": { "tag": "plain_text", "content": "🧠 Andrew · [DONE] task-001" },
    "template": "blue"
  },
  "body": {
    "elements": [
      {
        "tag": "div",
        "fields": [
          { "is_short": true, "text": { "tag": "lark_md", "content": "**任务ID**\ntask-001" } },
          { "is_short": true, "text": { "tag": "lark_md", "content": "**结果摘要**\n已完成数据抓取" } }
        ]
      },
      {
        "tag": "hr"
      },
      {
        "tag": "note",
        "elements": [{ "tag": "plain_text", "content": "2026-03-29 14:30 UTC" }]
      }
    ]
  }
}
```

### 8.3 线程发送（reply to root）

飞书 Thread 通过 `root_id` 实现：
```python
payload = {
    "receive_id": FEISHU_NOTIFY_CHAT_ID,
    "msg_type": "interactive",
    "content": json.dumps(card_json),
    "root_id": thread_id,   # ← 回复到 root 消息，形成 thread
}
```

### 8.4 Airtable 新增字段（存 Thread ID）

| 字段名 | 类型 | 用途 |
|-------|------|------|
| `FeishuThreadId` | Text | 存储每个任务的飞书线程根消息 ID，供后续 Agent 回复 |

---

## 9. OpenClaw 集成要点

### 9.1 任务开始时

当 Harness 将任务状态从 `LOADED → RUNNING` 时：
1. 调用 `send_task_start()` 在飞书群创建线程
2. 将返回的 `feishu_thread_id` 写回 Airtable `FeishuThreadId` 字段
3. 后续所有 Agent 更新都带上此 `thread_id`

### 9.2 各 Agent 执行中

每个 Agent 执行时通过 `task_context` 传入 `feishu_thread_id`，执行完一个关键步骤后调用 `send_agent_update()` 发 heartbeat 卡片到对应线程。

### 9.3 任务结束时

DONE / BLOCKED 事件触发 `send_agent_update()` 发结果卡片，同时保留原有 `send_done()` / `send_blocked()` 向 Discord 推送（Discord 继续作为备份通道）。

### 9.4 OpenClaw system_prompt 补丁

在 OpenClaw 的 channel systemPrompt 中增加飞书发言指令：

```
FEISHU OUTPUT RULES:
- When status changes to RUNNING: report task_start with goal and ETA
- Every 15-30 min during RUNNING: send heartbeat with current_step and progress
- On BLOCKED: send blocked card with reason and recovery_step
- On DONE: send done card with evidence_pack summary and artifact_link
- Always include feishu_thread_id from task_context when posting
```

---

## 10. 推进顺序（可执行 Roadmap）

### Phase 1 — 基础连通（可立即开始）
- [ ] 完成飞书 App 创建 + 权限申请（约 30 分钟）
- [ ] 填写 `.env` 中的飞书凭证
- [ ] 运行连通性验证脚本，确认消息到达群组

### Phase 2 — 升级 notify.py（约 2 小时开发）
- [ ] 新增 `send_task_start()` 接口（创建线程 + 返回 thread_id）
- [ ] 新增 `send_agent_update()` 接口（富文本卡片 + thread 回复）
- [ ] 更新 `send_blocked()` / `send_done()` 支持可选 `thread_id` 参数
- [ ] Airtable 新增 `FeishuThreadId` 字段

### Phase 3 — Harness 集成（约 1 小时）
- [ ] `task_poller.py` 在 LOADED→RUNNING 时调用 `send_task_start()`
- [ ] 将 `feishu_thread_id` 写回 Airtable
- [ ] `task_context` 中传入 `feishu_thread_id` 供 Agent 使用

### Phase 4 — OpenClaw 配置
- [ ] 更新各 Agent channel 的 systemPrompt，加入飞书发言规则
- [ ] 测试完整链路：Airtable LOADED → 飞书线程建立 → Agent 执行 → 飞书卡片更新 → DONE

---

## 11. 一句话总结

> MAE v1 不是再增加更多 Agent，而是把现有多 Agent 系统整理成一套：**角色清楚、协作显性、用户可见、可持续演进** 的执行框架。
> 飞书群是这套系统的"玻璃展示窗"——你不需要看 Airtable 或 Dashboard，只需打开飞书群，就能知道哪个 Agent 在做什么、做到哪里了、卡在哪里了。
