# MAE 项目主控台
## Multi-Agent Environment · Single Source of Truth

> 最后更新：2026-04-17
> 核心理念：**显影**（让不可见的 A2A 协作变成可见的数据流）
> Repo：https://github.com/HJN-Bot/local-automation-stack

---

## 📍 现在你在哪里？

Jianan 过去两个月在 claude.ai 里开了 5+ 个 session 讨论 MAE，讨论内容散落各处。这个文件夹是**整合后的唯一入口**，所有过去讨论的结论都汇聚到这里。

**之前所有讨论文档已被归档为历史参考**（见 `90-archive/`），不要在那些文档上继续迭代。

---

## 🗺️ 文档导航

| 序号 | 文档 | 用途 | 何时读 |
|------|------|------|------|
| 01 | `01-vision-and-principles.md` | 愿景 / 显影理念 / 蚁群映射 / 核心原则 | 每次开始前回顾一次 |
| 02 | `02-architecture.md` | 四层架构 + Garry Tan 三层分工 | 做架构决策时 |
| 03 | `03-execution-layer-decision.md` | 执行层路径选型（为什么是路 B） | 有疑问时回看 |
| 04 | `04-macmini-day0-checklist.md` | Mac Mini 环境准备完整清单 | Mac Mini 到手当天 |
| 05 | `05-orchestrator-implementation.md` | 代码骨架 + 目录结构 + 示例 skill | 写代码时对照 |
| 06 | `06-skill-authoring-guide.md` | 怎么写可复用 skill markdown | 加新能力时 |
| 07 | `07-todos-and-milestones.md` | 任务清单 + 里程碑 | 每周 review |
| 08 | `08-resources.md` | 所有外部链接、API 文档、参考资料 | 查资料时 |
| 09 | `09-postmortem.md` | MAE 之前为什么跑不通的复盘 | 认知混乱时回看 |
| 10 | `10-error-handling-and-retry.md` | 错误分类 + 重试 + 死信队列 | M1 跑通后第 1 周补 |
| 11 | `11-resource-guards.md` | 5 层资源 Guard + 成本控制 | M2 之前必须补完 |
| 12 | `12-roi-and-strategy.md` | 5 条变现路径 + 战略时间窗 | 怀疑投入是否值得时回看 |
| **13** | `13-two-day-battle-plan.md` | **Mac Mini 到手 48 小时作战手册** | **Mac Mini 今天到手，现在就看** |
| 90 | `90-archive/` | 历史讨论文档（归档参考） | 追溯决策时 |

---

## ⚡ 一分钟总览

**项目在做什么**
让 Do / Research / Writer / QA / PM 五个 Agent 在飞书群里可见地协作，任务来自 Airtable，执行在 Mac Mini 本地。

**核心洞察（不要忘）**
1. **显影必须由 orchestrator 强制**，不能靠 agent 自觉
2. **描述性 SKILL.md ≠ 可执行 runtime**，两者都要
3. **Claude Code 是 executor 之一**，不是执行引擎本身
4. **Skills 在上、Harness 在中、Tools 在下**（Garry Tan 三层）
5. **Latent vs Deterministic 要分清**，混了就出 hallucination
6. **Resource Guard 是必需不是优化**，agent 一定会跑飞，问题只是早晚（详见 11）
7. **错误处理分四类**：瞬时/参数/逻辑/致命，对应不同处理策略（详见 10）

**之前为什么跑不通**：见 `09-postmortem.md` —— 5 个根因都是架构层缺陷，**换模型/补配置都不解决**。新方案的本质是用代码替换"人推动"。

**当前最大瓶颈**
执行层闭环未打通。Mac Mini 到手后，**7 天内跑通第一个 "Airtable → Orchestrator → Executor → 飞书显影" 的闭环**，就算真正跨过了这个瓶颈。

**为什么值得做**
5 条具体的变现 / 能力路径（详见 12）：
1. **个人能力质变**：从 AI 应用使用者 → AI 系统设计者
2. **个人 AI 助理**：每天释放 1-2 小时认知带宽
3. **教程出售**：¥499-999 课程，年收入 ¥100k-400k 潜力
4. **咨询服务**：¥30k-200k/单，年收入 ¥280k-720k 潜力
5. **能力护城河**：站在 AI 同一边，5 年职业安全

---

## 🚀 Mac Mini 到手当天

**优先打开 `13-two-day-battle-plan.md`**——这是为"今天到手"场景量身定制的 48 小时作战手册，包含：
- Day 1 (4.24): 跑通最小闭环（Claude API + Airtable + 飞书显影）
- Day 2 (4.25): 多 Executor + 第一个日常 Agent（信息自动化收集）

环境配置的具体命令（SSH / Tailscale / LaunchAgent 自启动）看 `04-macmini-day0-checklist.md`。

---

## 📝 变更历史

- **2026-04-17**：整合 5+ 次讨论，融入 Garry Tan "thin harness, fat skills" 框架，作为 Mac Mini 到手前的最终版本
- 2026-04-13：Hermes + OpenClaw 实战方案讨论（归档）
- 2026-04-10：ReAct + LangGraph 通用化讨论（归档）
- 2026-04-03：蚁群 × MAE 概念映射（归档）
- 2026-03-29：飞书显影层初步设计（归档）
