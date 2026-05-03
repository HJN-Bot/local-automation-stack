# 13 · 两天作战计划

> Mac Mini 到手的 48 小时作战手册
> 唯一目标：跑通 MAE 核心闭环 + 落地第一个日常 agent（信息自动化收集）

---

## ⚠️ 开战前的心态校准

读完这 3 条再开始：

1. **今天不是"搭架构日"，是"跑通第一条任务日"**。任何"让我先整理一下"的念头都是陷阱。

2. **今天不装 Hermes / Codex CLI / OpenClaw 新框架**。Day 1 只用 Claude API，Day 2 才加 Claude Code CLI。其他延后。

3. **失败比完美更有价值**。飞书里出现一条显影消息（哪怕格式丑、哪怕一步就完成），比一个写得很完美但没跑起来的 orchestrator 强 100 倍。

---

## 📅 Day 1 (4.24) · 跑通最小闭环

### 当日唯一成功标准

**在飞书群里看到一条完整的显影流**：

```
🚀 [Task #xxx] research: 用三句话解释什么是多 agent 系统
  → 准备调用: 模型 claude-opus-4-5
  → API 返回: In 150 / Out 200 tokens
  → 完成: 已写入 outputs/xxx.md
✅ 完成（耗时 6.2s）
```

达到这条，Day 1 就成功。

---

### ⏰ 时间表

#### 上午 · 环境搭建（2-3 小时）

**09:00-09:30 · 系统与工具**

```bash
# 开机、连 Wi-Fi、登录 Apple ID

# Xcode CLI tools
xcode-select --install

# Homebrew (M 系列芯片)
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
echo 'eval "$(/opt/homebrew/bin/brew shellenv)"' >> ~/.zprofile
eval "$(/opt/homebrew/bin/brew shellenv)"

# 装工具
brew install git python@3.12 node tmux ripgrep jq

# nvm + Node
curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.39.7/install.sh | bash
source ~/.zshrc
nvm install --lts
```

**09:30-10:00 · Claude Code CLI**

```bash
npm install -g @anthropic-ai/claude-code
claude  # 首次登录
claude -p "What is 1+1?" --max-turns 1  # 验证
```

**10:00-10:30 · SSH + GitHub**

```bash
# 生成 SSH key
ssh-keygen -t ed25519 -C "jianan@macmini"
cat ~/.ssh/id_ed25519.pub
# 复制到 GitHub → Settings → SSH Keys

# Clone 项目
mkdir -p ~/Projects && cd ~/Projects
git clone git@github.com:HJN-Bot/local-automation-stack.git
cd local-automation-stack
```

**10:30-11:30 · MAE Design 文档就位 + Python 环境**

```bash
# 把这次 claude.ai 生成的 13 份文档放进 "MAE Design/"
# 如果旧 MAE Design 存在，先重命名为 MAE Design.backup-<date>，再 mv 进 90-archive/

mkdir -p mae-orchestrator && cd mae-orchestrator
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install anthropic requests python-dotenv pyairtable
pip freeze > requirements.txt

# 加 alias
echo 'alias mae="cd ~/Projects/local-automation-stack/mae-orchestrator && source venv/bin/activate"' >> ~/.zshrc
source ~/.zshrc
```

**11:30-12:30 · 配置 .env（最容易卡住的一步）**

```bash
# 创建 .env
cat > .env << 'EOF'
ANTHROPIC_API_KEY=sk-ant-...
AIRTABLE_API_KEY=pat...
AIRTABLE_BASE_ID=app...
AIRTABLE_TABLE_NAME=Tasks
FEISHU_GROUP_ID=oc_...
FEISHU_PM_APP_ID=cli_...
FEISHU_PM_APP_SECRET=...
FEISHU_CLAUDE_APP_ID=cli_...
FEISHU_CLAUDE_APP_SECRET=...
EOF

# .gitignore
cat >> ../.gitignore << 'EOF'
.env
venv/
__pycache__/
*.pyc
outputs/
logs/
data/
.DS_Store
EOF
```

**卡点预警**：如果飞书 bot 没提前创建，现在至少要创建 2 个（MAE-PM + Claude-Reasoner），剩下 3 个 Day 2 再说。

**12:30-13:30 · 午饭 + 缓冲**

---

#### 下午 · Day 1 代码（3-4 小时）

**13:30-15:00 · 最小代码骨架**

按 `05-orchestrator-implementation.md` 创建：
- `executors/base.py` (25 行)
- `tools/llm.py` (30 行，只要 call_claude 函数)
- `tools/feishu.py` (55 行)
- `executors/claude_api.py` (20 行)
- `display.py` (25 行)

