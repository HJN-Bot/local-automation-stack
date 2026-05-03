# 04 · Mac Mini Day 0 Checklist

> **Mac Mini 到手当天打开这个文件，从 Phase 0 顺序执行到 Phase 7。**
> 不需要读其他文档。遇到架构疑问再回看 01/02/03。

---

## ⏱️ 时间规划

| 阶段 | 时长 | 目标 |
|------|------|------|
| Phase 0 | 30min | 系统环境就绪 |
| Phase 1 | 10min | Repo 拉到本地 |
| Phase 2 | 10min | Python 环境 |
| Phase 3 | 5min | Claude Code CLI |
| Phase 4 | 20min | 环境变量配置 |
| Phase 5 | 2h | Day 1 闭环（单 executor） |
| Phase 6 | 1天 | Day 2-3 Airtable + 多 executor |
| Phase 7 | 2天 | Day 4-7 多 bot + 端到端 |

**Day 0 当天目标**：完成 Phase 0 到 Phase 5，跑通第一个最小闭环。

---

## 🟢 Phase 0：系统环境（~30min）

### 0.1 系统基础

```bash
# macOS 更新
softwareupdate -ia

# Xcode Command Line Tools
xcode-select --install

# Homebrew
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# 验证
brew --version
```

### 0.2 开发工具

```bash
# Git + Python + Node
brew install git python@3.12 node

# 终端增强（可选但强烈推荐）
brew install tmux fzf ripgrep jq

# nvm（管理 Node 版本）
curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.39.7/install.sh | bash
source ~/.zshrc
nvm install --lts
nvm use --lts

# 验证
python3 --version  # 应该 3.12+
node --version     # 应该 v20+
git --version
```

### 0.3 SSH / Remote 准备（可选）

如果计划未来从其他设备 SSH 进 Mac Mini：

```bash
# 开启 Remote Login（系统设置里也能开）
sudo systemsetup -setremotelogin on

# 生成 SSH key（如果还没有）
ssh-keygen -t ed25519 -C "jianan@macmini"

# 添加到 GitHub：把 ~/.ssh/id_ed25519.pub 内容粘贴到 GitHub SSH keys
cat ~/.ssh/id_ed25519.pub
```

---

## 🟢 Phase 1：Repo 初始化（~10min）

```bash
# 创建工作目录
mkdir -p ~/Projects && cd ~/Projects

# Clone 主 repo
git clone https://github.com/HJN-Bot/local-automation-stack.git
cd local-automation-stack

# 验证能看到 MAE Design 文件夹
ls -la "MAE Design/"

# 进入主控台（应该能看到 README）
cat "MAE Design/README.md"
```

---

## 🟢 Phase 2：Python 环境（~10min）

```bash
cd ~/Projects/local-automation-stack

# 创建 orchestrator 子目录
mkdir -p mae-orchestrator && cd mae-orchestrator

# 创建虚拟环境
python3 -m venv venv
source venv/bin/activate

# 升级 pip
pip install --upgrade pip

# 安装依赖
pip install anthropic requests python-dotenv pyairtable

# 保存依赖清单
pip freeze > requirements.txt

# 确认环境激活
which python  # 应该指向 venv/bin/python
```

**建议**：在 `~/.zshrc` 加个 alias 方便后续激活：
```bash
echo 'alias mae="cd ~/Projects/local-automation-stack/mae-orchestrator && source venv/bin/activate"' >> ~/.zshrc
source ~/.zshrc
```

以后每次打开终端，敲 `mae` 就自动进目录并激活 venv。

---

## 🟢 Phase 3：Claude Code CLI（~5min）

```bash
# 全局安装
npm install -g @anthropic-ai/claude-code

# 验证
claude --version

# 首次使用需要认证
claude
# 会打开浏览器登录，或用 API key
# 登录后输入 /quit 退出

# 测试 print 模式（被 orchestrator 调用时用这个）
claude -p "What is 2+2? Answer in one word." --max-turns 1
# 应该返回 "4" 或类似简短答案
```

---

## 🟢 Phase 4：环境变量配置（~20min）

### 4.1 创建 .env 文件

