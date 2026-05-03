# 07 · ToDo 清单与里程碑

> 所有待办事项，按优先级和阶段组织。每周 review 一次。

---

## 🎯 当前焦点：执行层闭环

Mac Mini 到手后 **7 天内** 跑通最小可行闭环（Airtable → Orchestrator → Executor → 飞书显影）。

---

## 📋 ToDo 清单

### 🔥 P0 · Mac Mini 到手前能做的

- [ ] 申请 Anthropic API key（充 $20）
- [ ] 申请 DeepSeek API key（可选）
- [ ] 创建 Airtable "Tasks" base，按 04 文档设 schema
- [ ] 创建飞书 5 个独立 bot（MAE-PM / Claude-Reasoner / DeepSeek-Router / Claude-Code / Research-Agent）
- [ ] 每个 bot 设独立头像、名字
- [ ] 把 5 个 bot 都加到"MAE Workspace"群
- [ ] 记录所有 App ID + App Secret
- [ ] 确认 Airtable 的 API key 有 read+write 权限

### 🔥 P0 · Mac Mini Day 0（到手当天）

**4.24 全天** —— 详见 `13-two-day-battle-plan.md`

- [ ] 上午：Phase 0-4（系统环境 + 依赖 + .env）
- [ ] 下午：Day 1 最小代码（base + llm + feishu + claude_api + display）
- [ ] 晚上：Airtable 集成 + 端到端跑通 1 条任务

**4.25 全天** —— 详见 `13-two-day-battle-plan.md`

- [ ] 上午：加 DeepSeek + Claude Code + Router + 多 bot 身份
- [ ] 下午：第一个日常 agent —— 信息自动化收集（daily-digest）
- [ ] 晚上：复盘 + 配开机自启（LaunchAgent）

### 🟡 P1 · Day 2-3

- [ ] Phase 6.1：Airtable schema 建好（字段完整）
- [ ] Phase 6.2：实现 `tools/airtable.py`
- [ ] Phase 6.3：主循环改成 Airtable 驱动
- [ ] Phase 6.4：端到端跑通一条 Airtable → 显影

### 🟡 P1 · Day 4-7

- [ ] Phase 7.1：DeepSeek executor
- [ ] Phase 7.2：Claude Code executor
- [ ] Phase 7.3：Router 路由逻辑
- [ ] Phase 7.4：多 bot 身份显影
- [ ] Phase 7.5：跑一个真实任务（如"写本周 MAE 进展周报"）

### 🟢 P2 · Week 2

- [ ] 把 OpenClaw 的 SKILL.md 迁移到 `skills/` 目录
- [ ] 写第一个真正的 fat skill（`research.md`）
- [ ] Executor 改成"加载 skill + 填参数"模式
- [ ] 加 `tools/search.py`（搜索工具）
- [ ] 加 `tools/github.py`（GitHub API）
- [ ] **错误处理 v1**（详见 `10-error-handling-and-retry.md`）
  - [ ] `tools/retry.py` 加指数退避装饰器
  - [ ] 给飞书/Airtable API 调用加重试
  - [ ] `tools/error_classifier.py` 实现 4 类错误分类
  - [ ] Airtable Schema 加 RetryCount / LastErrorAt / ErrorClass 字段
  - [ ] `core.py` 集成 `handle_error()` 替换简单的 try/except
- [ ] **资源 Guard v1**（详见 `11-resource-guards.md`）
  - [ ] Layer 1: 输入大小限制
  - [ ] Layer 2: 强制 max_tokens
  - [ ] Layer 3: 单任务预算（保守值起步）
  - [ ] Executor 跟踪 step / tokens / cost
  - [ ] 显影里加成本字段

### 🟢 P2 · Week 3-4

- [ ] 长期运行稳定性（崩溃自动重启）
- [ ] 日志系统（轮转 + 归档）
- [ ] 定时任务（cron：每早自动跑周报草稿）
- [ ] 记忆系统 v1：每日 session 摘要 → `memory/daily/{date}.md`
- [ ] 飞书交互命令（@bot 能触发任务，不只靠 Airtable）
- [ ] **错误处理 v2**
  - [ ] 死信队列（dead_letter 状态）
  - [ ] `tools/alerts.py` 飞书严重告警
  - [ ] 死信任务每日汇总
  - [ ] 错误日志结构化（`logs/errors/{date}.jsonl`）
