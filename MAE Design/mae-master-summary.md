# MAE 项目主线汇总
## Multi-Agent Environment · 从概念到落地的完整脉络

> 汇总日期：2026-04-17
> 核心理念：**显影**（让不可见的 A2A 协作过程变得可见，像照片显影一样）
> 项目仓库：https://github.com/HJN-Bot/local-automation-stack

---

## 一、项目定位与核心理念

**MAE（Multi-Agent Environment）** 是一个把"agent-to-agent 通信"从后台黑盒变成可观察、可交互、可自主执行的多 agent 系统。

核心设计哲学是「显影」——就像胶片在显影液里浮现图像一样，让原本隐藏在后台的 agent 协作过程在飞书这样的可视化层中浮现出来，既可被人类观察，也可被其他 agent 感知。

跨域启发来源：**蚁群群体智能**。蚁群的协调不靠中央指挥，而是靠信息素这种"环境中的可见痕迹"。这个机制直接映射到了 MAE 的四层架构。

---

## 二、已确定的四层架构

| 层级 | 角色 | 具体工具 |
|------|------|---------|
| 可视化层（显影） | 让 A2A 通信可见 | 飞书群聊 + 每 agent 独立 bot |
| 任务数据库 | 任务存储与派发 | Airtable（保留，不被飞书替代） |
| 编排器 | 路由、注册、会话记忆 | OpenClaw |
| 执行层 | 具体 agent 角色 | Do / Research / Writer / QA / PM Agents |

**蚁群类比映射**：
- 蚁后（任务发起源）→ Airtable
- 信息素通道（可见痕迹）→ 飞书群聊
- 基因规则（行为模式）→ OpenClaw 配置
- 工蚁分工（弹性角色）→ 各 Agent

---

## 三、核心决策纪要

**1. 每个 Agent 必须有独立 Bot 身份**
共用一个 bot 会让所有消息从同一头像发出，无法分辨谁在说话——这恰恰违背了"显影"的目标。飞书支持一个群里多个 bot，技术上完全可行。

**2. Airtable 保留，不被飞书替代**
Airtable 是任务数据库和自动派发骨干，飞书是通信/显影层。这两者互补而非冗余。流程是：Airtable 收到任务 → webhook 触发 → OpenClaw 分配 → Agent 在飞书对应线程里执行并汇报 → 状态双向同步回 Airtable。

**3. 描述性 ≠ 可执行**（关键洞察）
OpenClaw 的 SKILL.md、session-protocol.md 这些文件是"行为指南"，不是"自主运行时"。它们能在 Claude 被提示时引导行为，但没有一个引擎能自动循环 read → execute → write → report。**要做到真正的 agent 自主，必须引入独立的执行引擎**。

---

## 四、待解决的核心缺口

**执行能力缺口**——这是当前最关键的瓶颈。

讨论过的三条路径：

1. **Claude Code**（最近可达路径）
   - Terminal 自主循环，通过 `claude -p` 被调用
   - 优势：对 Jianan 最熟悉，访问 GitHub repo 也只能走这条路（GitHub robots.txt 屏蔽了 web fetch）
   - 建议作为 MVP 的第一步

2. **自建 orchestrator + Claude API**
   - 完全自定义，灵活度最高
   - 工作量大

3. **成熟框架：Hermes / CrewAI / LangGraph**
   - Hermes：Python，原生支持飞书 WebSocket，有 delegate_task、cron、skill 自生成等机制
   - LangGraph：更通用，ReAct 范式 + StateGraph + Checkpoint，生态成熟

**最小可行闭环目标**：一个 agent 接收任务 → 读 context → 执行 → 写输出文件 → 汇报完成，**全程无人工介入**。

---

## 五、六大痛点 → 解决方案对照

这是之前 Hermes + OpenClaw 讨论的核心产出，已经在两个文档中详细展开：

| # | 痛点 | Hermes 解法 | OpenClaw 解法 | LangGraph 通用解法 |
|---|------|------------|--------------|------------------|
| 1 | 飞书连接不稳 | Lark SDK 自动重连 | Gateway 层适配 | Interface Adapter 模式 |
| 2 | 长任务 session 断 | delegate_task + fallback chain | Markdown checkpoint | Subgraph 隔离 + Checkpointer |
| 3 | 自主性不够 | cron + 分层模型 | SOUL.md identity | Supervisor Node + Model Router |
| 4 | 错误无法自修 | subagent 调 Claude Code CLI | 人工 review | Watchdog Node + 条件边 |
| 5 | A2A 不可见 | 多 profile 独立 bot | MEMORY.md 审计日志 | LangSmith + 飞书日志 |
| 6 | 记忆与学习 | SQLite FTS5 + 程序性记忆 | MEMORY.md + Dreaming 巩固 | Store + Memory Consolidation 节点 |

