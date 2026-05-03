# 10 · 错误处理与重试机制

> 解决"agent 出错就卡住"的问题。
> 这一层不是 MVP 必需，但 Mac Mini 跑起来 1 周内会暴露问题，建议 M1 之后立刻补。

---

## 一、错误的分类（决定怎么处理）

不是所有错误都该重试。先把错误分清楚。

### A 类：瞬时错误（可重试）

| 类型 | 示例 | 重试策略 |
|------|------|---------|
| 网络抖动 | `ConnectionError` / `Timeout` | 指数退避，3 次 |
| Rate limit | HTTP 429 | 看 `Retry-After` header |
| 模型临时过载 | HTTP 503 / `OverloadedError` | 指数退避，5 次 |
| 飞书 API 偶发失败 | 99991663 / 99991668 | 直接重试 1 次 |

### B 类：参数错误（不可重试）

| 类型 | 示例 | 处理 |
|------|------|------|
| 任务格式错 | 缺必填字段 | 直接 mark failed，写明原因 |
| 模型拒答 | 触发安全策略 | 直接 mark failed |
| 文件不存在 | `FileNotFoundError` | 直接 mark failed |
| 配置错 | 缺 API key | 立刻报警，停整个 orchestrator |

### C 类：逻辑错误（需要人介入）

| 类型 | 示例 | 处理 |
|------|------|------|
| 反复失败 3+ 次 | 同一任务连续重试都失败 | 进入死信队列，飞书 @ 你 |
| 模型输出格式不符预期 | 该返回 JSON 却返回文本 | 进死信队列 + 记录待分析 |
| 死循环 | 某 executor 连续 yield 100+ 步 | 强制中断，进死信队列 |

### D 类：致命错误（停服）

| 类型 | 示例 | 处理 |
|------|------|------|
| Airtable 完全不可达 | 5 分钟内全部失败 | 暂停主循环，飞书报警 |
| 飞书 token 全部失效 | 所有 bot token 报错 | 暂停，等人工修复 |
| 磁盘满 | `OSError: No space left` | 立刻停机 |

---

## 二、重试策略

### 指数退避（核心策略）

```python
# tools/retry.py
import time
import random
from functools import wraps


def retry_with_backoff(
    max_attempts: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 60.0,
    exceptions: tuple = (Exception,),
):
    """指数退避装饰器
    
    Args:
        max_attempts: 最大尝试次数
        base_delay: 基础延迟（秒）
        max_delay: 单次延迟上限
        exceptions: 哪些异常触发重试
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            last_exc = None
            for attempt in range(max_attempts):
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    last_exc = e
                    if attempt == max_attempts - 1:
                        raise
                    
                    # 指数退避 + 随机抖动
                    delay = min(base_delay * (2 ** attempt), max_delay)
                    delay += random.uniform(0, delay * 0.1)
                    
                    print(f"[retry] {func.__name__} attempt {attempt+1} failed: {e}. Retry in {delay:.1f}s")
                    time.sleep(delay)
            
            raise last_exc
        return wrapper
    return decorator
```

### 在 Tools 层用法

```python
# tools/feishu.py（增强版）
import requests
from tools.retry import retry_with_backoff


@retry_with_backoff(
    max_attempts=3,
    exceptions=(requests.ConnectionError, requests.Timeout),
)
def send_message(bot_name: str, chat_id: str, text: str) -> str:
    """发送飞书消息（自动重试网络错误）"""
    # ... 原代码
```

### 任务级重试（在 Orchestrator 层）

任务级和 API 级的重试是**两层不同的概念**：
- **API 级**：单次 HTTP 调用失败 → 立刻重试几次
- **任务级**：整个任务失败 → 隔一段时间重新执行整个任务

```python
# tools/airtable.py 加字段：retry_count, last_error_at
# 在 fetch 时考虑：
def fetch_pending_tasks(limit: int = 10) -> list[Task]:
    """获取需要执行的任务，包括待重试的"""
    table = _get_table()
    
    # 三种状态都要拉：pending（新任务）+ retry（可重试的失败任务）
    formula = """
    OR(
        {Status} = 'pending',
        AND(
            {Status} = 'retry',
            DATETIME_DIFF(NOW(), {LastErrorAt}, 'seconds') > 300
        )
    )
    """
    records = table.all(formula=formula, max_records=limit)
    # ... 转换为 Task 对象
```

---

## 三、错误分类器