```bash
cd ~/Projects/local-automation-stack/mae-orchestrator

cat > .env << 'EOF'
# ===== 模型 API =====
ANTHROPIC_API_KEY=sk-ant-...
DEEPSEEK_API_KEY=sk-...
# OPENROUTER_API_KEY=sk-or-...  # 可选，用于统一网关

# ===== Airtable =====
AIRTABLE_API_KEY=pat...
AIRTABLE_BASE_ID=app...
AIRTABLE_TABLE_NAME=Tasks

# ===== 飞书 - 群 =====
FEISHU_GROUP_ID=oc_...

# ===== 飞书 - Bot 身份 =====
# PM Bot（发任务主消息）
FEISHU_PM_APP_ID=cli_...
FEISHU_PM_APP_SECRET=...

# Claude Reasoner Bot
FEISHU_CLAUDE_APP_ID=cli_...
FEISHU_CLAUDE_APP_SECRET=...

# DeepSeek Bot
FEISHU_DEEPSEEK_APP_ID=cli_...
FEISHU_DEEPSEEK_APP_SECRET=...

# Claude Code Bot
FEISHU_CC_APP_ID=cli_...
FEISHU_CC_APP_SECRET=...

# Research Bot（可选）
FEISHU_RESEARCH_APP_ID=cli_...
FEISHU_RESEARCH_APP_SECRET=...
EOF

# 立即加到 .gitignore
cat >> ../.gitignore << 'EOF'
.env
venv/
__pycache__/
*.pyc
outputs/
.DS_Store
EOF
```

### 4.2 获取所需的 Keys（在别的设备上也可以提前做）

| Key | 来源 | 备注 |
|-----|------|------|
| ANTHROPIC_API_KEY | https://console.anthropic.com | 充 $20 够 MVP |
| DEEPSEEK_API_KEY | https://platform.deepseek.com | 可选，用于便宜调度 |
| AIRTABLE_API_KEY | https://airtable.com/create/tokens | 需要 read+write 权限 |
| AIRTABLE_BASE_ID | 你的 Tasks base URL | `airtable.com/appXXX/...` |
| FEISHU_* | https://open.feishu.cn | 5 个 bot 各一套 |

### 4.3 飞书 Bot 创建（每个重复一次）

1. 访问 https://open.feishu.cn
2. 创建企业自建应用（共 5 个）
3. 每个 bot 设置独立头像、名字
4. 在"权限管理"里开启：
   - `im:message`（发消息）
   - `im:chat`（群管理）
5. 把 bot 添加到你的 MAE Workspace 群
6. 复制 App ID 和 App Secret 到 `.env`

---

## 🟢 Phase 5：Day 1 最小闭环（~2h）

**目标**：跑通单 executor（Claude API）的显影闭环，不接 Airtable。

### 5.1 创建目录结构

```bash
cd ~/Projects/local-automation-stack/mae-orchestrator

mkdir -p executors skills tools outputs

touch executors/__init__.py tools/__init__.py
```

### 5.2 复制 `05-orchestrator-implementation.md` 里的代码

按那份文档里的示例创建以下文件：
- `executors/base.py`
- `executors/claude_api.py`
- `tools/feishu.py`
- `tools/llm.py`
- `display.py`
- `core.py`
- `main.py`

详见 `05-orchestrator-implementation.md`。

### 5.3 手动测试（不走 Airtable）

创建 `test_minimal.py`：

```python
from executors.claude_api import ClaudeAPIExecutor
from executors.base import Task
from display import post_task_header, post_step, post_task_done
from dotenv import load_dotenv
import os, time

load_dotenv()

# 构造一个测试任务
task = Task(
    id="test-001",
    type="research",
    content="用三句话解释什么是多 agent 系统",
    context={}
)

# 执行 + 显影
start = time.time()
thread_id = post_task_header(task)

executor = ClaudeAPIExecutor(os.getenv("ANTHROPIC_API_KEY"))
for step in executor.execute(task):
    print(f"[{step.action}] {step.summary}")
    post_step(thread_id, executor, step)

post_task_done(thread_id, task, time.time() - start)
print("✅ Done")
```

运行：
```bash
python test_minimal.py
```