**不做什么**（重要）：
- 不做 router.py
- 不做 DeepSeek executor
- 不做 Claude Code executor
- 不做 airtable.py
- 不做 core.py 主循环

**15:00-16:00 · 手动测试（不接 Airtable）**

```bash
cd ~/Projects/local-automation-stack/mae-orchestrator

cat > test_day1.py << 'EOF'
"""Day 1 最小测试：手动构造任务 → 调 executor → 飞书显影"""
from dotenv import load_dotenv
load_dotenv()

import time, os
from executors.claude_api import ClaudeAPIExecutor
from executors.base import Task
from display import post_task_header, post_step, post_task_done

task = Task(
    id="test-day1-001",
    type="research",
    content="用三句话解释什么是多 agent 系统",
    context={}
)

start = time.time()
thread_id = post_task_header(task)
print(f"✅ 飞书主消息已发送，thread_id={thread_id}")

executor = ClaudeAPIExecutor()
for step in executor.execute(task):
    print(f"[{step.action}] {step.summary}")
    post_step(thread_id, executor, step)

post_task_done(thread_id, task, time.time() - start)
print("✅ Day 1 完成！")
EOF

python test_day1.py
```

**🎯 成功判定**：飞书群里看到主消息 + 回复步骤 + 完成消息。

**如果卡住**：看 `04-checklist.md` 的"常见问题"，或者把报错贴到 claude.ai 问。

---

#### 晚上 · Airtable 集成（2 小时）

**19:00-20:30 · Airtable + 主循环**

1. 在 Airtable 建 "Tasks" base（按 04 文档的 schema）
2. 实现 `tools/airtable.py`（45 行）
3. 实现 `core.py` + `main.py`（50 行）

**20:30-21:30 · 端到端验证**

```bash
# 启动 orchestrator
python main.py

# 另开一个终端 / 在 Airtable 里新建一条任务（Status=pending）
# 回到原终端看 log
# 30 秒内应该被取到，飞书群应该出现消息
```

**🎯 Day 1 最终成功判定**：
- ✅ Airtable 新建一条任务
- ✅ 不用做任何操作
- ✅ 飞书群自动出现完整显影流
- ✅ 任务执行完，Airtable 状态自动变成 done

---

#### 睡前 · 今日复盘（10 分钟）

打开 `07-todos-and-milestones.md`，勾掉完成的项。

记录一下踩过的坑（为明天、为未来的你）。

**今晚不做自启动配置**。手动跑是对的——你需要亲眼看到它跑起来，才敢让它后台跑。

---

## 📅 Day 2 (4.25) · 多 Executor + 第一个日常 Agent

### 上午 · 扩展执行层（3 小时）

#### 09:00-10:00 · 加 DeepSeek Executor + Router

**为什么加 DeepSeek**：不是为了省钱（还早），是为了**验证 router 分流能力**——这是你架构的核心卖点之一。

按 `05-orchestrator-implementation.md` 的代码：
- `tools/llm.py` 加 `call_deepseek` 函数
- 新建 `executors/deepseek_api.py`
- 新建 `router.py`

测试：在 Airtable 建两条任务，一条 type=research（走 Claude），一条 type=classify（走 DeepSeek），看飞书里是不是两个不同 bot 在汇报。

#### 10:00-11:00 · 加 Claude Code Executor

新建 `executors/claude_code.py`，关键是 `subprocess.run(["claude", "-p", ...])`。

测试：在 Airtable 建一条 type=code 的任务（比如"列出当前目录所有 Python 文件"），看 Claude-Code bot 是不是在汇报。

#### 11:00-12:00 · 多 Bot 身份显影

创建剩下 3 个飞书 bot：DeepSeek-Router / Claude-Code / Research-Agent。

更新 `tools/feishu.py` 的 bot token 映射。

最终效果：飞书群里 5 个不同头像的 bot 协作。

#### 🎯 上午成功判定

飞书群里跑一遍：
- research 任务 → Claude-Reasoner bot 汇报
- code 任务 → Claude-Code bot 汇报
- classify 任务 → DeepSeek-Router bot 汇报
- PM bot 始终发主消息和完成消息

---

### 下午 · 第一个日常 Agent：信息自动化收集（4 小时）

这是你的**第一个真实业务 agent**，为后续所有能力打样。

#### 业务目标

每天自动帮你完成：
- 抓取你关注的信息源（RSS / Twitter / 微信公众号 / 小红书话题）
- 去重 + 打分（基于你历史感兴趣的内容）
- 每晚 23:00 输出一份"今日必读"（5-10 条）
- 推送到飞书"每日情报"子群

#### 14:00-14:30 · 需求收敛

别想"做一个完美的信息收集系统"。**今天只做 1 个信息源 + 1 种输出格式**。

