"""
State machine — enforces valid transitions and writes state to Airtable.

Valid transitions:
  LOADED   → RUNNING
  RUNNING  → REVIEW | DONE | BLOCKED | FAILED
  REVIEW   → DONE | RUNNING (if LENS rejects, back to RUNNING for fix)
  BLOCKED  → RUNNING (after human recovery)
  FAILED   → (terminal, no auto-transition)
  DONE     → (terminal)
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import TYPE_CHECKING

from pyairtable import Api

from runtime.config import (
    AIRTABLE_API_KEY,
    AIRTABLE_BASE_ID,
    TABLE_TASKSTATELOG,
    FIELDS,
)

if TYPE_CHECKING:
    pass

log = logging.getLogger(__name__)

VALID_TRANSITIONS: dict[str, set[str]] = {
    "LOADED":   {"RUNNING"},
    "WAITING":  {"LOADED"},    # parent task: activated by aggregation trigger
    "RUNNING":  {"REVIEW", "DONE", "BLOCKED", "FAILED"},
    "REVIEW":   {"DONE", "RUNNING", "BLOCKED"},
    "BLOCKED":  {"RUNNING"},
    "DONE":     set(),
    "FAILED":   set(),
}


def _table():
    return Api(AIRTABLE_API_KEY).base(AIRTABLE_BASE_ID).table(TABLE_TASKSTATELOG)


def transition(
    record_id: str,
    current_status: str,
    target_status: str,
    *,
    extra_fields: dict | None = None,
) -> dict:
    """
    Transition a task to target_status.
    Raises ValueError if the transition is not allowed.
    Returns the updated Airtable record.
    """
    allowed = VALID_TRANSITIONS.get(current_status, set())
    if target_status not in allowed:
        raise ValueError(
            f"Invalid transition {current_status!r} → {target_status!r}. "
            f"Allowed: {allowed}"
        )

    fields: dict = {
        FIELDS["status"]:     target_status,
        FIELDS["updated_at"]: datetime.now(timezone.utc).isoformat(),
    }
    if extra_fields:
        fields.update(extra_fields)

    updated = _table().update(record_id, fields)
    log.info("state_machine: %s → %s  (record=%s)", current_status, target_status, record_id)
    return updated


def force_status(record_id: str, status: str, extra_fields: dict | None = None) -> dict:
    """
    Bypass transition rules — use only for SWEEP/GC cleanup or tests.
    """
    fields: dict = {
        FIELDS["status"]:     status,
        FIELDS["updated_at"]: datetime.now(timezone.utc).isoformat(),
    }
    if extra_fields:
        fields.update(extra_fields)

    updated = _table().update(record_id, fields)
    log.warning("state_machine: FORCE → %s  (record=%s)", status, record_id)
    return updated
