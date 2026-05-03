# 06 · Skill 编写指南

> 按 Garry Tan "fat skills, thin harness" 模式编写可复用 skill。
> 这一层是 **90% 的价值所在**。

---

## 什么是 Skill

Skill 是一个 **Markdown 文件**，封装了一段"判断流程"——遇到什么任务，先做什么，再做什么，如何判断。

**Skill 不是**：
- 硬编码的 if-else 规则
- 对具体模型的 API 调用代码
- 固定字段的 prompt 模板

**Skill 是**：
- 人类可读的流程描述
- 可被任何模型解读并执行的**判断蓝本**
- 带参数，可复用

---

## Skill 文件的标准结构

```markdown
---
name: enrich-task
description: 收到一个简单任务描述后，从多个源头补充信息，生成结构化的 enriched task
parameters:
  - name: task_description
    required: true
    type: string
  - name: depth
    required: false
    type: enum[shallow, standard, deep]
    default: standard
tools:
  - tools.github
  - tools.airtable
  - tools.search
---

# Enrich Task

## 何时使用
当任务描述模糊、关键信息缺失时，先跑这个 skill 把任务补充完整再执行。

## 执行流程

1. **解析任务描述**
   从 `task_description` 中提取：
   - 目标（这个任务要产出什么？）
   - 约束（时间、资源、依赖）
   - 未知项（需要查证的信息）

2. **补充上下文**（deterministic 部分）
   根据 depth 参数决定调用哪些工具：
   - `shallow`: 只查 Airtable 关联记录
   - `standard`: Airtable + 相关 GitHub issue
   - `deep`: 上述 + Web 搜索 + 历史类似任务

3. **综合判断**（latent 部分）
   读完所有上下文后，输出结构化 profile：
   - 任务真实目标（可能和描述不同）
   - 最关键的 3 个已知事实
   - 最关键的 3 个未知项
   - 推荐的下一步 skill

## 输出格式

```yaml
enriched_task:
  real_goal: ...
  known_facts:
    - ...
  unknowns:
    - ...
  next_skill: ...
```

## 示例

输入：`task_description="帮我调研下这个方向"`

经过 enrich：
```yaml
enriched_task:
  real_goal: "明确 MAE 执行层是否要迁移到 LangGraph"
  known_facts:
    - "当前 orchestrator 代码 ~330 行"
    - "团队诉求优先级：灵活 > 显影 > 速度"
    - "LangGraph 有完整 checkpoint 机制"
  unknowns:
    - "LangGraph 能否和飞书 bot 身份体系集成"
    - "迁移后代码量会膨胀多少"
    - "LangGraph 的学习曲线"
  next_skill: research.md (with depth=deep)
```
```

---

## Skill 的三个关键字段

### 1. `description` 是 resolver 的路由依据

未来实现 latent 路由时，模型会读所有 skill 的 description 来决定调哪个。所以 description 要：
- **动词开头**（"收到 X 后" / "当 Y 时" / "为了 Z"）
- **说清楚输入输出**
- **不要重复 name**

❌ 差：`research` 的描述写成"这是 research skill"
✅ 好：`research` 的描述写成"当需要对某个话题做系统性信息收集和分析时使用"

### 2. `parameters` 明确输入

每个 skill 接受参数，像方法调用一样。不要把参数硬编码在 prompt 里。

### 3. `tools` 声明依赖

skill 用到哪些 deterministic 工具，提前声明。这样 harness 能做安全检查（比如"只读模式下不允许调用会修改数据的工具"）。

---

## Latent vs Deterministic 的标记

在 skill 里要明确区分哪一步是哪种：

```markdown
## 执行流程

1. **读取 GitHub commits**（deterministic）
   调用 `tools.github.get_commits(repo, since="30d")`
   
2. **判断"说的 vs 做的"差距**（latent）
   读完 README、pitch deck、commits，综合判断真实在做什么
   
3. **生成报告**（latent）
   基于上述判断，生成 markdown 报告

4. **写入文件**（deterministic）
   `tools.fs.write(path, content)`
```