---

## 六、成本控制：三层模型分级

| 层级 | 模型 | 用途 | 触发场景 |
|------|------|------|---------|
| Tier 1 | DeepSeek R1 / Llama 3.3（免费） | 调度、分类、路由 | Orchestrator 决策 |
| Tier 2 | Gemini Flash / DeepSeek V3（低价） | 代码、研究、执行 | Subagent 实际工作 |
| Tier 3 | Claude Opus / Claude Code | 关键决策、复杂 debug、架构 | 最终验证、难题 |

通过 OpenRouter 实现统一网关，加 fallback provider chain 容错。

---

## 七、已生成的参考文档

之前对话中已产出的完整资料：

1. **mae-architecture-guide.md** — Hermes + OpenClaw 实战方案 + Mac Mini 迁移步骤（含 9 个 Phase）
2. **mae-react-langgraph-guide.md** — ReAct + LangGraph 通用 agent 设计框架
3. **ant-colony-mae-mapping.html** — 蚁群 × MAE 概念映射可视化
4. **urls.txt** — 20 条蚁群智能 + A2A 协议的研究链接（可喂 NotebookLM）

---

## 八、ToDo 清单（按优先级）

### 🔥 紧急（执行层闭环）

- [ ] **选定执行引擎**：Claude Code 还是 LangGraph？建议先用 Claude Code 跑 MVP，再评估是否升级
- [ ] **实现单 agent 闭环**：接任务 → 读 context → 执行 → 写输出 → 汇报，无人工介入
- [ ] **Hermes-agent 的研究任务**：之前锁定但未产出，需要推进出第一个 tangible 输出

### 📐 架构对齐

- [ ] 把现有 MAE design 文档对照四层架构审查一遍，找出不一致的地方
- [ ] 写出一份可直接部署的 OpenClaw 飞书配置（Agent Registry + Routing Rules + Session Memory + 飞书 API 集成层）
- [ ] 决策：OpenClaw 继续做 orchestrator，还是逐步过渡到 LangGraph？

### 🤖 Agent 身份层

- [ ] 为 Do / Research / Writer / QA / PM 各自创建独立飞书 bot（独立头像、独立名字）
- [ ] 设计每个 agent 的能力边界与触发关键词
- [ ] 定义 PM Agent 在群里发任务 header 的模板

### 💾 Mac Mini 部署（到手后）

- [ ] 装 Hermes（如果选这条路）或 Claude Code CLI
- [ ] 配置 OpenRouter 三级模型
- [ ] 搭建 OpenClaw MEMORY.md 与执行引擎的同步层
- [ ] 配置 Airtable webhook

### 🧠 长期机制

- [ ] 记忆巩固机制：OpenClaw Dreaming 概念的具体实现
- [ ] Skill 自生成：从成功的 agent 协作中提取可复用模式
- [ ] "信息素强度" 可视化：飞书里高频协作的 thread 给视觉热度标识

---

## 九、关键启发与设计原则

**1. 描述性文件不等于运行时**
写再好的 SKILL.md 也不会自己跑起来。区分"行为指南"和"执行引擎"，两者都需要。

**2. 身份即可见性**
A2A 显影的关键是让每个 agent 有独立身份。共用身份就是隐身。

**3. 互补而非替代**
Airtable × 飞书、OpenClaw × Hermes、微信 × 飞书——这些都不是非此即彼，而是分工协作。选择基于"这一层解决什么问题"。

**4. 从蚁群学到的三件事**
- 任务弹性分配（角色可切换，而非硬绑定）
- 正反馈回路（高效模式会被强化）
- 阈值响应（防止所有 agent 同时抢一个任务）

**5. GitHub web fetch 不可靠**
新公开的 repo 没被搜索引擎索引 + robots.txt 屏蔽。`git clone` 是唯一稳定路径，这也决定了 Claude Code 在当前工作流中的核心地位。

**6. 跨域概念映射是设计利器**
蚁群 → MAE 的映射不只是类比，而是直接提供了可落地的机制（信息素 = 飞书消息流、基因规则 = OpenClaw 配置）。继续保持这种跨域思考的习惯。

---

## 十、下一步建议的动作

最小化启动方案——先解决"执行层闭环"：

1. 在 Mac Mini 上用 Claude Code 起一个最简 agent
2. 让它从 Airtable 读一个任务
3. 执行后写一个 output 文件到 repo
4. 通过飞书 webhook 发一条完成消息
5. 打通这条最小链路，再逐步加 PM Agent、Research Agent 等角色

关键是**跑起来第一个闭环**，而不是把架构文档写得更完美。执行层的缺口只能用代码填，不能用文档填。