```python
# tools/error_classifier.py
import requests


class ErrorClass:
    TRANSIENT = "transient"      # A 类，可重试
    PARAM = "param"               # B 类，不可重试
    LOGIC = "logic"               # C 类，进死信
    FATAL = "fatal"               # D 类，停服


def classify_error(exc: Exception) -> str:
    """判断错误类别"""
    
    # D 类：致命
    if isinstance(exc, OSError) and "No space left" in str(exc):
        return ErrorClass.FATAL
    
    # A 类：网络瞬时
    if isinstance(exc, (requests.ConnectionError, requests.Timeout)):
        return ErrorClass.TRANSIENT
    
    if isinstance(exc, requests.HTTPError):
        status = exc.response.status_code if exc.response else 0
        if status in (429, 502, 503, 504):
            return ErrorClass.TRANSIENT
        if status in (400, 401, 403, 404, 422):
            return ErrorClass.PARAM
    
    # 模型 API 特定错误
    err_msg = str(exc).lower()
    if any(k in err_msg for k in ["overloaded", "rate limit", "timeout"]):
        return ErrorClass.TRANSIENT
    if any(k in err_msg for k in ["invalid", "missing", "unauthorized"]):
        return ErrorClass.PARAM
    
    # 默认归 C 类逻辑错误
    return ErrorClass.LOGIC
```

---

## 四、Orchestrator 集成（增强版 core.py）

```python
# core.py（增强版）
import time
import traceback
from tools.airtable import (
    fetch_pending_tasks, mark_running, mark_done, 
    mark_failed, mark_retry, mark_dead_letter
)
from tools.error_classifier import classify_error, ErrorClass
from tools.alerts import alert_critical
from router import choose_executor
from display import post_task_header, post_step, post_task_done, post_task_failed
from executors.base import Step


MAX_TASK_RETRY = 3                    # 任务级最大重试次数
MAX_STEP_PER_TASK = 50                # 单任务最多 yield 50 步（防死循环）


def run_one_task(task):
    start = time.time()
    thread_id = post_task_header(task)
    executor = None
    
    try:
        mark_running(task.id)
        executor = choose_executor(task)
        
        # 执行 + 步数保护
        step_count = 0
        for step in executor.execute(task):
            step_count += 1
            if step_count > MAX_STEP_PER_TASK:
                raise RuntimeError(f"Task exceeded max steps ({MAX_STEP_PER_TASK})")
            post_step(thread_id, executor, step)
        
        # 成功
        mark_done(task.id, f"outputs/{task.id}.md")
        post_task_done(thread_id, task, time.time() - start)
    
    except Exception as e:
        handle_error(task, executor, thread_id, e)


def handle_error(task, executor, thread_id, exc):
    """统一错误处理"""
    err_class = classify_error(exc)
    err_msg = f"{type(exc).__name__}: {str(exc)}"
    traceback.print_exc()
    
    retry_count = task.context.get("retry_count", 0)
    
    if err_class == ErrorClass.FATAL:
        # D 类：停服
        alert_critical(f"FATAL error on task {task.id}: {err_msg}")
        mark_failed(task.id, err_msg)
        if executor:
            post_step(thread_id, executor, Step("🚨 FATAL", err_msg[:200]))
        raise SystemExit("Fatal error, stopping orchestrator")
    
    elif err_class == ErrorClass.TRANSIENT and retry_count < MAX_TASK_RETRY:
        # A 类：可重试 → mark retry
        mark_retry(task.id, err_msg, retry_count + 1)
        if executor:
            post_step(
                thread_id, executor,
                Step("⏳ 临时错误，将重试", f"{err_msg[:100]}（第 {retry_count+1}/{MAX_TASK_RETRY} 次）")
            )
    
    elif err_class == ErrorClass.LOGIC or retry_count >= MAX_TASK_RETRY:
        # C 类（或 A 类重试耗尽）：进死信
        mark_dead_letter(task.id, err_msg)
        if executor:
            post_step(thread_id, executor, Step("💀 进入死信队列", err_msg[:200]))
        post_task_failed(thread_id, task, f"已重试 {retry_count} 次，需人工介入")
    
    else:  # ErrorClass.PARAM
        # B 类：直接 failed
        mark_failed(task.id, err_msg)
        if executor:
            post_step(thread_id, executor, Step("❌ 参数错误", err_msg[:200]))
        post_task_failed(thread_id, task, err_msg)
```

---

## 五、Airtable Schema 增强

为了支持错误处理，给 Tasks 表加几个字段：

| 字段名 | 类型 | 说明 |
|-------|------|------|
| RetryCount | Number | 已重试次数 |
| LastErrorAt | DateTime | 最近一次失败时间 |
| LastErrorMsg | Long Text | 最近一次失败原因 |
| ErrorClass | Single Select | transient / param / logic / fatal |

Status 字段增加两个值：
- `retry`：失败但可重试（等冷却期过了重新跑）
- `dead_letter`：放弃执行，等人工

