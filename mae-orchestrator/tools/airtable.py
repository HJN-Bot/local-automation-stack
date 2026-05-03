import json
import os
import re
from pyairtable import Api
from executors.base import Task

_TYPE_RE = re.compile(r"^\[mae_type:(\w+)\]\s*")
_CONTEXT_RE = re.compile(r"\[context:(\{.+?\})\]", re.DOTALL)


def _get_table():
    api = Api(os.getenv("AIRTABLE_API_KEY"))
    return api.table(os.getenv("AIRTABLE_BASE_ID"), os.getenv("AIRTABLE_TABLE_ID"))


def fetch_pending_tasks(limit: int = 10) -> list[Task]:
    table = _get_table()
    records = table.all(formula="{Status} = 'pending'", max_records=limit)
    tasks = []
    for r in records:
        f = r["fields"]
        raw_type = f.get("Task Type", "research")
        raw_content = f.get("Content", "")
        # Decode [mae_type:xxx] prefix if present
        m = _TYPE_RE.match(raw_content)
        if m:
            raw_type = m.group(1)
            raw_content = raw_content[m.end():]
        # Parse embedded context from content (e.g. [context:{"cli":"auto"}])
        exec_context = {}
        ctx_match = _CONTEXT_RE.search(raw_content)
        if ctx_match:
            try:
                exec_context = json.loads(ctx_match.group(1))
                # Strip the context tag from content
                raw_content = _CONTEXT_RE.sub("", raw_content).strip()
            except json.JSONDecodeError:
                pass

        tasks.append(Task(
            id=r["id"],
            type=raw_type,
            content=raw_content,
            context=exec_context,
        ))
    return tasks


def mark_running(task_id: str):
    _get_table().update(task_id, {"Status": "running"})


def mark_done(task_id: str, result_path: str = None):
    update = {"Status": "done"}
    if result_path:
        try:
            with open(result_path, encoding="utf-8") as f:
                update["Result"] = f.read()[:50000]
        except Exception:
            pass
    _get_table().update(task_id, update)


def mark_failed(task_id: str, error: str):
    _get_table().update(task_id, {"Status": "failed", "Error": error[:5000]})
