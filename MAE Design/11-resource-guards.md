# 11 · 资源 Guard 与成本控制

> 防止"agent 跑飞了一晚上烧掉 $200"。
> 这一层不是 MVP 必需，但**必须在 M2 之前补上**——一旦 orchestrator 7×24 跑起来，没有 guard 是真的会出事的。

---

## 一、为什么需要 Guard

**真实场景模拟**：

你在 Airtable 里建了一个研究任务，描述写得不太清楚。Orchestrator 取到任务，路由给 Claude API。

模型读完任务后，开始"自我对话"——它觉得需要更多信息，调一次 web search，处理结果时又判断需要再搜一次，然后又一次，又一次……每次都是合理的"下一步"，但累计下来一个任务跑了 30 步、消耗 200k input tokens、$15。

你以为完了？没有。这条任务卡在那一直没成功，retry 机制把它**重试了 3 次**。一晚上 $60 烧掉，飞书也被 30×3 = 90 条显影消息刷屏。

**这就是为什么需要 guard。** Agent 系统的危险性在于：每一步的决策都"看起来合理"，但累计效应会失控。

---

## 二、5 层 Guard 设计

从内到外的 5 层防护：

```
┌──────────────────────────────────────────┐
│ Layer 5: 全局开关（紧急刹车）              │
│ ENV 变量 / 文件标记 / 飞书命令             │
├──────────────────────────────────────────┤
│ Layer 4: 每日预算                          │
│ 当日累计 Token / 美元超限 → 暂停           │
├──────────────────────────────────────────┤
│ Layer 3: 单任务预算                        │
│ 单任务 Token / Step / 时间超限 → 中断     │
├──────────────────────────────────────────┤
│ Layer 2: 单次 API 调用限制                 │
│ 每次 LLM 调用的 max_tokens 强制设置        │
├──────────────────────────────────────────┤
│ Layer 1: 输入大小限制                      │
│ 任务描述 / 上下文不能超过 N 字              │
└──────────────────────────────────────────┘
```

每层都不能少。Layer 1 是最常见的小漏洞，Layer 5 是最后兜底。

---

## 三、Layer 1：输入限制

最简单也最容易忽略的一层。

```python
# tools/input_guard.py
MAX_TASK_CONTENT_LENGTH = 10000   # 任务描述最长字符数
MAX_CONTEXT_SIZE = 50000           # 整个 task.context 序列化后最大字节


def validate_task_input(task) -> tuple[bool, str]:
    """检查任务输入是否合理"""
    if len(task.content) > MAX_TASK_CONTENT_LENGTH:
        return False, f"任务描述过长 ({len(task.content)} > {MAX_TASK_CONTENT_LENGTH})"
    
    import json
    ctx_size = len(json.dumps(task.context, default=str))
    if ctx_size > MAX_CONTEXT_SIZE:
        return False, f"任务上下文过大 ({ctx_size} > {MAX_CONTEXT_SIZE})"
    
    return True, "ok"
```

在 `core.py` 的 `run_one_task` 开头调一下。不通过的直接 mark failed，根本不进 executor。

---

## 四、Layer 2：单次 API 调用限制

最直接的成本控制：每次调模型时强制 `max_tokens`。

```python
# tools/llm.py（增强）
def call_claude(
    prompt: str,
    model: str = "claude-opus-4-5",
    max_tokens: int = 4096,
) -> tuple[str, dict]:
    # 关键：max_tokens 强制不超过 8192
    max_tokens = min(max_tokens, 8192)
    
    # 输入也要限制
    if len(prompt) > 100000:
        raise ValueError(f"Prompt too long: {len(prompt)} chars")
    
    # ... 调用
```

**经验值**：
- DeepSeek/Gemini Flash：max_tokens 2048 够 95% 场景
- Claude Sonnet：max_tokens 4096
- Claude Opus：max_tokens 8192（贵，要克制）

---

## 五、Layer 3：单任务预算（最重要）

每个任务在执行前定一个**总预算**，运行时持续跟踪，超限立刻中断。

