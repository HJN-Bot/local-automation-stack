# 03 · 执行层决策备忘

> 这份文档记录**为什么**选现在的方案。有疑问时回看。

---

## 核心决策

**自建 Python Orchestrator，下面挂多种 executor（Claude API / DeepSeek / Claude Code CLI / 其他）。所有 executor 通过统一接口调用，Orchestrator 强制在每步之间显影到飞书。**

---

## 两条路径的对比

### 路 A：Claude Code 做执行引擎 + Hook 显影

**如何工作**：
Claude Code 自己跑主循环，通过 post-tool-use hook 或 SKILL.md 指令汇报飞书。

**为什么否决**：
1. Claude Code 内部 loop 对外是黑盒，显影不稳定
2. 锁死 Claude 生态，无法用便宜模型做调度
3. 靠描述性文档控制行为 = 之前识别出的"认知陷阱"

### 路 B：自建 Orchestrator + 多 Executor 可插拔 ✅

**如何工作**：
Python Orchestrator 取任务 → 选 executor → 执行 → 每步都推飞书。

**为什么采用**：
1. 显影是**编译期保证**（代码结构强制），不是运行时祈祷
2. Executor 可插拔，换模型零成本
3. 成本按任务分级可控

---

## 诉求优先级（锁定）

排序明确的三个诉求：

1. **灵活换模型/CLI** P0
2. **显影流程统一** P1
3. **快速起跑** P2

把"灵活"放第一，直接排除了路 A。把"显影"放第二，意味着必须有中间层强制。把"速度"放第三，接受前期多写 200 行换长期灵活。

---

## 关键设计决定

### 1. Executor 用 yield 返回过程

```python
def execute(task: Task) -> Iterator[Step]:
    yield Step("搜索", "...")
    yield Step("调用", "...")
    yield Step("完成", "...")
```

而不是 `return final_result`。理由：让 Orchestrator 能**在每步之间插入显影**，不用等任务结束。

### 2. Skills 独立于 Executor 代码

业务判断逻辑放 `skills/*.md`，Executor 只负责"加载 skill + 调 API + yield Step"。理由：下次模型升级时 Skill 自动变聪明。

### 3. Router 分两层

- Deterministic 路由：任务类型 → Executor 明确映射（`if task.type == "code"`）
- Latent 路由：模糊任务 → 模型读 skill description 决定（Garry Tan 模式）

MVP 阶段只做 Deterministic，成熟后再引入 Latent。

### 4. 飞书 Bot 每个独立

不共用。理由：共用 bot 所有消息同头像 = 不显影。

### 5. Airtable 保留作为任务层

不合并进飞书。理由：Airtable 是数据库，飞书是通信层，职责分离。

---

## 不选其他方案的理由

| 方案 | 为什么不选 |
|------|----------|
| Hermes Agent 做 Orchestrator | 锁 Python 生态 + 特定 abstraction，灵活度差 |
| LangGraph 做 Orchestrator | MVP 阶段框架复杂度 > 收益 |
| CrewAI | 偏 multi-agent 模式，不符合"thin harness"理念 |
| OpenClaw 做 Orchestrator | SKILL.md 是描述性，没有执行能力 |
| 纯 Claude Code | 黑盒 + 锁生态 |

---

## 未来的演进方向

当 Orchestrator 代码超过 500 行时，考虑迁移 LangGraph。核心概念会自然对应：

| 自建 Orchestrator | LangGraph |
|------------------|-----------|
| 主循环 | StateGraph |
| Executor | Node |
| Step 流 | Conditional Edge |
| Context 管理 | Checkpoint |
| Subagent | Subgraph |

**关键**：现在先自建，是为了深入理解执行层的本质。跑通后迁移 LangGraph 几乎是 1:1 映射。
