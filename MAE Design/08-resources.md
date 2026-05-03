# 08 · 资源与链接

> 所有外部参考资料。按主题分类。

---

## 🏗️ 项目本身

| 资源 | 链接 |
|------|------|
| 项目仓库 | https://github.com/HJN-Bot/local-automation-stack |

---

## 🔧 核心工具文档

### Anthropic

| 资源 | 链接 |
|------|------|
| Claude API | https://docs.claude.com |
| Claude Code | https://docs.claude.com/en/docs/claude-code |
| Python SDK | https://github.com/anthropics/anthropic-sdk-python |
| Building agents | https://www.anthropic.com/engineering/building-agents-with-the-claude-agent-sdk |

### 飞书（Lark）

| 资源 | 链接 |
|------|------|
| 开发者后台 | https://open.feishu.cn |
| 开放平台文档 | https://open.feishu.cn/document/home/index |
| 消息 API | https://open.feishu.cn/document/server-docs/im-v1/message/create |
| WebSocket 接入 | https://open.feishu.cn/document/uAjLw4CM/ukTMukTMukTM/reference/event-subscription-guide/overview |

### Airtable

| 资源 | 链接 |
|------|------|
| API 文档 | https://airtable.com/developers/web/api/introduction |
| Token 管理 | https://airtable.com/create/tokens |
| pyairtable SDK | https://pyairtable.readthedocs.io/ |

### DeepSeek

| 资源 | 链接 |
|------|------|
| API 文档 | https://api-docs.deepseek.com/ |
| 平台 | https://platform.deepseek.com |

### OpenRouter（可选统一网关）

| 资源 | 链接 |
|------|------|
| 首页 | https://openrouter.ai |
| 模型列表 | https://openrouter.ai/docs/guides/overview/models |
| 定价 | https://openrouter.ai/pricing |
| Provider Routing | https://openrouter.ai/docs/guides/routing/provider-selection |
| 成本优化指南 | https://sidsaladi.substack.com/p/openrouter-101-the-complete-guide |

---

## 🎓 理论参考

### Garry Tan "Thin Harness, Fat Skills"

| 资源 | 链接 |
|------|------|
| 原 X 帖子 | https://x.com/garrytan/status/2042925773300908103 |
| gstack 实现 | https://github.com/garrytan/gstack |
| 实战分析 | https://codex.danielvaughan.com/2026/03/30/gstack-garry-tan-production-skills-toolkit/ |

### 蚁群群体智能

| 资源 | 链接 |
|------|------|
| Deborah Gordon 《Ant Encounters》 | https://press.princeton.edu/books/paperback/9780691138794/ant-encounters |
| Deborah Gordon 《Ecology of Collective Behavior》(2024) | https://press.princeton.edu/books/hardcover/9780691232157/the-ecology-of-collective-behavior |
| Dorigo 《Ant Colony Optimization》 | https://mitpress.mit.edu/9780262042192/ant-colony-optimization/ |

### Agent-to-Agent 协议

| 资源 | 链接 |
|------|------|
| A2A Protocol GitHub | https://github.com/a2aproject/A2A |
| IBM A2A 介绍 | https://www.ibm.com/think/topics/agent2agent-protocol |
| Microsoft A2A 分析 | https://www.microsoft.com/en-us/microsoft-cloud/blog/2025/05/07/empowering-multi-agent-apps-with-the-open-agent2agent-a2a-protocol/ |

### 多 Agent 框架对比

| 资源 | 链接 |
|------|------|
| 2026 多 Agent 框架对比 | https://gurusup.com/blog/best-multi-agent-frameworks-2026 |
| 持久 AI Agent 对比 | https://thenewstack.io/persistent-ai-agents-compared/ |

---

## 📚 备选框架（未来可能迁移）

### LangGraph

| 资源 | 链接 |
|------|------|
| GitHub | https://github.com/langchain-ai/langgraph |
| 官方文档 | https://docs.langchain.com/oss/python/langgraph |
| Memory 文档 | https://docs.langchain.com/oss/python/langgraph/memory |
| LangSmith（可观测） | https://smith.langchain.com |
| 深度指南 | https://www.mager.co/blog/2026-03-12-langgraph-deep-dive/ |

### Hermes Agent

| 资源 | 链接 |
|------|------|
| 官方文档 | https://hermes-agent.nousresearch.com/docs/ |
| GitHub | https://github.com/NousResearch/hermes-agent |
| Subagent Delegation | https://hermes-agent.nousresearch.com/docs/user-guide/features/delegation/ |
| Claude Code Skill | https://github.com/NousResearch/hermes-agent/blob/main/skills/autonomous-ai-agents/claude-code/SKILL.md |

### OpenClaw（当前在用）

| 资源 | 链接 |
|------|------|
| 文档 | https://docs.openclaw.ai |
| 记忆系统 | https://docs.openclaw.ai/concepts/memory |
| Workspace 模板 | https://github.com/kindomLee/openclaw-workspace-template |
| memsearch 独立库 | https://milvus.io/blog/we-extracted-openclaws-memory-system-and-opensourced-it-memsearch.md |
| SOUL.md 工具 | https://github.com/aaronjmars/soul.md |

---

## 🔨 命令速查

### 常用命令

```bash
# 进入工作环境
mae                                  # 自定义 alias

# 启动 orchestrator
python main.py

# 后台启动（tmux）
tmux new -s mae
python main.py
# Ctrl+B 然后 D 脱离

# 查看飞书消息日志
tail -f orchestrator.log

# 验证各组件
python test_minimal.py               # 测试单 executor
claude --version                     # Claude Code
claude auth status                   # 认证状态
claude doctor                        # 健康检查
```

### 调试技巧

```bash
# 看 Airtable 响应
python -c "from tools.airtable import fetch_pending_tasks; print(fetch_pending_tasks())"

# 看飞书 token 能否获取
python -c "from tools.feishu import get_bot_token; print(get_bot_token('MAE-PM')[:20])"

# 测单步显影
python -c "
from display import post_task_header
from executors.base import Task
t = Task(id='debug', type='test', content='测试显影')
print(post_task_header(t))
"
```

---

## 📖 延伸阅读

### Claude Code 源码泄漏分析（有参考价值）

| 资源 | 链接 |
|------|------|
| San Francisco Today 报道 | https://nationaltoday.com/us/ca/san-francisco/news/2026/04/12/y-combinator-chief-reveals-productivity-secret-harness-over-raw-coding/ |
| HackerNews 讨论 | https://news.ycombinator.com/item?id=47418576 |

### Context Engineering 基础

| 资源 | 链接 |
|------|------|
| Prompt Engineering Overview | https://docs.claude.com/en/docs/build-with-claude/prompt-engineering/overview |
| Claude Agent SDK | https://www.anthropic.com/engineering/building-agents-with-the-claude-agent-sdk |

---

## 🧰 可选增强工具

- **ngrok**：如果需要公网 webhook（飞书事件订阅），但 WebSocket 模式不需要
- **n8n**：如果未来要做可视化工作流编排
- **Grafana + Prometheus**：监控 orchestrator 运行状态
- **Sentry**：错误追踪

这些都**不是 MVP 必需**。到 M3 之后根据实际需要再考虑。
