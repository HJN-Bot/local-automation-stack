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
class PlanCreationResult:
    parent_record_id: str
    parent_task_id: str
    feishu_thread_id: str | None   # shared across all sub-tasks
    sub_tasks: list[dict]          # [{"record_id", "task_id", "owner_agent", "goal"}, ...]


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


def create_plan(
    parent_goal: str,
    sub_tasks: list[dict],
    source: str = "discord",
) -> PlanCreationResult:
    """
    Create a multi-agent plan: one parent task (owned by SAM for aggregation)
    and N sub-tasks each assigned to a specific agent.

    Sam calls this when a task needs multiple agents working in parallel.

    Args:
        parent_goal: The overall goal (one sentence).
        sub_tasks:   List of dicts, each with:
                       - goal (str): what this sub-task does
                       - owner_agent (str): REX / LULU / ALEX / SAM
                       - eta (str, optional): time estimate
        source:      Trigger source ("discord" / "manual").

    Returns:
        PlanCreationResult with parent + all sub-task IDs.

    Example:
        create_plan(
            parent_goal="调研竞品并产出报告",
            sub_tasks=[
                {"goal": "搜集竞品数据和定价", "owner_agent": "REX",  "eta": "30min"},
                {"goal": "整理报告框架和文案",  "owner_agent": "LULU", "eta": "30min"},
            ]
        )
    """
    tbl = Api(AIRTABLE_API_KEY).base(AIRTABLE_BASE_ID).table(TABLE_TASKSTATELOG)
    ts = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M")

    # ── 1. Create parent task (held WAITING until all sub-tasks complete) ─────
    parent_task_id = f"plan-{ts}-{str(uuid.uuid4())[:4]}"
    parent_context = json.dumps({
        "messages": [{"role": "user", "content": f"[AGGREGATION] {parent_goal}"}]
    })
    parent_record = tbl.create({
        FIELDS["task_id"]:     parent_task_id,
        FIELDS["status"]:      "WAITING",   # not LOADED — activated when all subs done
        FIELDS["owner_agent"]: "SAM",
        FIELDS["source"]:      source,
        FIELDS["task_context"]: parent_context,
        FIELDS["updated_at"]: datetime.now(timezone.utc).isoformat(),
    })
    parent_record_id = parent_record["id"]
    log.info("create_plan: parent %s (record=%s)", parent_task_id, parent_record_id)

    # ── 2. Create Feishu thread anchor (shared by all sub-tasks) ─────────────
    feishu_thread_id = notify.send_task_start(
        task_id=parent_task_id,
        goal=parent_goal,
        owner_agent="SAM",
        eta=f"{len(sub_tasks)} 个子任务并行",
    )
    if feishu_thread_id:
        tbl.update(parent_record_id, {FIELDS["feishu_thread_id"]: feishu_thread_id})

    # ── 3. Create sub-tasks (all LOADED, point to parent) ────────────────────
    created_subs: list[dict] = []
    for i, sub in enumerate(sub_tasks, 1):
        sub_goal         = sub["goal"]
        sub_agent        = sub.get("owner_agent", "SAM").upper()
        sub_eta          = sub.get("eta", "—")
        sub_task_id      = f"{parent_task_id}-sub{i}"
        sub_context      = json.dumps({
            "messages": [{"role": "user", "content": sub_goal}]
        })

        sub_record = tbl.create({
            FIELDS["task_id"]:       sub_task_id,
            FIELDS["status"]:        "LOADED",
            FIELDS["owner_agent"]:   sub_agent,
            FIELDS["source"]:        source,
            FIELDS["task_context"]:  sub_context,
            FIELDS["parent_task_id"]: parent_record_id,
            FIELDS["feishu_thread_id"]: feishu_thread_id or "",
            FIELDS["updated_at"]:    datetime.now(timezone.utc).isoformat(),
        })

        # Announce sub-task assignment in shared Feishu thread
        notify.send_agent_update(
            thread_id=feishu_thread_id,
            agent_name=sub_agent,
            msg_type="TASK_START",
            title=f"子任务 {i} 已分配",
            fields={"任务ID": sub_task_id, "目标": sub_goal, "ETA": sub_eta},
        )

        created_subs.append({
            "record_id":   sub_record["id"],
            "task_id":     sub_task_id,
            "owner_agent": sub_agent,
            "goal":        sub_goal,
        })
        log.info("create_plan: sub-task %s → %s (record=%s)", sub_task_id, sub_agent, sub_record["id"])

    return PlanCreationResult(
        parent_record_id=parent_record_id,
        parent_task_id=parent_task_id,
        feishu_thread_id=feishu_thread_id,
        sub_tasks=created_subs,
    )
