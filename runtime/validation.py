"""
LENS gate — mechanical evidence_pack validation.
No LLM involved. Pure deterministic checks.

Evidence pack passes iff ALL four fields are non-null and non-empty:
  run_id, log_summary, artifact_link, writeback_ts

If validation fails, task goes to REVIEW (not DONE).
The harness decides whether to retry or escalate.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field

log = logging.getLogger(__name__)

REQUIRED_EVIDENCE_FIELDS = ("run_id", "log_summary", "artifact_link", "writeback_ts")


@dataclass
class ValidationResult:
    passed: bool
    missing_fields: list[str] = field(default_factory=list)
    reason: str = ""

    def __bool__(self) -> bool:
        return self.passed


def check_evidence_pack(llm_output: dict) -> ValidationResult:
    """
    Validate that the LLM output contains a complete evidence pack.

    Rules:
    - evidence dict must exist
    - All 4 required fields must be non-null and non-empty string
    - writeback_ts should look like an ISO timestamp (basic check)
    """
    evidence = llm_output.get("evidence")
    if not isinstance(evidence, dict):
        return ValidationResult(
            passed=False,
            missing_fields=list(REQUIRED_EVIDENCE_FIELDS),
            reason="evidence field is missing or not a dict",
        )

    missing = []
    for key in REQUIRED_EVIDENCE_FIELDS:
        val = evidence.get(key)
        if val is None or (isinstance(val, str) and not val.strip()):
            missing.append(key)

    if missing:
        return ValidationResult(
            passed=False,
            missing_fields=missing,
            reason=f"evidence_pack incomplete — missing: {', '.join(missing)}",
        )

    # Basic ISO timestamp sanity check on writeback_ts
    ts = evidence.get("writeback_ts", "")
    if not (len(ts) >= 10 and ts[4] == "-" and ts[7] == "-"):
        return ValidationResult(
            passed=False,
            missing_fields=["writeback_ts"],
            reason=f"writeback_ts does not look like ISO timestamp: {ts!r}",
        )

    log.debug("validation: evidence_pack PASS (run_id=%s)", evidence.get("run_id"))
    return ValidationResult(passed=True)


def check_status_claim(llm_output: dict) -> ValidationResult:
    """
    If LLM claims DONE, evidence pack must pass.
    If LLM claims BLOCKED, blocked_reason must be present.
    """
    status = llm_output.get("status")

    if status == "DONE":
        return check_evidence_pack(llm_output)

    if status == "BLOCKED":
        blocked_reason = llm_output.get("blocked_reason")
        if not blocked_reason or not str(blocked_reason).strip():
            return ValidationResult(
                passed=False,
                missing_fields=["blocked_reason"],
                reason="BLOCKED status requires blocked_reason to be set",
            )

    return ValidationResult(passed=True)
