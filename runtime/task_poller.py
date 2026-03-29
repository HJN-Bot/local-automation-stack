"""
MAE Harness — main execution loop.

Entry point: python -m runtime.task_poller

Flow per invocation (cron fires this every N minutes):
  1. sweep_expired_locks()              — GC stale leases
  2. find LOADED tasks in Airtable
  3. for each task:
       a. claim lock
       b. LOADED → RUNNING
       c. load task_context (messages[])
       d. build system_prompt
       e. call LLM
       f. validate output (LENS gate)
       g. append LLM response to context, save
       h. transition state (RUNNING/DONE/BLOCKED/REVIEW)
       i. if DONE: push notify, release lock
       j. if BLOCKED: push notify, release lock
       k. if RUNNING: release lock (next cron picks up)
       l. if REVIEW: hold — do not release lock (LENS rejected, will retry)
"""
from __future__ import annotations

import logging
import sys
import uuid
from datetime import datetime, timezone

from pyairtable import Api

import runtime.lock_manager as lock_manager
import runtime.notify as notify
import runtime.state_machine as state_machine
import runtime.task_context as task_context
import runtime.tool_runner as tool_runner
import runtime.validation as validation
from runtime.config import (
    AIRTABLE_API_KEY,
    AIRTABLE_BASE_ID,
    TABLE_TASKSTATELOG,
    CLAIMABLE_STATUSES,
    FIELDS,
    TOOL_MAX_ITERATIONS,
)
from runtime.llm_caller import call as llm_call

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(name)s  %(message)s",
    datefmt="%Y-%m-%dT%H:%M:%SZ",
    stream=sys.stdout,
)
log = logging.getLogger("task_poller")


def _table():
    return Api(AIRTABLE_API_KEY).base(AIRTABLE_BASE_ID).table(TABLE_TASKSTATELOG)


def _find_claimable_tasks() -> list[dict]:
    """Return all records whose Status is in CLAIMABLE_STATUSES."""
    tbl = _table()
    status_filter = " OR ".join(
        f"{{Status}} = '{s}'" for s in CLAIMABLE_STATUSES
    )
    formula = f"OR({status_filter})"
    return tbl.all(formula=formula)