**验收**：
- 终端打印出每个 Step
- 飞书群里能看到任务主消息 + 步骤回复 + 完成消息
- Claude Reasoner bot 头像出现在回复里

---

## 🟡 Phase 6：Day 2-3 Airtable 集成（~1 天）

**目标**：从 Airtable 自动取任务，完成后写回状态。

### 6.1 Airtable Schema 准备

你的 Tasks 表需要以下字段：

| 字段名 | 类型 | 说明 |
|-------|------|------|
| ID | Auto Number | 主键 |
| Task Type | Single Select | research / code / classify / review |
| Content | Long Text | 任务描述 |
| Status | Single Select | pending / running / done / failed |
| Result | Long Text | 执行结果（执行后写入） |
| Error | Long Text | 失败原因（失败时写入） |
| Created | Created Time | 自动 |
| Updated | Last Modified Time | 自动 |

### 6.2 实现 `tools/airtable.py`

详见 `05-orchestrator-implementation.md`。核心方法：
- `fetch_pending_tasks()` → 查 Status=pending 的记录
- `mark_running(task_id)` → 更新状态
- `mark_done(task_id, result)` → 写回结果
- `mark_failed(task_id, error)` → 写回错误

### 6.3 主循环改成 Airtable 驱动

修改 `core.py`，让主循环从 Airtable 读任务而非硬编码。

### 6.4 端到端验证

在 Airtable 里新建一条 Status=pending 的记录，启动 orchestrator：

```bash
python main.py
```

**验收**：
- 记录自动被取到
- 飞书显影流完整
- Airtable 状态更新为 done

---

## 🟡 Phase 7：Day 4-7 多 Executor + 完整身份（~2 天）

### 7.1 加 DeepSeek Executor（Day 4）

实现 `executors/deepseek_api.py`，用于便宜的分类/调度任务。

### 7.2 加 Claude Code Executor（Day 5）

实现 `executors/claude_code.py`，通过 `subprocess` 调用 `claude -p`。

### 7.3 Router 路由逻辑（Day 5）

实现 `router.py`，根据 `task.type` 分发：
- `code` / `debug` / `refactor` → Claude Code
- `classify` / `route` / `summary` → DeepSeek
- `research` / `analysis` / `write` → Claude API

### 7.4 多 Bot 身份（Day 6）

`display.py` 按 `executor.bot_name` 切换飞书 token。

### 7.5 真实任务端到端（Day 7）

在 Airtable 录一个真实任务（如"写本周 MAE 进展周报"），完整跑一遍。

---

## 🔴 Phase 8+：扩展能力（2 周后再考虑）

- Skills 层：写第一个 `.md` skill 文件，Executor 加载它
- 记忆同步：每日 session 摘要 → 文件
- Cron 调度：定时任务（如每天早上自动跑周报草稿）
- Resolver：基于 skill description 的 latent 路由

---

## 🌐 Phase 9：Mac Mini 接入方式（M1 跑通后配）

Mac Mini 放在家里 7×24 跑，你不会一直坐在它前面。怎么接入它？三种模式。

### 模式 A：SSH 远程（日常用）

```bash
# 在 Mac Mini 上开启 SSH
sudo systemsetup -setremotelogin on

# 查局域网 IP
ipconfig getifaddr en0   # 有线
ipconfig getifaddr en1   # 无线

# 从主力电脑/手机
ssh jianan@<mac-mini-ip>
mae    # 自动进目录 + 激活 venv
tail -f orchestrator.log
```

**外网访问**（推荐 Tailscale）：

```bash
# Mac Mini 上
brew install --cask tailscale
# 打开 Tailscale 登录（Google 账号一键登录）

# 主力电脑/手机同样登录
# 之后 Tailscale 会分配一个固定 IP（100.x.x.x），从任何网络都能 SSH 进来
ssh jianan@<tailscale-ip>
```

### 模式 B：VS Code Remote（写代码时用）

主力电脑的 VS Code 装 "Remote - SSH" 插件 → 连 `jianan@<mac-mini-ip>` → 像本地一样编辑远端代码。

**强烈推荐**：比直接 SSH 用 vim/nano 效率高 10 倍。

### 模式 C：飞书群（日常 90% 时间）

