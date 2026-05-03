# 02 · 架构总图

> MAE 的完整架构。四层横向划分业务，三层纵向划分实现。

---

## 一、四层横向架构（业务视角）

这是从"业务数据流动"的视角看 MAE：

```
┌──────────────────────────────────────────────┐
│  第 1 层：显影层（Visibility Layer）           │
│  飞书群 · 每个 Agent 独立 Bot 身份             │
│  所有 A2A 通信以消息线程形式可见               │
└────────────────────┬─────────────────────────┘
                     ↑
┌────────────────────┴─────────────────────────┐
│  第 2 层：任务层（Task Layer）                 │
│  Airtable · 任务数据库 + 状态追踪             │
│  Webhook 触发 → 状态双向同步                  │
└────────────────────┬─────────────────────────┘
                     ↑
┌────────────────────┴─────────────────────────┐
│  第 3 层：编排层（Orchestration Layer）        │
│  Python Orchestrator · 取任务/路由/强制显影    │
│  ~200 行代码，无框架依赖                       │
└────────────────────┬─────────────────────────┘
                     ↑
┌────────────────────┴─────────────────────────┐
│  第 4 层：执行层（Execution Layer）            │
│  Executors 可插拔：Claude API / DeepSeek /    │
│  Claude Code CLI / Gemini / ...               │
└──────────────────────────────────────────────┘
```

### 数据流动

```
你在 Airtable 新建任务
       ↓
Webhook 触发 Orchestrator（或定期轮询）
       ↓
Orchestrator 决定用哪个 Skill + 哪个 Executor
       ↓
PM Bot 在飞书群发任务主消息（显影 开始）
       ↓
Executor 执行（每步 yield 一个 Step）
       ↓
Orchestrator 把每个 Step 推送到飞书（显影 过程）
       ↓
任务完成 → 写回 Airtable 状态
       ↓
PM Bot 发完成消息（显影 结束）
```

---

## 二、三层纵向架构（实现视角 · Garry Tan 模式）

这是从"代码结构"的视角看 Orchestrator 内部：

```
┌──────────────────────────────────────────────┐
│  Skills 层（Fat Skills · 90% 价值所在）        │
│  Markdown 文件，封装判断流程                   │
│  ├── enrich-task.md                          │
│  ├── research.md                             │
│  ├── review.md                               │
│  ├── diarize.md                              │
│  └── ...                                     │
│  每个带 description，resolver 按需加载          │
└────────────────────┬─────────────────────────┘
                     ↓
┌────────────────────┴─────────────────────────┐
│  Harness 层（Thin Harness · ~200 行 Python）  │
│  ├── 主循环（取任务 → resolve → 执行）         │
│  ├── Resolver（根据任务匹配 skill）            │
│  ├── Context 管理（只加载相关 skill）          │
│  ├── Display 层（强制显影到飞书）              │
│  └── Safety check（只读默认）                 │
└────────────────────┬─────────────────────────┘
                     ↓
┌────────────────────┴─────────────────────────┐
│  Tools 层（Deterministic Foundation · 可靠）   │
│  ├── tools/airtable.py   （SQL 查询）          │
│  ├── tools/github.py     （API 调用）          │
│  ├── tools/search.py     （检索）              │
│  ├── tools/feishu.py     （消息推送）          │
│  └── tools/llm.py        （模型 API 包装）     │
└──────────────────────────────────────────────┘
```

### 分层原则

**智能往上推**：判断、推理、生成 → 放 Skills 层（Markdown）
**执行往下推**：查询、计算、IO → 放 Tools 层（Python）
**Harness 保持精简**：只做"加载 + 串联 + 显影"，不做业务判断

**模型升级的收益**：下次 Claude 升级时，Skills 自动变聪明（因为 Markdown 里的判断流程由新模型解读），Tools 保持可靠（因为是确定性代码）。

---

## 三、两种视角的对应关系

四层横向（业务）和三层纵向（实现）不是替代关系，而是**叠加的两个维度**：