```python
# tools/task_budget.py
import time
from dataclasses import dataclass, field


@dataclass
class TaskBudget:
    """单任务预算"""
    max_tokens: int = 100000          # 单任务最多 100k tokens
    max_steps: int = 50                # 最多 yield 50 步
    max_duration_sec: int = 600       # 最多跑 10 分钟
    max_cost_usd: float = 1.0         # 最多花 $1
    
    # 运行时累计
    used_tokens: int = 0
    used_steps: int = 0
    used_cost: float = 0.0
    started_at: float = field(default_factory=time.time)
    
    def add_usage(self, tokens: int, cost: float):
        self.used_tokens += tokens
        self.used_cost += cost
    
    def add_step(self):
        self.used_steps += 1
    
    def check(self) -> tuple[bool, str]:
        """检查是否超限"""
        if self.used_tokens > self.max_tokens:
            return False, f"Token 超限: {self.used_tokens} > {self.max_tokens}"
        
        if self.used_steps > self.max_steps:
            return False, f"步数超限: {self.used_steps} > {self.max_steps}"
        
        elapsed = time.time() - self.started_at
        if elapsed > self.max_duration_sec:
            return False, f"超时: {elapsed:.1f}s > {self.max_duration_sec}s"
        
        if self.used_cost > self.max_cost_usd:
            return False, f"成本超限: ${self.used_cost:.4f} > ${self.max_cost_usd:.2f}"
        
        return True, "ok"


# 任务类型对应的默认预算
DEFAULT_BUDGETS = {
    "research": TaskBudget(max_tokens=200000, max_cost_usd=2.0, max_duration_sec=900),
    "code":     TaskBudget(max_tokens=150000, max_cost_usd=3.0, max_duration_sec=1200),
    "classify": TaskBudget(max_tokens=10000,  max_cost_usd=0.05, max_duration_sec=60),
    "summary":  TaskBudget(max_tokens=20000,  max_cost_usd=0.1, max_duration_sec=120),
}


def get_budget_for_task(task) -> TaskBudget:
    """根据任务类型返回预算"""
    return DEFAULT_BUDGETS.get(task.type, TaskBudget())
```

### 在 Executor 里使用

```python
# executors/claude_api.py（增强）
from .base import Task, Step
from tools.llm import call_claude
from tools.task_budget import get_budget_for_task


# 模型定价（per 1M tokens, USD）
PRICING = {
    "claude-opus-4-5":   {"input": 15.0, "output": 75.0},
    "claude-sonnet-4-7": {"input": 3.0,  "output": 15.0},
}


class ClaudeAPIExecutor:
    bot_name = "Claude-Reasoner"
    
    def execute(self, task: Task):
        budget = get_budget_for_task(task)
        model = "claude-opus-4-5"
        
        yield Step("准备调用", f"模型: {model}，预算上限: ${budget.max_cost_usd}")
        budget.add_step()
        
        # 检查预算
        ok, msg = budget.check()
        if not ok:
            raise RuntimeError(f"Budget exceeded: {msg}")
        
        # 调用
        text, usage = call_claude(task.content, model=model)
        
        # 计算成本
        price = PRICING[model]
        cost = (
            usage["input_tokens"] / 1_000_000 * price["input"] +
            usage["output_tokens"] / 1_000_000 * price["output"]
        )
        budget.add_usage(usage["input_tokens"] + usage["output_tokens"], cost)
        
        yield Step(
            "API 返回",
            f"In {usage['input_tokens']} / Out {usage['output_tokens']} / 花费 ${cost:.4f}"
        )
        budget.add_step()
        
        # 写文件
        output_path = f"outputs/{task.id}.md"
        with open(output_path, "w") as f:
            f.write(text)
        
        yield Step("完成", f"已写入 {output_path}（任务总花费 ${budget.used_cost:.4f}）")
```

---

## 六、Layer 4：每日预算

每天累计的 token 和成本不能超限。

