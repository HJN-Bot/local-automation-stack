import os
import traceback
from tools.feishu import send_message, reply_message
from executors.base import Step


def _safe_send(fn, *args, **kwargs):
    """Wrap Feishu calls so they never block the pipeline."""
    try:
        return fn(*args, **kwargs)
    except Exception as e:
        print(f"[display] Feishu post failed (non-fatal): {e}")
        traceback.print_exc()
        return None


def post_task_header(task) -> str:
    text = f"🚀 [Task #{task.id}] {task.type}\n{task.content[:200]}"
    result = _safe_send(send_message, os.getenv("FEISHU_GROUP_ID"), text, bot_name="MAE-PM")
    return result or task.id  # fallback: return task.id as thread_id


def post_step(thread_id: str, step: Step, bot_name: str = "DS-Worker"):
    text = f"  → {step.action}: {step.summary}"
    _safe_send(reply_message, thread_id, text, bot_name=bot_name)


def post_task_done(thread_id: str, duration: float):
    _safe_send(reply_message, thread_id, f"✅ 完成（耗时 {duration:.1f}s）", bot_name="MAE-PM")


def post_task_failed(thread_id: str, error: str):
    _safe_send(reply_message, thread_id, f"❌ 失败：{error[:200]}", bot_name="MAE-PM")