**这才是 MAE 的真正 UI**：
- 你在手机 Airtable 建任务
- Mac Mini 后台跑
- 飞书群里看结果

你不需要"操作 Mac Mini"，你和 Mac Mini 的唯一接口就是飞书群。

**日常 90% 时间用模式 C，只有部署代码和 debug 时才用 A/B。**

---

## 🚀 Phase 10：开机自启动（M1 跑通后配）

**重要**：这一步**必须在 Day 1/Day 2 跑通后**才做。原因：你需要先亲眼确认它能跑稳，才敢让它后台跑。

### 创建 LaunchAgent

```bash
mkdir -p ~/Library/LaunchAgents
mkdir -p ~/Projects/local-automation-stack/mae-orchestrator/logs

# 替换 {jianan} 为你的实际用户名
USER_NAME=$(whoami)

cat > ~/Library/LaunchAgents/com.jianan.mae.plist << EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.jianan.mae</string>
    <key>ProgramArguments</key>
    <array>
        <string>/Users/$USER_NAME/Projects/local-automation-stack/mae-orchestrator/venv/bin/python</string>
        <string>/Users/$USER_NAME/Projects/local-automation-stack/mae-orchestrator/main.py</string>
    </array>
    <key>WorkingDirectory</key>
    <string>/Users/$USER_NAME/Projects/local-automation-stack/mae-orchestrator</string>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <true/>
    <key>StandardOutPath</key>
    <string>/Users/$USER_NAME/Projects/local-automation-stack/mae-orchestrator/logs/orchestrator.log</string>
    <key>StandardErrorPath</key>
    <string>/Users/$USER_NAME/Projects/local-automation-stack/mae-orchestrator/logs/orchestrator.err</string>
    <key>EnvironmentVariables</key>
    <dict>
        <key>PATH</key>
        <string>/usr/local/bin:/usr/bin:/bin:/opt/homebrew/bin</string>
    </dict>
</dict>
</plist>
EOF
```

### 常用命令

```bash
# 启动（第一次加载）
launchctl load ~/Library/LaunchAgents/com.jianan.mae.plist

# 停止
launchctl unload ~/Library/LaunchAgents/com.jianan.mae.plist

# 查看状态
launchctl list | grep mae

# 实时查看日志
tail -f ~/Projects/local-automation-stack/mae-orchestrator/logs/orchestrator.log

# 看错误
tail -f ~/Projects/local-automation-stack/mae-orchestrator/logs/orchestrator.err
```

### 系统电源设置（防休眠）

打开"系统设置"：
- **显示器** → 进入睡眠 → "永不"
- **电池**（笔记本才有）→ 当显示器关闭时防止自动睡眠 ✓
- **登录项** → 可选加入 Tailscale 自启动

这样 Mac Mini 合上盖子也不会让 orchestrator 停。

### 验证自启动

重启 Mac Mini：
```bash
sudo reboot
```

等它重启完，不手动登录、不打开终端，直接去 Airtable 建一条任务。30 秒内飞书应该出现显影——说明自启动成功。

---

## 🆘 常见问题

**Q1: 飞书 API 调用 403？**
→ 检查 bot 是否真的加到了群里；权限里是否开启了 `im:message`

**Q2: Claude Code CLI 卡住不动？**
→ 用 `--verbose` 看日志：`claude -p "..." --verbose`；首次调用需要认证

**Q3: Airtable 取不到任务？**
→ 检查字段名是否完全一致（大小写敏感）；检查 token 是否有 write 权限

**Q4: Orchestrator 卡死或重复执行？**
→ 先改状态为 running 再执行；加上 try/finally 保证状态收尾

**Q5: 显影消息顺序错乱？**
→ 飞书 API 调用是异步的，需要在 `post_step` 里加 `thread_id` 确保都回复到主消息下

---

## 🎯 Day 0 当晚的成功指标

完成以下 3 条即可睡觉：

1. ✅ `claude -p "hello"` 能正常返回
2. ✅ `python test_minimal.py` 能看到飞书显影流
3. ✅ README + 5 个核心文档在 `~/Projects/local-automation-stack/MAE Design/` 可见

其余的留给后续几天慢慢推进。别急，架构已经想清楚了，现在是把代码跑起来的阶段。