```python
# tools/daily_budget.py
import json
from datetime import datetime, timezone
from pathlib import Path


BUDGET_FILE = Path("data/daily_budget.json")
BUDGET_FILE.parent.mkdir(parents=True, exist_ok=True)


# 每日上限
DAILY_LIMITS = {
    "max_tokens": 5_000_000,           # 5M tokens
    "max_cost_usd": 50.0,              # $50
    "max_tasks": 200,                   # 200 个任务
}


def _load_today() -> dict:
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    if BUDGET_FILE.exists():
        data = json.loads(BUDGET_FILE.read_text())
        if data.get("date") == today:
            return data
    
    return {
        "date": today,
        "tokens": 0,
        "cost": 0.0,
        "tasks": 0,
    }


def add_daily_usage(tokens: int, cost: float):
    """累加今日用量"""
    data = _load_today()
    data["tokens"] += tokens
    data["cost"] += cost
    data["tasks"] += 1
    BUDGET_FILE.write_text(json.dumps(data, indent=2))


def check_daily_budget() -> tuple[bool, str]:
    """检查是否还能继续执行"""
    data = _load_today()
    
    if data["tokens"] > DAILY_LIMITS["max_tokens"]:
        return False, f"今日 token 超限: {data['tokens']:,} > {DAILY_LIMITS['max_tokens']:,}"
    
    if data["cost"] > DAILY_LIMITS["max_cost_usd"]:
        return False, f"今日成本超限: ${data['cost']:.2f} > ${DAILY_LIMITS['max_cost_usd']}"
    
    if data["tasks"] > DAILY_LIMITS["max_tasks"]:
        return False, f"今日任务数超限: {data['tasks']} > {DAILY_LIMITS['max_tasks']}"
    
    return True, "ok"


def get_daily_summary() -> str:
    """获取今日总览（用于飞书显影）"""
    data = _load_today()
    pct_cost = data["cost"] / DAILY_LIMITS["max_cost_usd"] * 100
    return (
        f"📊 今日（{data['date']}）：\n"
        f"  任务: {data['tasks']}/{DAILY_LIMITS['max_tasks']}\n"
        f"  Token: {data['tokens']:,}/{DAILY_LIMITS['max_tokens']:,}\n"
        f"  成本: ${data['cost']:.2f}/${DAILY_LIMITS['max_cost_usd']} ({pct_cost:.1f}%)"
    )
```

### 在 Orchestrator 主循环里集成

```python
# core.py（增强）
from tools.daily_budget import check_daily_budget, add_daily_usage, get_daily_summary
from tools.alerts import alert_critical


def run_forever(poll_interval: int = 30):
    print(f"[MAE] Orchestrator started.")
    
    while True:
        try:
            # 每个轮询周期检查每日预算
            ok, msg = check_daily_budget()
            if not ok:
                alert_critical(f"每日预算超限，暂停轮询：{msg}")
                # 等到明天
                time.sleep(3600)
                continue
            
            tasks = fetch_pending_tasks()
            for task in tasks:
                run_one_task(task)
        
        except Exception as e:
            print(f"[ERROR] {e}")
        
        time.sleep(poll_interval)
```

---

## 七、Layer 5：全局紧急刹车

最后的兜底——三种刹车方式。

### 方式 1：环境变量

```bash
# 紧急停服
echo "ORCHESTRATOR_PAUSED=1" >> .env
# 重启 orchestrator，它会读到环境变量然后什么都不做
```

### 方式 2：文件标记

```python
# tools/kill_switch.py
from pathlib import Path

KILL_FILE = Path(".kill_switch")


def is_killed() -> bool:
    return KILL_FILE.exists()


def kill():
    KILL_FILE.touch()


def revive():
    KILL_FILE.unlink(missing_ok=True)
```

```bash
# SSH 到 Mac Mini，touch 一个文件就停
touch .kill_switch
# orchestrator 下次 poll 时发现文件，立刻暂停

# 恢复
rm .kill_switch
```

### 方式 3：飞书命令（未来扩展）

在飞书里 @ MAE-PM bot 发：
- `/pause` → 暂停
- `/resume` → 继续
- `/status` → 查看当前状态
- `/budget` → 查看今日预算

需要在飞书 bot 里加事件处理逻辑，未来扩展。

---

## 八、显影集成：让你看到成本

### 任务级显影

每个任务完成时，显影里带成本：

```
🚀 [Task #abc123] research
  → 准备调用: 模型: claude-opus-4-5，预算上限: $2.0
  → API 返回: In 3500 / Out 800 / 花费 $0.1125
  → 完成: 已写入 outputs/abc123.md（任务总花费 $0.1125）
✅ 完成（耗时 8.3s）
```

### 每日总览

每天早上 9 点，PM Bot 自动发一条总结：