def _execute_task(record: dict) -> None:
    """Run one full harness cycle for a single task record."""
    record_id = record["id"]
    fields = record.get("fields", {})
    task_id = fields.get(FIELDS["task_id"], record_id)
    current_status = fields.get(FIELDS["status"], "LOADED")
    owner_agent = fields.get(FIELDS["owner_agent"], "SAM")

    # Read feishu_thread_id early — used for all notify calls in this task
    feishu_thread_id: str | None = fields.get(FIELDS["feishu_thread_id"]) or None

    log.info("task: %s | status: %s | agent: %s | feishu_thread: %s",
             task_id, current_status, owner_agent, feishu_thread_id or "none")

    # ── 1. Claim lock ────────────────────────────────────────────────────────
    token = lock_manager.claim(record_id)
    if token is None:
        log.info("task: %s skipped — locked by another process", task_id)
        return

    claimed_status = "FAILED"  # default — overwritten on success
    try:
        # ── 2. Transition to RUNNING ──────────────────────────────────────────
        run_id = str(uuid.uuid4())[:8]
        state_machine.transition(
            record_id,
            current_status,
            "RUNNING",
            extra_fields={FIELDS["run_id"]: run_id},
        )

        # Notify Feishu that this task has been picked up by the harness
        notify.send_agent_update(
            thread_id=feishu_thread_id,
            agent_name=owner_agent,
            msg_type="HEARTBEAT",
            title="任务已认领，开始执行",
            fields={"任务ID": task_id, "run_id": run_id, "执行者": owner_agent},
        )

        # ── 3. Load task_context ──────────────────────────────────────────────
        # load() tries to parse TaskContext as JSON messages[].
        # If it's plain text (first-run description), it returns [] and we
        # capture the raw text as the initial goal.
        messages, raw_context = task_context.load_with_raw(record_id)

        # ── 4. Build system prompt ────────────────────────────────────────────
        # Re-fetch fresh fields after status write
        fresh_record = _table().get(record_id)
        fresh_fields = fresh_record.get("fields", {})
        system_prompt = task_context.build_system_prompt(fresh_fields, owner_agent)

        # ── 5. Call LLM ───────────────────────────────────────────────────────
        llm_messages = task_context.to_llm_messages(messages)
        if not llm_messages:
            # First invocation — use raw TaskContext text as goal if available,
            # otherwise fall back to Progress field
            goal = raw_context or fresh_fields.get(FIELDS["progress"], "") or "No goal description provided."
            llm_messages = [{"role": "user", "content": f"Begin working on this task: {goal}"}]

        log.info("task: %s — calling LLM (%d messages)", task_id, len(llm_messages))
        llm_output = llm_call(system_prompt, llm_messages)

        # ── 5b. Tool-use loop ─────────────────────────────────────────────────
        # If the LLM requested tools (search / run_python / fetch_url / run_bash),
        # execute them and call the LLM again with the results.
        # Repeat up to TOOL_MAX_ITERATIONS times, then proceed with final output.
        tool_iter = 0
        while llm_output.get("tool_calls") and tool_iter < TOOL_MAX_ITERATIONS:
            tool_iter += 1
            log.info("task: %s — tool iteration %d/%d: %s",
                     task_id, tool_iter, TOOL_MAX_ITERATIONS,
                     [c.get("type") for c in llm_output["tool_calls"]])

            # Run all requested tools
            tool_results = tool_runner.execute_all(llm_output["tool_calls"])

            # Append tool results to context as "tool" role message
            messages = task_context.append(
                messages,
                role="tool",
                content=tool_results,
                agent="HARNESS",
            )
            task_context.save(record_id, messages)

            # Post heartbeat to Feishu so progress is visible
            tool_types = [c.get("type", "?") for c in llm_output["tool_calls"]]
            notify.send_agent_update(
                thread_id=feishu_thread_id,
                agent_name=owner_agent,
                msg_type="HEARTBEAT",
                title=f"工具调用 #{tool_iter}：{', '.join(tool_types)}",
                fields={"任务ID": task_id, "迭代": f"{tool_iter}/{TOOL_MAX_ITERATIONS}"},
            )

            # Call LLM again with tool results in context
            llm_messages = task_context.to_llm_messages(messages)
            llm_output = llm_call(system_prompt, llm_messages)

        if tool_iter >= TOOL_MAX_ITERATIONS and llm_output.get("tool_calls"):
            log.warning("task: %s — reached max tool iterations (%d), proceeding without more tools",
                        task_id, TOOL_MAX_ITERATIONS)

        # ── 6. LENS validation ────────────────────────────────────────────────
        val_result = validation.check_status_claim(llm_output)
        claimed_status = llm_output["status"]

        if claimed_status == "DONE" and not val_result:
            log.warning(
                "task: %s — LLM claimed DONE but evidence_pack failed: %s",
                task_id, val_result.reason,
            )
            # Downgrade to REVIEW so harness can retry
            claimed_status = "REVIEW"
            llm_output["status"] = "REVIEW"
            llm_output["next_step"] = (
                f"Evidence pack incomplete ({val_result.reason}). "
                "Complete the evidence and respond DONE again."
            )

        # ── 7. Append LLM response to context, save ───────────────────────────
        messages = task_context.append(
            messages,
            role="assistant",
            content=str(llm_output),
            agent=owner_agent,
        )
        task_context.save(record_id, messages)

        # ── 8. Transition state ───────────────────────────────────────────────
        # next_step is already saved in task_context messages[];
        # do NOT write it to Progress (which is a numeric field in Airtable)
        evidence = llm_output.get("evidence", {})
        extra: dict = {
            FIELDS["run_id"]: evidence.get("run_id") or run_id,
        }

        if claimed_status == "DONE":
            extra[FIELDS["artifact_links"]] = evidence.get("artifact_link") or ""
            state_machine.transition(record_id, "RUNNING", "DONE", extra_fields=extra)
            notify.send_done(task_id, record_id, evidence, owner_agent,
                             thread_id=feishu_thread_id)
            log.info("task: %s — DONE", task_id)

        elif claimed_status == "BLOCKED":
            blocked_reason = llm_output.get("blocked_reason", "Unknown")
            recovery = llm_output.get("next_recovery_step")
            extra[FIELDS["blocked_reason"]] = blocked_reason
            extra[FIELDS["next_recovery_step"]] = recovery or ""
            state_machine.transition(record_id, "RUNNING", "BLOCKED", extra_fields=extra)
            notify.send_blocked(task_id, record_id, blocked_reason, recovery, owner_agent,
                                thread_id=feishu_thread_id)
            log.info("task: %s — BLOCKED: %s", task_id, blocked_reason)

        elif claimed_status == "REVIEW":
            state_machine.transition(record_id, "RUNNING", "REVIEW", extra_fields=extra)
            log.info("task: %s — REVIEW (will retry next cycle)", task_id)

        else:  # RUNNING — release and wait for next cron
            state_machine.transition(record_id, "RUNNING", "RUNNING", extra_fields=extra)
            log.info("task: %s — still RUNNING, next_step: %s", task_id, llm_output.get("next_step"))

    except Exception as exc:
        log.error("task: %s — unhandled error: %s", task_id, exc, exc_info=True)
        try:
            state_machine.force_status(
                record_id, "FAILED",
                extra_fields={FIELDS["blocked_reason"]: str(exc)},
            )
        except Exception as inner:
            log.error("task: %s — could not write FAILED: %s", task_id, inner)
    finally:
        # Always release lock unless REVIEW (we hold to retry immediately next time)
        if claimed_status not in ("REVIEW",):
            lock_manager.release(record_id, token)


def run_once() -> None:
    """Single poll cycle — called by cron."""
    log.info("=== harness poll start ===")

    # GC expired locks first
    cleaned = lock_manager.sweep_expired()
    if cleaned:
        log.info("lock_manager: swept %d expired lock(s)", cleaned)

    tasks = _find_claimable_tasks()
    log.info("found %d claimable task(s)", len(tasks))

    for record in tasks:
        _execute_task(record)

    log.info("=== harness poll end ===")


if __name__ == "__main__":
    run_once()
