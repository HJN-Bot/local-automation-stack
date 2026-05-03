# 05 · Orchestrator 代码实现

> Mac Mini 到手后，照这份文档复制代码。每段都可以直接运行。

---

## 目录结构

```
mae-orchestrator/
├── .env                     # 环境变量（不提交 git）
├── .gitignore
├── requirements.txt
├── main.py                  # 入口
├── core.py                  # 主循环
├── display.py               # 飞书显影
├── router.py                # 路由逻辑
├── executors/
│   ├── __init__.py
│   ├── base.py              # 接口定义
│   ├── claude_api.py        # Claude API
│   ├── deepseek_api.py      # DeepSeek API
│   └── claude_code.py       # Claude Code CLI
├── tools/
│   ├── __init__.py
│   ├── airtable.py          # Airtable 读写
│   ├── feishu.py            # 飞书 API 封装
│   └── llm.py               # 模型 API 包装
├── skills/                  # （Phase 8 再填）
│   └── .gitkeep
└── outputs/                 # 任务产出文件
    └── .gitkeep
```

---

## 1. `executors/base.py` —— 统一接口

```python
from dataclasses import dataclass, field
from typing import Iterator, Protocol, Optional


@dataclass
class Task:
    id: str                          # Airtable record ID
    type: str                        # "research" | "code" | "classify" | ...
    content: str                     # 任务描述
    context: dict = field(default_factory=dict)  # 附加上下文


@dataclass
class Step:
    action: str                      # 显影给人看的动作名
    summary: str                     # 显影给人看的摘要
    raw: Optional[dict] = None       # 原始数据（调试用）


class Executor(Protocol):
    """所有 executor 必须实现的接口"""
    
    bot_name: str                    # 对应的飞书 bot 身份
    
    def execute(self, task: Task) -> Iterator[Step]:
        """执行任务，用 yield 返回每一步"""
        ...
```

---

## 2. `tools/llm.py` —— 模型 API 包装

```python
import anthropic
import requests
import os


def call_claude(prompt: str, model: str = "claude-opus-4-5", max_tokens: int = 4096) -> tuple[str, dict]:
    """调用 Claude API，返回 (文本, 用量信息)"""
    client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
    response = client.messages.create(
        model=model,
        max_tokens=max_tokens,
        messages=[{"role": "user", "content": prompt}]
    )
    text = response.content[0].text
    usage = {
        "input_tokens": response.usage.input_tokens,
        "output_tokens": response.usage.output_tokens,
    }
    return text, usage


def call_deepseek(prompt: str, model: str = "deepseek-chat") -> tuple[str, dict]:
    """调用 DeepSeek API（兼容 OpenAI 格式）"""
    resp = requests.post(
        "https://api.deepseek.com/v1/chat/completions",
        headers={
            "Authorization": f"Bearer {os.getenv('DEEPSEEK_API_KEY')}",
            "Content-Type": "application/json",
        },
        json={
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
        },
        timeout=60,
    )
    resp.raise_for_status()
    data = resp.json()
    text = data["choices"][0]["message"]["content"]
    usage = data.get("usage", {})
    return text, usage
```

---

## 3. `tools/feishu.py` —— 飞书 API 封装

```python
import requests
import json
import os
from functools import lru_cache


@lru_cache(maxsize=16)
def _get_token(app_id: str, app_secret: str) -> str:
    """获取飞书 tenant_access_token（缓存）"""
    resp = requests.post(
        "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal",
        json={"app_id": app_id, "app_secret": app_secret},
        timeout=10,
    )
    return resp.json()["tenant_access_token"]


def get_bot_token(bot_name: str) -> str:
    """根据 bot 名字获取 access token"""
    mapping = {
        "MAE-PM": ("FEISHU_PM_APP_ID", "FEISHU_PM_APP_SECRET"),
        "Claude-Reasoner": ("FEISHU_CLAUDE_APP_ID", "FEISHU_CLAUDE_APP_SECRET"),
        "DeepSeek-Router": ("FEISHU_DEEPSEEK_APP_ID", "FEISHU_DEEPSEEK_APP_SECRET"),
        "Claude-Code": ("FEISHU_CC_APP_ID", "FEISHU_CC_APP_SECRET"),
        "Research-Agent": ("FEISHU_RESEARCH_APP_ID", "FEISHU_RESEARCH_APP_SECRET"),
    }
    id_key, secret_key = mapping[bot_name]
    return _get_token(os.getenv(id_key), os.getenv(secret_key))


def send_message(bot_name: str, chat_id: str, text: str) -> str:
    """发送消息到群，返回 message_id"""
    token = get_bot_token(bot_name)
    resp = requests.post(
        "https://open.feishu.cn/open-apis/im/v1/messages",
        params={"receive_id_type": "chat_id"},
        headers={"Authorization": f"Bearer {token}"},
        json={
            "receive_id": chat_id,
            "msg_type": "text",
            "content": json.dumps({"text": text}),
        },
        timeout=10,
    )
    resp.raise_for_status()
    return resp.json()["data"]["message_id"]


def reply_message(bot_name: str, message_id: str, text: str) -> str:
    """回复某条消息（形成线程）"""
    token = get_bot_token(bot_name)
    resp = requests.post(
        f"https://open.feishu.cn/open-apis/im/v1/messages/{message_id}/reply",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "msg_type": "text",
            "content": json.dumps({"text": text}),
        },
        timeout=10,
    )
    resp.raise_for_status()
    return resp.json()["data"]["message_id"]
```