**今天的最小化版本**：

| 维度 | 今天做的 | 推迟的 |
|------|--------|------|
| 信息源 | 1 个：你订阅的 RSS（如 Readwise Reader） | Twitter / 微信 / 小红书 |
| 处理 | 去重 + 调模型打分 | ML 个性化推荐 |
| 输出 | 飞书一条卡片消息 | 多格式 / 多平台 |
| 触发 | 手动（在 Airtable 建任务） | cron 定时 |

#### 14:30-15:30 · 加 fetch_rss 工具

新建 `tools/rss.py`：

```python
"""RSS 抓取工具"""
import feedparser
from datetime import datetime, timedelta


def fetch_rss(feed_url: str, hours: int = 24) -> list[dict]:
    """抓取 RSS feed 最近 N 小时内的文章"""
    feed = feedparser.parse(feed_url)
    cutoff = datetime.now() - timedelta(hours=hours)
    
    articles = []
    for entry in feed.entries:
        # 解析发布时间
        pub_time = None
        if hasattr(entry, "published_parsed"):
            pub_time = datetime(*entry.published_parsed[:6])
        
        if pub_time and pub_time < cutoff:
            continue
        
        articles.append({
            "title": entry.get("title", ""),
            "url": entry.get("link", ""),
            "summary": entry.get("summary", "")[:500],
            "published": pub_time.isoformat() if pub_time else None,
        })
    
    return articles
```

装依赖：
```bash
pip install feedparser
```

#### 15:30-16:30 · 加 daily-digest skill

这是你**第一个真正意义上的 fat skill**。

新建 `skills/daily-digest.md`：

```markdown
---
name: daily-digest
description: 从 RSS 源抓取最近 24 小时文章，打分后生成"今日必读"摘要
parameters:
  - name: feed_url
    required: true
    type: string
  - name: top_n
    required: false
    type: int
    default: 5
tools:
  - tools.rss.fetch_rss
---

# Daily Digest

## 执行流程

1. **抓取**（deterministic）：`tools.rss.fetch_rss(feed_url, hours=24)`
2. **去重**（deterministic）：按 title 去重
3. **打分**（latent）：对每篇文章打 1-10 分，基于：
   - 信息密度（是观点还是新闻）
   - 与 AI / agent / 创业 / 产品话题的相关度
   - 标题的信息量（标题党扣分）
4. **排序**（deterministic）：按分数降序取 top_n
5. **摘要**（latent）：给每篇写 2 句话的本质提炼（不是原文摘要，是"为什么值得看"）

## 输出格式

```markdown
# 今日必读 ({date})

## 1. {title}
- 评分: {score}/10
- 为什么看: {2 句提炼}
- 链接: {url}

## 2. ...
```
```

#### 16:30-17:30 · 新建 DigestExecutor

新建 `executors/digest_executor.py`：

```python
"""专门处理 daily-digest 类任务的 executor"""
from .base import Task, Step
from tools.rss import fetch_rss
from tools.llm import call_claude
from pathlib import Path


class DigestExecutor:
    bot_name = "Research-Agent"
    
    def execute(self, task: Task):
        feed_url = task.context.get("feed_url")
        if not feed_url:
            raise ValueError("缺少 feed_url")
        
        top_n = task.context.get("top_n", 5)
        
        # Step 1: 抓取
        yield Step("抓取 RSS", f"源: {feed_url}")
        articles = fetch_rss(feed_url, hours=24)
        yield Step("抓取完成", f"共 {len(articles)} 篇文章")
        
        if not articles:
            yield Step("无新文章", "今天没有新内容")
            return
        
        # Step 2: 去重
        seen_titles = set()
        unique = []
        for a in articles:
            if a["title"] not in seen_titles:
                seen_titles.add(a["title"])
                unique.append(a)
        yield Step("去重", f"去重后 {len(unique)} 篇")
        
        # Step 3: 加载 skill + 打分 + 摘要（让 Claude 一次性做完）
        skill_content = Path("skills/daily-digest.md").read_text(encoding="utf-8")
        
        articles_text = "\n\n".join([
            f"### {i+1}. {a['title']}\n{a['summary']}\n链接: {a['url']}"
            for i, a in enumerate(unique)
        ])
        
        prompt = f"""
{skill_content}

---

# 今天的文章

{articles_text}

请按 skill 定义的流程：打分 → 排序 → 选 top {top_n} → 写 2 句本质提炼。

直接输出最终格式的 markdown，不要任何解释。
"""
        
        yield Step("调用模型", f"准备打分和摘要 {len(unique)} 篇")
        text, usage = call_claude(prompt, max_tokens=2048)
        yield Step("模型返回", f"用了 {usage['output_tokens']} tokens")
        
        # Step 4: 写文件
        output_path = f"outputs/digest-{task.id}.md"
        Path(output_path).parent.mkdir(exist_ok=True)
        Path(output_path).write_text(text, encoding="utf-8")
        
        yield Step("完成", f"已写入 {output_path}")
```