```
              第4层执行层
                 ↓
     ┌───────────┼───────────┐
     │   Skills 层（MD）       │   ← 业务逻辑
     │   Harness 层（Python）  │   ← 流程串联
     │   Tools 层（Python）    │   ← 底层调用
     └───────────┬───────────┘
                 ↓
          第3层编排（Python 代码实体）
                 ↓
          第2层任务（Airtable）
                 ↓
          第1层显影（飞书）
```

- 四层是**系统在真实世界里的样子**
- 三层是**Orchestrator 代码内部的组织方式**

---

## 四、Executor 接口（关键抽象）

所有 executor（不管是 API 还是 CLI）都实现同一个 Python 生成器接口：

```python
def execute(task: Task) -> Iterator[Step]:
    yield Step(action="开始搜索", summary="关键词: X")
    yield Step(action="调用模型", summary="返回 500 tokens")
    yield Step(action="完成", summary="结果已写入 output.md")
```

**关键**：用 `yield` 返回过程而非 `return` 最终结果。这让 Harness 能**在每步之间插入显影**，不用等任务结束。

---

## 五、飞书 Bot 规划

5 个独立 Bot（独立头像 + 独立名字）：

| Bot 名 | 头像建议 | 角色 | 何时发言 |
|-------|---------|------|---------|
| MAE-PM | 📋 橙色 | 项目经理 | 任务主消息、汇总完成 |
| Claude-Reasoner | 🧠 紫色 | 推理/研究 | Claude API executor 工作时 |
| DeepSeek-Router | 🔀 蓝色 | 路由/分类 | DeepSeek 处理轻量任务时 |
| Claude-Code | 💻 黑色 | 代码操作 | Claude Code CLI 执行时 |
| Research-Agent | 🔍 绿色 | 深度研究 | 扩展能力（可选） |

每个 bot 单独申请 App ID 和 App Secret，在 `.env` 里配置。

---

## 六、成本分级策略（三层模型）

通过 OpenRouter 或直连 API 实现：

| 层 | 模型 | 场景 | 估算成本 |
|---|------|------|---------|
| Tier 1 | DeepSeek R1 / Llama 3.3（免费） | 调度、分类、路由 | $0 |
| Tier 2 | Gemini Flash / DeepSeek V3 | 代码、研究、执行 | $1-5/月 |
| Tier 3 | Claude Opus 4.7 / Claude Code | 关键决策、复杂 debug | $10-30/月 |

Router 逻辑：默认 Tier 2，路由层判断时用 Tier 1，关键验证用 Tier 3。

---

## 七、与历史方案的差异

### 相比"Hermes 做执行引擎"方案

- ❌ 之前：Hermes 绑定飞书 + 内部 delegate_task + 调 Claude Code CLI
- ✅ 现在：自建 Python Orchestrator + 所有 executor 平级挂载
- 理由：Hermes 锁定了 Python 生态和特定 abstraction，自建更灵活

### 相比"OpenClaw 做 Orchestrator"方案

- ❌ 之前：OpenClaw 管注册/路由/记忆
- ✅ 现在：OpenClaw 的 SKILL.md 降级为"行为指南参考"，不是 runtime
- 理由：OpenClaw 的 SKILL.md 是描述性文档，没有执行能力

### 相比"LangGraph 通用方案"

- ❌ 之前：用 LangGraph 的 StateGraph + Subgraph + Checkpointer
- ✅ 现在：MVP 用 200 行 Python，未来复杂度超标再迁移
- 理由：框架学习成本 > MVP 收益

### 相比"Claude Code 做执行引擎"方案

- ❌ 之前：Claude Code 内部 loop 驱动一切
- ✅ 现在：Claude Code 是 executor 之一
- 理由：Claude Code 内部黑盒违背显影目标，且锁 Claude 生态

---

## 八、架构变更的触发条件

以下情况出现时，需要重新审视架构：

1. **Orchestrator 代码超过 500 行** → 考虑迁移 LangGraph
2. **Skill 数量超过 30 个** → 考虑引入专门的 resolver 服务
3. **多 agent 并行需求出现** → 引入真正的 DAG 编排
4. **显影消息过多、噪声大** → 分级显影（详细 log + 摘要消息）
5. **记忆膨胀到影响响应速度** → 引入向量检索或分层存储

不到这些阈值时，**保持当前架构**，不提前优化。
