"""
Rolling task_context — loads / appends / saves the messages[] JSON from Airtable.

Format stored in TaskContext field (JSON string):
[
  {"role": "system",    "content": "...", "ts": "ISO", "agent": "SAM"},
  {"role": "assistant", "content": "...", "ts": "ISO", "agent": "FORGE"},
  {"role": "user",      "content": "...", "ts": "ISO", "agent": "harness"},
  ...
]

This is directly compatible with both Anthropic and OpenAI messages[] format
(role + content). The extra fields (ts, agent) are stripped when calling LLM.
"""
from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import Literal

from pyairtable import Api

from runtime.config import (
    AIRTABLE_API_KEY,
    AIRTABLE_BASE_ID,
    TABLE_TASKSTATELOG,
    FIELDS,
)

log = logging.getLogger(__name__)

Role = Literal["system", "user", "assistant"]


def _table():
    return Api(AIRTABLE_API_KEY).base(AIRTABLE_BASE_ID).table(TABLE_TASKSTATELOG)


def load(record_id: str) -> list[dict]:
    """
    Load messages[] from Airtable TaskContext field.
    Returns empty list if field is empty or invalid JSON.
    """
    messages, _ = load_with_raw(record_id)
    return messages


def load_with_raw(record_id: str) -> tuple[list[dict], str]:
    """
    Load messages[] from TaskContext field.
    Returns (messages, raw_text):
      - messages: parsed JSON list, or [] if not valid JSON
      - raw_text: the original string value (useful when it's a plain-text goal on first run)
    """
    record = _table().get(record_id)
    raw = record.get("fields", {}).get(FIELDS["task_context"], "") or ""
    if not raw:
        return [], ""
    try:
        data = json.loads(raw)
        if not isinstance(data, list):
            log.warning("task_context: unexpected format in %s, treating as plain text", record_id)
            return [], raw
        return data, ""
    except json.JSONDecodeError:
        # Plain text — treat as first-run task description
        log.info("task_context: plain text detected in %s, will use as goal", record_id)
        return [], raw


def append(
    messages: list[dict],
    role: Role,
    content: str,
    agent: str = "harness",
) -> list[dict]:
    """
    Append a new message entry to the in-memory list.
    Does NOT write to Airtable — call save() after.
    Returns the updated list (immutable pattern).
    """
    return [
        *messages,
        {
            "role":    role,
            "content": content,
            "ts":      datetime.now(timezone.utc).isoformat(),
            "agent":   agent,
        },
    ]


def trim(messages: list[dict], max_messages: int = 40) -> list[dict]:
    """
    Keep messages within max_messages limit.
    Strategy: always keep the first message (original goal) + the most recent ones.
    When trimmed, inserts a summary marker so the LLM knows history was condensed.
    """
    if len(messages) <= max_messages:
        return messages

    keep_head = 1          # always keep the initial goal message
    keep_tail = max_messages - keep_head - 1
    dropped = len(messages) - keep_head - keep_tail

    trimmed = [
        *messages[:keep_head],
        {
            "role":    "system",
            "content": f"[context trimmed: {dropped} older messages removed to stay within limits]",
            "ts":      datetime.now(timezone.utc).isoformat(),
            "agent":   "harness",
        },
        *messages[-keep_tail:],
    ]
    log.info("task_context: trimmed %d messages (kept head=%d + tail=%d)", dropped, keep_head, keep_tail)
    return trimmed


def save(record_id: str, messages: list[dict], max_messages: int = 40) -> None:
    """
    Persist messages[] back to Airtable as JSON string.
    Automatically trims to max_messages before saving.
    """
    messages = trim(messages, max_messages)
    _table().update(
        record_id,
        {FIELDS["task_context"]: json.dumps(messages, ensure_ascii=False)},
    )
    log.debug("task_context: saved %d messages to %s", len(messages), record_id)


def to_llm_messages(messages: list[dict]) -> list[dict]:
    """
    Strip harness-only fields (ts, agent) so the list is
    directly usable in Claude / OpenAI API calls.
    """
    return [{"role": m["role"], "content": m["content"]} for m in messages]


def build_system_prompt(task_fields: dict, agent_role: str = "SAM") -> str:
    """
    Build the minimal, task-specific system prompt injected into LLM calls.
    Follows MAE cognitive-layer principle: inject only what's relevant.
    """
    task_id  = task_fields.get(FIELDS["task_id"], "unknown")
    progress = task_fields.get(FIELDS["progress"], "")
    owner    = task_fields.get(FIELDS["owner_agent"], agent_role)

    return f"""You are {owner}, executing task {task_id} inside the MAE multi-agent harness.

## Your current mission
{progress or "(no description yet — determine from context)"}

## Output format (strict JSON, no markdown wrapping)
{{
  "status": "RUNNING | DONE | BLOCKED | REVIEW",
  "action_taken": "<what you just did>",
  "tool_calls": [],
  "evidence": {{
    "run_id": "<unique ID for this run, generate if none>",
    "log_summary": "<1-3 sentences of what happened>",
    "artifact_link": "<URL or path, or null — optional, leave null if no file produced>",
    "writeback_ts": "<ISO timestamp>"
  }},
  "next_step": "<what should happen next>",
  "needs_human": false,
  "blocked_reason": null,
  "next_recovery_step": null
}}

## Tools available (add to tool_calls when needed)
You can request tools by populating the tool_calls array. The harness will run them
and give you the results before your next response.

| type         | args required          | when to use                                  |
|--------------|------------------------|----------------------------------------------|
| search       | query, max_results?    | research, find info, look up APIs            |
| fetch_url    | url                    | read a specific doc page, README, blog post  |
| run_python   | script, timeout?       | process data, call APIs, run calculations    |
| run_bash     | script, timeout?       | file ops, system commands, check env         |

Example tool_calls:
[
  {{"id": "t1", "type": "search",   "args": {{"query": "Feishu API send card message"}}}},
  {{"id": "t2", "type": "run_python","args": {{"script": "import requests\\nprint(requests.get('https://httpbin.org/get').status_code)"}}}}
]

## Rules
- Use tools when you need external information or to run code — don't guess.
- Max 3 tool calls per response; max 5 tool-use iterations total per task cycle.
- status=RUNNING + tool_calls → harness runs tools, calls you again with results.
- status=BLOCKED if you cannot proceed even with tools and need human decision.
- status=DONE only when deliverables are complete AND evidence block is fully populated.
- NEVER claim DONE without run_id, log_summary, and writeback_ts. artifact_link is optional (null is fine).
- Omit tool_calls (or leave []) when you don't need tools.
"""