#### 17:30-18:00 · Router 加 digest 分流

修改 `router.py`：

```python
from executors.digest_executor import DigestExecutor

def choose_executor(task):
    t = task.type.lower()
    
    # 新增：信息摘要
    if t == "digest":
        return _get("digest", DigestExecutor)
    
    # ... 原有逻辑
```

#### 18:00-18:30 · 端到端测试

在 Airtable 建一条任务：
- Task Type: `digest`
- Content: `抓取今日 RSS 生成摘要`
- 需要新加一个字段 `FeedURL`（或者放在 Content 里）

Executor 会从 `task.context` 读 feed_url——你的 Airtable 字段会自动进 context 字典。

**🎯 Day 2 下午成功判定**：
- 飞书里看到 Research-Agent bot 汇报完整流程
- outputs/ 里生成一份结构化的"今日必读"
- 你真的觉得有用（不是凑数，是真能节省时间）

---

### 晚上 · 轻度 Review + 庆祝（1-2 小时）

#### 21:00-21:30 · 两日复盘

打开 `09-postmortem.md`，对照你之前"跑不通"的 5 个根因：

| 根因 | 是否已解决 |
|------|----------|
| 没 Runtime | ✅ Python orchestrator 在跑 |
| Skill 不可执行 | ✅ daily-digest.md 被 executor 加载 |
| Latent/Deterministic 错配 | ✅ 抓取/去重是 deterministic，打分/摘要是 latent |
| Context 必爆 | ✅ 每个任务独立 context，不累积 |
| 不可见 | ✅ 飞书有完整显影 |

5 个根因全部被堵上 —— **这不是小胜利，这是项目的里程碑**。

#### 21:30-22:00 · 配自启动

**这时候才配**，因为你已经亲眼确认它能跑稳。

```bash
mkdir -p ~/Library/LaunchAgents
# 按 13-two-day-battle-plan.md 的模板创建 plist
launchctl load ~/Library/LaunchAgents/com.jianan.mae.plist
```

从现在开始，Mac Mini 开机就自动启动 orchestrator。

#### 22:00-23:00 · 写一条庆祝消息

发一条 X / 朋友圈 / 飞书：

> "今天（4.25）跑通了自己的多 agent 系统。Airtable 建任务 → Python orchestrator 调度 → 5 个飞书 bot 协作 → 输出到 outputs。明天开始真正的日常使用。"

**不要晒代码，只说**结果。这是你从"观众"变成"玩家"的分水岭时刻，值得标记。

---

## 📋 Day 3+ 的自然延伸（不在本计划内）

Day 2 结束后，下一周你会自然遇到这些事：

| 事情 | 什么时候做 | 对应文档 |
|------|---------|---------|
| 加 cron 定时触发 digest | 第 3 天 | 自己想 |
| 加更多信息源（Twitter / 公众号） | 第 5 天 | 06-skill 指南 |
| 加错误处理 + 资源 Guard | 第 1 周末 | 10 + 11 |
| 写 PPT skill 集成 | 第 2 周 | 06-skill 指南 |
| 开始写第一篇技术文章 | 第 3 周 | 12-roi 路径 3 |

**不要提前做**。每件事都等你**真的遇到需要它的时候**再做。

---

## 🚨 最容易犯的 5 个错误（避坑）

**1. Day 1 上午想把所有 executor 都写了**
→ 只写 Claude API。其他 Day 2。

**2. Day 1 就想做 router**
→ Day 1 只有 1 个 executor，不需要 router。

**3. 飞书 bot 没创建好就开工**
→ 至少 2 个（PM + Claude-Reasoner）先到位。

**4. Day 2 想同时做多个日常 agent**
→ 只做 digest 一个。其他推迟。

**5. 跑通后立刻优化**
→ 跑通后先用 1 周，让真实问题自己浮现，再针对性优化。

---

## ✅ 48 小时结束时的终态

- [ ] Mac Mini 自启动 orchestrator
- [ ] Airtable 建任务 → 飞书自动显影（5 种 bot 协作）
- [ ] 第一个真实业务 agent（daily-digest）能用
- [ ] 13 份 MAE Design 文档都在 repo 里
- [ ] 你自己真的觉得"这系统在帮我"

**达到以上 5 条，项目就从"构想"正式变成"运行中"**。

这比任何完美的架构文档都重要。
