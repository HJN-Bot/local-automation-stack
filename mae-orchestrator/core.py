import time
import traceback
from tools.airtable import fetch_pending_tasks, mark_running, mark_done, mark_failed
from router import choose_executor
from display import post_task_header, post_step, post_task_done, post_task_failed
from executors.base import Step


def run_one_task(task):
    start = time.time()
    thread_id = post_task_header(task)

    try:
        mark_running(task.id)
        executor, decision = choose_executor(task)

        # 路由决策作为第一条 step 显影
        post_step(thread_id, Step("路由决策", decision.to_step_summary()), bot_name="MAE-PM")

        for step in executor.execute(task):
            print(f"  [{step.action}] {step.summary}")
            post_step(thread_id, step, bot_name=executor.bot_name)

        mark_done(task.id, f"outputs/{task.id}.md")
        post_task_done(thread_id, time.time() - start)

    except Exception as e:
        error_msg = f"{type(e).__name__}: {str(e)}"
        traceback.print_exc()
        mark_failed(task.id, error_msg)
        post_task_failed(thread_id, error_msg)


def run_forever(poll_interval: int = 30):
    print(f"[MAE] Orchestrator started. Polling every {poll_interval}s...")
    while True:
        try:
            tasks = fetch_pending_tasks()
            if tasks:
                print(f"[MAE] Found {len(tasks)} pending task(s)")
            for task in tasks:
                print(f"[MAE] Processing {task.id} ({task.type}): {task.content[:60]}")
                run_one_task(task)
        except Exception as e:
            print(f"[ERROR] {e}")
            traceback.print_exc()
        time.sleep(poll_interval)
