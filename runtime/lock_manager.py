"""
Idempotency lock — prevents duplicate execution when cron fires multiple times
or when two processes race on the same task.

Protocol:
  claim(record_id)  → sets LockToken + LeaseUntil + LeaseOwner, returns token
  release(record_id, token)  → clears lock fields
  is_expired(record)  → True if LeaseUntil is in the past
  sweep_expired()  → finds all records with expired leases and clears them
"""
from __future__ import annotations

import logging
import uuid
import socket
from datetime import datetime, timedelta, timezone

from pyairtable import Api

from runtime.config import (
    AIRTABLE_API_KEY,
    AIRTABLE_BASE_ID,
    TABLE_TASKSTATELOG,
    FIELDS,
    LEASE_DURATION_SECONDS,
)

log = logging.getLogger(__name__)

OWNER_ID = f"{socket.gethostname()}-harness"


def _table():
    return Api(AIRTABLE_API_KEY).base(AIRTABLE_BASE_ID).table(TABLE_TASKSTATELOG)


def claim(record_id: str) -> str | None:
    """
    Attempt to claim a task.
    Returns the lock_token if successful, None if already locked by another process.
    """
    tbl = _table()
    record = tbl.get(record_id)
    fields = record.get("fields", {})

    # Check if an unexpired lock exists
    existing_token = fields.get(FIELDS["lock_token"])
    lease_until_raw = fields.get(FIELDS["lease_until"])

    if existing_token and lease_until_raw:
        lease_until = datetime.fromisoformat(lease_until_raw.rstrip("Z")).replace(
            tzinfo=timezone.utc
        )
        if datetime.now(timezone.utc) < lease_until:
            log.info(
                "lock_manager: task %s already locked by %s until %s",
                record_id,
                fields.get(FIELDS["lease_owner"], "?"),
                lease_until.isoformat(),
            )
            return None  # Someone else holds the lock

    # Claim the lock
    token = str(uuid.uuid4())
    lease_until = datetime.now(timezone.utc) + timedelta(seconds=LEASE_DURATION_SECONDS)

    tbl.update(
        record_id,
        {
            FIELDS["lock_token"]:  token,
            FIELDS["lease_until"]: lease_until.isoformat(),
            FIELDS["lease_owner"]: OWNER_ID,
        },
    )
    log.info("lock_manager: claimed %s (token=%s, until=%s)", record_id, token[:8], lease_until.isoformat())
    return token


def release(record_id: str, token: str) -> None:
    """
    Release the lock if we still own it.
    Safe to call even if already released.
    """
    tbl = _table()
    record = tbl.get(record_id)
    current_token = record.get("fields", {}).get(FIELDS["lock_token"])

    if current_token != token:
        log.warning(
            "lock_manager: release skipped — token mismatch (record=%s, expected=%s, got=%s)",
            record_id, token[:8], str(current_token)[:8] if current_token else "None",
        )
        return

    tbl.update(
        record_id,
        {
            FIELDS["lock_token"]:  None,
            FIELDS["lease_until"]: None,
            FIELDS["lease_owner"]: None,
        },
    )
    log.info("lock_manager: released %s", record_id)


def is_expired(fields: dict) -> bool:
    """Check if a record's lease has expired (or was never set)."""
    lease_until_raw = fields.get(FIELDS["lease_until"])
    if not lease_until_raw:
        return True
    lease_until = datetime.fromisoformat(lease_until_raw.rstrip("Z")).replace(
        tzinfo=timezone.utc
    )
    return datetime.now(timezone.utc) >= lease_until


def sweep_expired() -> int:
    """
    Clear locks on all records whose lease has expired.
    Returns count of records cleaned up.
    Called by SWEEP/GC routine.
    """
    tbl = _table()
    formula = f"AND({{LockToken}} != '', {{LeaseUntil}} < NOW())"
    records = tbl.all(formula=formula)

    cleaned = 0
    for rec in records:
        tbl.update(
            rec["id"],
            {
                FIELDS["lock_token"]:  None,
                FIELDS["lease_until"]: None,
                FIELDS["lease_owner"]: None,
            },
        )
        cleaned += 1
        log.info("lock_manager: swept expired lock on %s", rec["id"])

    return cleaned