- [ ] **资源 Guard v2**（M2 之前必须完成）
  - [ ] Layer 4: 每日预算 + `tools/daily_budget.py`
  - [ ] 每日总览自动推飞书（cron 每天 9 点）
  - [ ] 超 50% 警告，超 90% 暂停

### 🔵 P3 · 长期演进

- [ ] Latent 路由（模型读 skill description 决定）
- [ ] Skill 自生成（从成功任务提取 skill 模板）
- [ ] Dreaming 记忆巩固
- [ ] 信息素可视化（高频协作 thread 显示热度）
- [ ] 真正的 multi-agent DAG（不是 delegation 是并行）
- [ ] 评估：何时迁移 LangGraph（orchestrator 超 500 行时）
- [ ] **错误处理 v3**：周报错误模式分析，反复错误转 skill / 代码改进
- [ ] **资源 Guard v3**：Layer 5 全局 kill switch + 飞书命令（pause/resume/status）

---

## 🏁 里程碑

### M1：最小闭环（目标：Mac Mini 到手 + 7 天）

**验收 6 条**：
1. Airtable 新建任务
2. Orchestrator 自动取到
3. 飞书群出现任务主消息（PM bot）
4. Executor bot 逐步汇报
5. Airtable 状态 done
6. 全程无人工介入

**M1 阶段的最低 Guard 要求**（不算验收，但必须有）：
- ✅ Layer 1：任务描述长度限制（10k 字）
- ✅ Layer 2：API max_tokens 强制设置（4096）
- ✅ 简单 try/except，失败 mark failed

**产出**：一个能 7×24 跑的 orchestrator。

---

### M2：多 Agent 显影 + 资源安全（目标：Mac Mini 到手 + 14 天）

**验收**：
- 至少 3 种任务类型路由到不同 executor
- 飞书群能看到 4+ 个不同 bot 头像协作
- 任意一条任务能从 Airtable 追溯到飞书 log
- Orchestrator 连续运行 3 天无崩溃
- **错误分类 + 重试机制完整**（详见 10）
- **5 层 Guard 全部启用**（详见 11）
- **死信队列 + 飞书告警**

**产出**：可演示给外人看的"活着的、安全的"系统。

---

### M3：Skills 化（目标：Mac Mini 到手 + 30 天）

**验收**：
- `skills/` 目录有 5+ 个 skill 文件
- Executor 代码不含任何业务判断
- 加新能力 = 写新 skill，零代码
- 切换主力模型 = 改一行 `tools/llm.py`，所有 skill 立刻"更聪明"

**产出**：真正的 fat skills + thin harness 架构。

---

### M4：记忆 + 自主（目标：Mac Mini 到手 + 60 天）

**验收**：
- 每日自动生成 session 摘要
- 周日自动提炼周报
- 能从过去的任务里检索相关经验
- Cron 任务稳定运行

**产出**：一个会学习、会进化的个人 AI agent 团队。

---

## 🚫 明确不做的事

列在这里，防止走神：

- ❌ 不提前迁移 LangGraph / Hermes / CrewAI
- ❌ 不在 Phase 8 之前写 skill（先跑通基础）
- ❌ 不搞多 agent 并行（delegation 够了）
- ❌ 不接入 Slack / Discord（飞书够了）
- ❌ 不做前端 UI（飞书本身就是 UI）
- ❌ 不做用户系统（你一个人用）
- ❌ 不写测试（MVP 阶段）
- ❌ 不做 CI/CD（本地运行）

等你通过 M3 了再考虑其中任何一条。

---

## 🔄 Review 节奏

**每天**：看飞书群，检查任务执行情况
**每周日**：review 本清单，挪动 ToDo 位置
**每两周**：评估当前里程碑进度
**每月**：写一篇 retrospective，思考架构是否需要调整

---

## 💭 遇到困惑时的决策框架

**"我要加这个功能吗？"**
→ 看它属于 P 几。P0 没做完之前，不做 P1；P1 没做完之前，不做 P2。

**"我要用这个框架吗？"**
→ 先看 03 文档"为什么不选其他方案"。如果当前瓶颈不是那个框架能解决的，就不换。

**"这一步该让模型判断还是写代码？"**
→ 看 01 文档的"Latent vs Deterministic"。拿不准就写代码。

**"这个文档该写多长？"**
→ 看它的读者。给自己看的 3 段就够；给未来 3 个月后的自己看的，要带"为什么"。

**"我要重构吗？"**
→ 看 02 文档的"架构变更触发条件"。没到阈值不重构。