---

## 4. `display.py` —— 强制显影

```python
import os
from tools.feishu import send_message, reply_message
from executors.base import Step


def post_task_header(task) -> str:
    """PM Bot 发任务主消息"""
    text = f"🚀 [Task #{task.id}] {task.type}\n{task.content[:200]}"
    return send_message("MAE-PM", os.getenv("FEISHU_GROUP_ID"), text)


def post_step(thread_id: str, executor, step: Step):
    """对应 executor 的 bot 在回复串里发步骤"""
    text = f"  → {step.action}: {step.summary}"
    reply_message(executor.bot_name, thread_id, text)


def post_task_done(thread_id: str, task, duration: float):
    """任务完成"""
    text = f"✅ 完成（耗时 {duration:.1f}s）"
    reply_message("MAE-PM", thread_id, text)


def post_task_failed(thread_id: str, task, error: str):
    """任务失败"""
    text = f"❌ 失败：{error[:200]}"
    reply_message("MAE-PM", thread_id, text)
```

---

## 5. `executors/claude_api.py` —— Claude Executor

```python
from .base import Task, Step
from tools.llm import call_claude


class ClaudeAPIExecutor:
    bot_name = "Claude-Reasoner"
    
    def execute(self, task: Task):
        yield Step("准备调用", f"模型: claude-opus-4-5，任务类型: {task.type}")
        
        # 调用模型
        text, usage = call_claude(task.content)
        
        yield Step(
            "API 返回",
            f"输入 {usage['input_tokens']} tokens，输出 {usage['output_tokens']} tokens"
        )
        
        # 写文件
        output_path = f"outputs/{task.id}.md"
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(text)
        
        yield Step("完成", f"已写入 {output_path}")
```

---

## 6. `executors/deepseek_api.py` —— DeepSeek Executor

```python
from .base import Task, Step
from tools.llm import call_deepseek


class DeepSeekExecutor:
    bot_name = "DeepSeek-Router"
    
    def execute(self, task: Task):
        yield Step("调用 DeepSeek", f"任务: {task.content[:50]}...")
        
        text, usage = call_deepseek(task.content)
        
        total = usage.get("total_tokens", 0)
        yield Step("API 返回", f"总 tokens: {total}")
        
        output_path = f"outputs/{task.id}.md"
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(text)
        
        yield Step("完成", f"已写入 {output_path}")
```

---

## 7. `executors/claude_code.py` —— Claude Code CLI Executor

```python
import subprocess
from .base import Task, Step


class ClaudeCodeExecutor:
    bot_name = "Claude-Code"
    
    def execute(self, task: Task):
        working_dir = task.context.get("working_dir", ".")
        yield Step("启动 Claude Code", f"命令: claude -p (cwd={working_dir})")
        
        try:
            result = subprocess.run(
                ["claude", "-p", task.content, "--max-turns", "10"],
                capture_output=True,
                text=True,
                cwd=working_dir,
                timeout=600,
            )
        except subprocess.TimeoutExpired:
            yield Step("超时", "Claude Code 执行超过 10 分钟")
            return
        
        yield Step("CLI 返回", f"exit_code={result.returncode}，输出 {len(result.stdout)} 字符")
        
        if result.returncode == 0:
            output_path = f"outputs/{task.id}.log"
            with open(output_path, "w", encoding="utf-8") as f:
                f.write(result.stdout)
            yield Step("完成", f"已写入 {output_path}")
        else:
            yield Step("失败", f"stderr: {result.stderr[:200]}")
```

---

## 8. `router.py` —— 路由逻辑