```python
# 在 cron 任务里
from tools.daily_budget import get_daily_summary
from tools.feishu import send_message
import os

send_message("MAE-PM", os.getenv("FEISHU_GROUP_ID"), get_daily_summary())
```

显影效果：

```
📊 今日（2026-04-17）：
  任务: 23/200
  Token: 1,234,567/5,000,000
  成本: $8.45/$50.00 (16.9%)
```

---

## 九、初始预算建议

刚开始跑时，先**保守一点**，跑顺了再放开：

| Layer | 项目 | 起步值 | 跑顺后 |
|-------|------|------|------|
| Layer 1 | 任务描述长度 | 10,000 字 | 50,000 字 |
| Layer 2 | 单次 API max_tokens | 4,096 | 8,192 |
| Layer 3 | 单任务最多花费 | $0.5 | $2.0 |
| Layer 3 | 单任务最多步数 | 30 | 50 |
| Layer 3 | 单任务最多时长 | 5 分钟 | 15 分钟 |
| Layer 4 | 每日总成本 | $5 | $50 |
| Layer 4 | 每日总任务数 | 50 | 200 |

**关键**：第一周观察实际用量，再调整阈值。盲目调大 = 失控风险，盲目调小 = 任务老是被中断。

---

## 十、跑飞了怎么办（Recovery Playbook）

如果某天突然发现成本失控：

### Step 1：立刻刹车

```bash
ssh macmini
cd ~/Projects/local-automation-stack/mae-orchestrator
touch .kill_switch
```

### Step 2：定位问题任务

```bash
# 看今日预算
cat data/daily_budget.json

# 看错误日志
tail -100 logs/errors/$(date +%Y-%m-%d).jsonl

# 看 Airtable 哪些任务消耗大（在 Airtable 里按 cost 排序）
```

### Step 3：处理元凶

- 如果是某类任务失控 → 调小那个类型的预算
- 如果是某个任务无限重试 → 把它 mark failed
- 如果是 Skill 写错了导致死循环 → 修 Skill

### Step 4：恢复

```bash
rm .kill_switch
# orchestrator 自动恢复轮询
```

### Step 5：复盘

每次跑飞都写一份 retro，吸收成 guard 的新规则。

---

## 十一、和错误处理的协同

资源 Guard 触发的"中断"，本质上是一种特殊错误：

```python
# 在 Executor 里
ok, msg = budget.check()
if not ok:
    raise RuntimeError(f"Budget exceeded: {msg}")
```

这个 `RuntimeError` 会被 `core.py` 的 `handle_error` 捕获。

**重要决策**：预算超限的错误，应该归到哪个 ErrorClass？

建议：归到 **PARAM**（B 类），不可重试。理由：
- 重试不会改变预算超限的事实
- 直接 mark failed 让人介入
- 人介入后可以选择：调大预算 / 拆小任务 / 优化 prompt

修改 `tools/error_classifier.py`：

```python
def classify_error(exc: Exception) -> str:
    err_msg = str(exc).lower()
    
    # 预算超限 = 参数错误（不可重试）
    if "budget exceeded" in err_msg or "超限" in err_msg:
        return ErrorClass.PARAM
    
    # ... 其他规则
```

---

## 十二、Mac Mini 部署的渐进式启用

### M1 阶段（最小闭环）

只启用 Layer 1 + Layer 2：
- 任务描述长度限制
- API max_tokens 强制设置

这两个加起来不到 20 行代码，但能挡住 80% 的失控场景。

### M1 跑通后第 1 周

加 Layer 3：
- 单任务预算（先用最保守的值）
- 在 Executor 里跟踪 step / tokens / cost
- 显影里显示成本

### M2 阶段

加 Layer 4：
- 每日预算 + 每日总览
- 飞书告警（超 50% 警告，超 90% 暂停）

### M3 阶段

加 Layer 5：
- 全局 kill switch
- 飞书命令（pause/resume/status）
- 历史成本分析（每周一份 cost report）

---

## 十三、最重要的一句话

**不要相信"agent 不会跑飞"——它一定会。问题只是早晚。**

资源 Guard 不是优化，是必需。M2 之前补完。

跑飞过一次的代价：钱（$50-200） + 信心（怀疑整个架构） + 时间（debug + 重置）。补 Guard 的代价：4 小时写代码。

划算得不能再划算。