---

## 最小 Skill 示例

`skills/research.md`：

```markdown
---
name: research
description: 对给定话题进行深度研究并产出结构化报告
parameters:
  - name: topic
    required: true
    type: string
  - name: focus
    required: false
    type: string
    default: "general overview"
tools:
  - tools.search
---

# Research

## 执行流程

1. 搜索（deterministic）：用 `tools.search.web(topic)` 获取 top 10 结果
2. 阅读判断（latent）：读完所有结果，提取 5 个核心观点
3. 交叉验证（latent）：判断哪些观点有多源印证，哪些是单一信息源
4. 产出报告（latent）：按以下结构生成 markdown

## 报告结构

```
# {topic}

## TL;DR（3 句话）
...

## 核心观点（5 条）
1. ... [来源: X, Y, Z]
2. ...

## 存在分歧的地方
...

## 未覆盖的问题
...
```
```

---

## Executor 如何使用 Skill

Executor 代码里应该只做"加载 skill + 填参数 + 调模型"，不做判断：

```python
# executors/claude_api.py (改进版)

from .base import Task, Step
from tools.llm import call_claude


class ClaudeAPIExecutor:
    bot_name = "Claude-Reasoner"
    
    def execute(self, task: Task):
        # 1. 从 task.context 找到对应 skill（或默认 skill）
        skill_name = task.context.get("skill", "default")
        skill_path = f"skills/{skill_name}.md"
        
        yield Step("加载 skill", f"{skill_path}")
        
        with open(skill_path) as f:
            skill_content = f.read()
        
        # 2. 拼接 prompt：skill 指南 + 具体任务
        prompt = f"""
{skill_content}

---

# Current Task

{task.content}

Follow the skill's execution flow above. Output the final result only.
"""
        
        yield Step("调用模型", f"任务: {task.content[:50]}...")
        
        text, usage = call_claude(prompt)
        
        yield Step(
            "API 返回",
            f"输出 {usage['output_tokens']} tokens"
        )
        
        # 3. 写文件
        output_path = f"outputs/{task.id}.md"
        with open(output_path, "w") as f:
            f.write(text)
        
        yield Step("完成", f"已写入 {output_path}")
```

**关键变化**：Executor 变得更薄了，所有业务逻辑都在 `skills/{name}.md` 里。换模型、换 skill 都不用改 Executor 代码。

---

## Skills 目录的演进

**Phase 8.1（第一次引入 skill）**：
```
skills/
└── default.md          # 最基础的 skill，等价于现在直接调模型
```

**Phase 8.2（常见任务类型）**：
```
skills/
├── default.md
├── research.md
├── code.md
├── review.md
└── summary.md
```

**Phase 8.3（复合 skill）**：
```
skills/
├── research.md
├── code.md
├── enrich-task.md      # 复合：调用其他 skill
├── weekly-report.md    # 复合：research + summary + format
└── ...
```

---

## 和 OpenClaw 原有 SKILL.md 的关系

你之前在 OpenClaw 里写的 SKILL.md 文件（`session-protocol.md`、`claw-vibe-project`、`jianan-presentation-system` 等）**可以直接复用**！它们就是 fat skills 的雏形。

搬迁方式：
1. 把 OpenClaw 的 SKILL.md 复制到 `mae-orchestrator/skills/`
2. 在 frontmatter 加上 `name`、`description`、`parameters`
3. 标记哪些步骤是 latent、哪些是 deterministic
4. 明确它依赖哪些 `tools.*`

这样 OpenClaw 积累的知识就融入了新 orchestrator。

---

## 什么时候开始写 skill？

**不是现在**。先按 04 和 05 把基础 orchestrator 跑通（Phase 5-7），然后 Phase 8 再开始填 skills。

原因：skill 必须在真实任务里迭代才有价值。脱离任务写的 skill 往往是空想。先跑几个真实任务，看 Executor 里哪些 prompt 在重复，那就是第一批要抽取的 skill。