```python
from executors.claude_api import ClaudeAPIExecutor
from executors.deepseek_api import DeepSeekExecutor
from executors.claude_code import ClaudeCodeExecutor


# 懒加载缓存
_cache = {}


def _get(key, factory):
    if key not in _cache:
        _cache[key] = factory()
    return _cache[key]


def choose_executor(task):
    """根据任务类型选择 executor
    
    未来可扩展为基于 skill description 的 latent 路由（Garry Tan 模式）
    """
    t = task.type.lower()
    
    # 代码任务 → Claude Code CLI
    if t in ("code", "debug", "refactor", "test"):
        return _get("claude_code", ClaudeCodeExecutor)
    
    # 便宜的分类/调度 → DeepSeek
    if t in ("classify", "route", "summary", "extract"):
        return _get("deepseek", DeepSeekExecutor)
    
    # 复杂推理/研究/写作 → Claude API
    if t in ("research", "analysis", "write", "review"):
        return _get("claude", ClaudeAPIExecutor)
    
    # 默认 fallback
    return _get("claude", ClaudeAPIExecutor)
```

---

## 9. `tools/airtable.py` —— 任务读写

```python
import os
from pyairtable import Api
from executors.base import Task


def _get_table():
    api = Api(os.getenv("AIRTABLE_API_KEY"))
    return api.table(os.getenv("AIRTABLE_BASE_ID"), os.getenv("AIRTABLE_TABLE_NAME"))


def fetch_pending_tasks(limit: int = 10) -> list[Task]:
    """获取 pending 状态的任务"""
    table = _get_table()
    records = table.all(formula="{Status} = 'pending'", max_records=limit)
    
    tasks = []
    for r in records:
        f = r["fields"]
        tasks.append(Task(
            id=r["id"],
            type=f.get("Task Type", "research"),
            content=f.get("Content", ""),
            context=f,
        ))
    return tasks


def mark_running(task_id: str):
    _get_table().update(task_id, {"Status": "running"})


def mark_done(task_id: str, result_path: str = None):
    update = {"Status": "done"}
    if result_path:
        try:
            with open(result_path) as f:
                update["Result"] = f.read()[:50000]  # Airtable 字段限制
        except:
            pass
    _get_table().update(task_id, update)


def mark_failed(task_id: str, error: str):
    _get_table().update(task_id, {
        "Status": "failed",
        "Error": error[:5000],
    })
```

---

## 10. `core.py` —— 主循环

```python
import time
import traceback
from tools.airtable import fetch_pending_tasks, mark_running, mark_done, mark_failed
from router import choose_executor
from display import post_task_header, post_step, post_task_done, post_task_failed
from executors.base import Step


def run_one_task(task):
    """执行单个任务 —— 核心：显影 + 执行"""
    start = time.time()
    thread_id = post_task_header(task)      # PM bot 发主消息
    executor = None
    
    try:
        mark_running(task.id)
        executor = choose_executor(task)
        
        # 关键：逐步消费 yield，每步都显影
        for step in executor.execute(task):
            post_step(thread_id, executor, step)
        
        mark_done(task.id, f"outputs/{task.id}.md")
        post_task_done(thread_id, task, time.time() - start)
    
    except Exception as e:
        error_msg = f"{type(e).__name__}: {str(e)}"
        traceback.print_exc()
        
        mark_failed(task.id, error_msg)
        if executor:
            post_step(thread_id, executor, Step("❌ 异常", error_msg[:200]))
        post_task_failed(thread_id, task, error_msg)


def run_forever(poll_interval: int = 30):
    """主循环：持续轮询 Airtable"""
    print(f"[MAE] Orchestrator started. Polling every {poll_interval}s...")
    
    while True:
        try:
            tasks = fetch_pending_tasks()
            if tasks:
                print(f"[MAE] Found {len(tasks)} pending task(s)")
            
            for task in tasks:
                print(f"[MAE] Processing task {task.id} ({task.type})")
                run_one_task(task)
        
        except Exception as e:
            print(f"[ERROR] Main loop exception: {e}")
            traceback.print_exc()
        
        time.sleep(poll_interval)
```

---

## 11. `main.py` —— 入口

```python
from dotenv import load_dotenv
from core import run_forever

if __name__ == "__main__":
    load_dotenv()
    run_forever(poll_interval=30)
```

---

## 12. 启动命令

```bash
cd ~/Projects/local-automation-stack/mae-orchestrator
source venv/bin/activate
python main.py
```

后台运行（可选）：

```bash
# 用 nohup
nohup python main.py > orchestrator.log 2>&1 &

# 或用 tmux（推荐）
tmux new -s mae
python main.py
# Ctrl+B 然后按 D 脱离 session，orchestrator 继续跑
# 回来看：tmux attach -t mae
```

---

## 13. 代码总行数估算

| 文件 | 行数 |
|------|------|
| executors/base.py | 25 |
| tools/llm.py | 30 |
| tools/feishu.py | 55 |
| tools/airtable.py | 45 |
| display.py | 25 |
| executors/claude_api.py | 20 |
| executors/deepseek_api.py | 20 |
| executors/claude_code.py | 30 |
| router.py | 30 |
| core.py | 45 |
| main.py | 5 |
| **合计** | **~330 行** |

符合"thin harness"原则。业务判断都在未来的 `skills/*.md` 里。
