# 🎯 NOW.md · Day 2 作战指挥

> 每次打开项目第一眼看这里。跑完即更新，不留历史版本。

---

## 📅 当前时间窗

**2026-04-25 · Mac Mini 到手第 2 天**

---

## ✅ Day 1 已完成

| 成果 | 说明 |
|------|------|
| Python 3.12 + venv | 依赖全装好 |
| Repo 初始化 | `~/Projects/local-automation-stack/` |
| DeepSeek V3 接通 | 阿里云 DashScope |
| 飞书单 bot 显影 | MAE-Workplace 群可见 |
| Airtable Agent Tasks 表 | Status / Task Type / Content / Result / Error |
| 端到端闭环 | Airtable pending → 执行 → 飞书显影 → done |
| main.py 后台运行 | tmux session `mae` 持续轮询 |

---

## 🌙 昨晚讨论沉淀

- **PM 和 Worker 必须视觉分离**：现有 bot 专做 PM（主消息 + 完成），新 bot 专做 Worker（step 回复）
- **Doctor bot 推 Week 1**：先跑真实任务，出现 3+ 故障再设计；Mac Mini 不会以 OpenClaw 同样的方式死
- **main.py 永远不改**：扩展在 executors / tools / skills / router
- **OpenClaw 推 Week 2**：4 channel → 4 fat skill，只取 30% 精华

---

## 🎯 今天的目标

飞书里出现 **3 种不同 bot 头像协作**：
```
🚀 MAE-PM：     [Task #abc] 开始执行
  ↳ DS-Worker：  → 准备调用 deepseek-v3
  ↳ DS-Worker：  → API 返回 84 tokens
✅ MAE-PM：     完成（耗时 8s）

🚀 MAE-PM：          [Task #xyz] code 任务
  ↳ CC-Worker：       → 启动 Claude Code CLI
  ↳ CC-Worker：       → CLI 返回
✅ MAE-PM：          完成
```

---

## ⚠️ 今天的"绝对不做"

1. ❌ 不做 Doctor bot（Week 1）
2. ❌ 不做 OpenClaw 迁移（Week 2）
3. ❌ 不做记忆系统（Week 3+）
4. ❌ 不改 main.py / core.py
5. ❌ 任何"顺便"——写进 `_wishlist.md` 然后关掉

**纪律**：每件做完验收通过才下一件。卡住了停下来，不硬往后走。

---

## 🛠️ 上午 4 件事（08:30-12:30）

### 事项 1：加 DeepSeek-Worker bot（08:30-09:30）

**目标**：PM 和 Worker 视觉分离

1. 飞书开放平台 → 新建企业自建应用，名 `DS-Worker`，头像和 PM 明显不同
2. 加进 MAE-Workplace 群
3. `.env` 加：
   ```
   FEISHU_WORKER_APP_ID=cli_xxx
   FEISHU_WORKER_APP_SECRET=xxx
   ```
4. `tools/feishu.py`：`_get_token()` 按 bot_name 切换（PM 用旧 key，Worker 用新 key）
5. `display.py`：`post_task_header` / `post_task_done` → PM；`post_step` → Worker
6. `executors/deepseek_api.py`：`bot_name = "DS-Worker"`

**验收**：Airtable 建任务 → 飞书两种头像出现 ✅

---

### 事项 2：基础保护（09:30-10:30）

**目标**：系统能扛住网络抖动和进程崩溃

**2.1 API 重试（`tools/llm.py`）**：指数退避装饰器，最多 3 次
**2.2 自动重启 wrapper**：创建 `run_orchestrator.sh`
```bash
#!/bin/bash
cd ~/Projects/local-automation-stack/mae-orchestrator
source venv/bin/activate
while true; do
  echo "[$(date)] Starting..."
  python main.py
  echo "[$(date)] Exited $?, restart in 5s"
  sleep 5
done
```
**2.3 任务超时**：`core.py` 里 `signal.alarm(600)`，超时 → mark_failed → 飞书报错

**验收**：故意把 API key 改错 → 飞书看到重试 3 次后失败消息；kill main.py → 看到自动重启 ✅

---

### 事项 3：路由层抽象（10:30-11:30）

**目标**：router.py 真正按 task type 分流，加 executor 只需加一行

```python
TYPE_MAP = {
    "research": DeepSeekExecutor,
    "summary":  DeepSeekExecutor,
    "classify": DeepSeekExecutor,
    "write":    DeepSeekExecutor,
    # "code":  ClaudeCodeExecutor,  # 事项 4 加
}
def choose_executor(task):
    cls = TYPE_MAP.get(task.type.lower(), DeepSeekExecutor)
    return _get(cls.__name__, cls)
```

**验收**：4 种 task type 各建一条任务，全部正常执行 ✅

---

### 事项 4：Claude Code executor（11:30-12:30）

**目标**：code 任务走 Claude Code CLI，飞书出现第 3 种头像

1. 飞书再建 1 个 bot：`CC-Worker`（黑色/紫色头像）
2. 写 `executors/claude_code.py`（subprocess 调 `claude -p`）
3. `router.py` TYPE_MAP 加 `"code": ClaudeCodeExecutor`

**验收**：
- Airtable 建 Task Type=code，Content="列出 mae-orchestrator 下所有 .py 文件"
- 飞书出现 CC-Worker 头像 ✅

---

## 📡 下午：第一个真实业务 agent（13:30-18:00）

**目标**：Airtable 建任务"整理今天 AI 领域 3 条新闻"→ 飞书出现完整简报

1. `pip install duckduckgo-search` → `tools/search.py`
2. `skills/daily-digest.md`（搜索关键词 + 整理格式）
3. `executors/research.py`（读 skill → 搜索 → DeepSeek → 显影）
4. 端到端跑一次

---

## 🌆 晚上（19:00-22:00）

- 配 LaunchAgent 开机自启动（见 `MAE Design/04` Phase 10）
- 更新 NOW.md 为 Week 1 指挥
- 发朋友圈/X 庆祝

---

## 📊 今天成功指标

| 指标 | 验收 |
|------|------|
| 飞书 3 种头像协作 | PM + DS-Worker + CC-Worker |
| 系统能自动重启 | kill 进程后自动恢复 |
| 路由按类型分流 | code 任务不走 DeepSeek |
| 第一条真实简报 | AI 新闻 3 条，飞书可读 |

---

## 🔮 未来观察清单（不是现在做）

- **Doctor bot**：等出现 3+ 真实故障后设计
- **Observer bot**：M2 阶段（30 天后）
- **OpenClaw 迁移**：Week 2，4 channel → 4 skill
- **记忆系统**：跑满 50 个真实任务后再想

---

> 创建于 2026-04-25
> 今晚跑完更新为 Week 1 指挥
> 永远放在 repo 根目录