```python
# tools/airtable.py 新增
def mark_retry(task_id: str, error: str, retry_count: int):
    """标记为待重试"""
    from datetime import datetime
    _get_table().update(task_id, {
        "Status": "retry",
        "RetryCount": retry_count,
        "LastErrorAt": datetime.utcnow().isoformat(),
        "LastErrorMsg": error[:5000],
        "ErrorClass": "transient",
    })


def mark_dead_letter(task_id: str, error: str):
    """放进死信队列"""
    from datetime import datetime
    _get_table().update(task_id, {
        "Status": "dead_letter",
        "LastErrorAt": datetime.utcnow().isoformat(),
        "LastErrorMsg": error[:5000],
    })
```

---

## 六、死信队列处理

死信队列（dead_letter 状态）是**已经放弃自动重试，需要人介入**的任务。

### 飞书提醒

```python
# tools/alerts.py
from tools.feishu import send_message


def alert_critical(message: str):
    """发到飞书 + 钉一下你"""
    text = f"🚨🚨🚨 严重错误\n{message}\n\n请立刻检查"
    send_message("MAE-PM", os.getenv("FEISHU_GROUP_ID"), text)


def alert_dead_letter_summary():
    """每日汇总死信任务"""
    table = _get_table()
    records = table.all(formula="{Status} = 'dead_letter'")
    
    if not records:
        return
    
    text = f"📋 死信队列日报：{len(records)} 个任务待处理\n\n"
    for r in records[:5]:
        f = r["fields"]
        text += f"  • [{r['id']}] {f.get('Content', '')[:50]}... → {f.get('LastErrorMsg', '')[:100]}\n"
    
    if len(records) > 5:
        text += f"\n... 还有 {len(records) - 5} 个"
    
    send_message("MAE-PM", os.getenv("FEISHU_GROUP_ID"), text)
```

### 人工处理界面

不需要专门做 UI——直接在 Airtable 里：
1. 看到 Status=dead_letter 的任务
2. 修改任务内容/参数（如果是任务本身有问题）
3. 把 Status 改回 pending（让它重新进队列）
4. 或者把 Status 改成 failed（彻底放弃）

---

## 七、错误日志 + 长期学习

### 错误日志文件

```python
# tools/error_log.py
import json
from datetime import datetime
from pathlib import Path


def log_error(task, exc, err_class):
    """每个错误写一条结构化日志"""
    log_dir = Path("logs/errors")
    log_dir.mkdir(parents=True, exist_ok=True)
    
    today = datetime.utcnow().strftime("%Y-%m-%d")
    log_file = log_dir / f"{today}.jsonl"
    
    entry = {
        "timestamp": datetime.utcnow().isoformat(),
        "task_id": task.id,
        "task_type": task.type,
        "error_class": err_class,
        "error_type": type(exc).__name__,
        "error_msg": str(exc)[:500],
    }
    
    with open(log_file, "a") as f:
        f.write(json.dumps(entry) + "\n")
```

### 周报 / 月报：错误模式分析

每周看一次错误日志，找出**反复出现的错误模式**，把它们：
- 转成 skill（如果是判断问题）
- 转成代码（如果是确定性问题）
- 转成监控告警（如果是依赖问题）

这就是"程序性记忆"在工程上的体现——每个反复出现的错误都应该变成一次架构升级。

---

## 八、给 Mac Mini 部署的建议

### 一开始不要全部上

按这个顺序逐步加：

**M1 阶段（最小闭环）**：
- 只用最简单的 try/except，失败就 mark failed
- 不重试，不分类，不死信

**M1 跑通后第 1 周**：
- 加 `tools/retry.py`，给飞书/Airtable API 调用加上重试
- 加错误分类器
- 实现 mark_retry 和 retry 状态

**M2 阶段**：
- 加死信队列
- 加飞书告警
- 加错误日志

**M3 阶段**：
- 周报错误分析
- 反复错误转化为 skill / 代码改进

### 不要一开始就搞复杂

最小可工作的错误处理 = 4 行代码：

```python
try:
    run_one_task(task)
except Exception as e:
    print(f"[ERROR] task {task.id} failed: {e}")
    mark_failed(task.id, str(e))
```

先用这 4 行让系统跑起来，遇到具体痛点了再升级到本文档的完整方案。

**避免过早优化**——你需要的是先看到"哪些错误会真的发生"，再针对性处理。

---

## 九、监控指标（运行 1 个月后再考虑）

跑一段时间后，这些指标值得追踪：

| 指标 | 含义 | 阈值 |
|------|------|------|
| 任务成功率 | done / (done + failed + dead_letter) | < 90% 要调查 |
| 平均重试次数 | sum(RetryCount) / count(retry+done) | > 0.5 要调查 |
| 死信任务数（日） | count(dead_letter created today) | > 3 要调查 |
| 平均任务时长 | avg(updated_at - created_at) | 超过基线 50% 要调查 |
| Token 消耗（日） | sum(usage tokens) | 看 11-resource-guards.md |

可以用 Airtable 自带的 view + chart 来做仪表盘，不用专门搭监控系统。
