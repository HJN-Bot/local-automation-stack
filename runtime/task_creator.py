"""
Task creator — called by Sam (Andrew) to create a new MAE task.

Does three things atomically:
  1. Writes a LOADED record to Airtable (triggers harness on next poll)
  2. Posts the task anchor card to Feishu via Andrew Bot (creates thread)
  3. Writes feishu_thread_id back to the Airtable record

Returns a TaskCreationResult so Sam can confirm to the user what was started.
"""
from __future__ import annotations

import json
import logging
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone

from pyairtable import Api

import runtime.notify as notify
from runtime.config import (
    AIRTABLE_API_KEY,
    AIRTABLE_BASE_ID,
    TABLE_TASKSTATELOG,
    FIELDS,
)

log = logging.getLogger(__name__)


@dataclass
class TaskCreationResult:
    record_id: str
    task_id: str
    feishu_thread_id: str | None  # None if Feishu not yet configured
    airtable_url: str


def create_task(
    goal: str,
    owner_agent: str = "SAM",
    eta: str = "—",
    source: str = "discord",
    task_id: str | None = None,
) -> TaskCreationResult:
    """
    Create a MAE task from Sam's trigger.

    Args:
        goal:        One-sentence description of what needs to be done.
        owner_agent: Which agent owns this task ("SAM" / "REX" / "LULU" / "ALEX").
        eta:         Human-readable time estimate ("2小时" / "今天内" / "30min").
        source:      Where the task came from ("discord" / "manual" / "feishu").
        task_id:     Optional — if not provided, auto-generated from timestamp.

    Returns:
        TaskCreationResult with record_id, task_id, feishu_thread_id.
    """
    if task_id is None:
        ts = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M")
        short = str(uuid.uuid4())[:4]
        task_id = f"task-{ts}-{short}"

    tbl = Api(AIRTABLE_API_KEY).base(AIRTABLE_BASE_ID).table(TABLE_TASKSTATELOG)

    # ── Step 1: Create Airtable record ────────────────────────────────────────
    initial_context = json.dumps({
        "messages": [{"role": "user", "content": goal}]
    })

    record = tbl.create({
        FIELDS["task_id"]:    task_id,
        FIELDS["status"]:     "LOADED",
        FIELDS["owner_agent"]: owner_agent,
        FIELDS["source"]:     source,
        FIELDS["task_context"]: initial_context,
        FIELDS["updated_at"]: datetime.now(timezone.utc).isoformat(),
    })
    record_id = record["id"]
    log.info("task_creator: created %s (record=%s)", task_id, record_id)

    # ── Step 2: Post Feishu task anchor (creates thread) ──────────────────────
    feishu_thread_id = notify.send_task_start(
        task_id=task_id,
        goal=goal,
        owner_agent=owner_agent,
        eta=eta,
    )

    # ── Step 3: Write feishu_thread_id back to Airtable ───────────────────────
    if feishu_thread_id:
        tbl.update(record_id, {FIELDS["feishu_thread_id"]: feishu_thread_id})
        log.info("task_creator: feishu_thread_id=%s written back", feishu_thread_id)
    else:
        log.warning("task_creator: Feishu thread not created for %s", task_id)

    airtable_url = (
        f"https://airtable.com/{AIRTABLE_BASE_ID}/{TABLE_TASKSTATELOG}/{record_id}"
    )

    return TaskCreationResult(
        record_id=record_id,
        task_id=task_id,
        feishu_thread_id=feishu_thread_id,
        airtable_url=airtable_url,
    )
