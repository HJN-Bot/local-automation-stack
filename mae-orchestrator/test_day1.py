"""Day 1 最小闭环测试：不走 Airtable，手动构造任务，验证飞书显影"""
import time
import os
from dotenv import load_dotenv

load_dotenv()

from executors.base import Task
from executors.deepseek_api import DeepSeekExecutor
from display import post_task_header, post_step, post_task_done

task = Task(
    id="test-001",
    type="research",
    content="用三句话解释什么是多 agent 系统",
    context={},
)

print(f"开始测试任务: {task.content}")
start = time.time()

thread_id = post_task_header(task)
print(f"✅ 飞书主消息已发，thread_id={thread_id}")

executor = DeepSeekExecutor()
for step in executor.execute(task):
    print(f"  [{step.action}] {step.summary}")
    post_step(thread_id, step)

post_task_done(thread_id, time.time() - start)
print(f"✅ 全部完成，耗时 {time.time() - start:.1f}s")
print("去飞书群看显影消息 👀")
