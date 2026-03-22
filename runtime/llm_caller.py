"""
LLM-agnostic caller — supports Claude (Anthropic) and OpenAI.
Controlled by LLM_PROVIDER env var: "claude" | "openai"

Output contract: always returns a parsed dict matching the schema in task_context.build_system_prompt.
Retries up to LLM_RETRY_MAX times if the model returns malformed JSON.
"""
from __future__ import annotations

import json
import logging
import time

from runtime.config import (
    LLM_PROVIDER,
    LLM_MODEL,
    CLAUDE_API_KEY,
    OPENAI_API_KEY,
    LLM_RETRY_MAX,
)

log = logging.getLogger(__name__)

# Required keys in LLM output
REQUIRED_OUTPUT_KEYS = {"status", "action_taken", "evidence", "next_step", "needs_human"}
VALID_STATUSES = {"RUNNING", "DONE", "BLOCKED", "REVIEW"}


def call(system_prompt: str, messages: list[dict]) -> dict:
    """
    Call the configured LLM and return a validated structured dict.
    Raises RuntimeError if output cannot be parsed after LLM_RETRY_MAX attempts.
    """
    for attempt in range(1, LLM_RETRY_MAX + 1):
        try:
            raw = _call_provider(system_prompt, messages)
            result = _parse_and_validate(raw)
            return result
        except (ValueError, json.JSONDecodeError) as exc:
            log.warning("llm_caller: attempt %d/%d failed: %s", attempt, LLM_RETRY_MAX, exc)
            if attempt < LLM_RETRY_MAX:
                # Append the error as a user correction message and retry
                messages = [
                    *messages,
                    {
                        "role":    "user",
                        "content": (
                            f"Your previous response was not valid JSON or was missing required fields. "
                            f"Error: {exc}. "
                            f"Please respond with ONLY a valid JSON object matching the required schema."
                        ),
                    },
                ]
                time.sleep(2 ** attempt)  # exponential backoff

    raise RuntimeError(f"LLM failed to return valid output after {LLM_RETRY_MAX} attempts")


def _call_provider(system_prompt: str, messages: list[dict]) -> str:
    if LLM_PROVIDER == "mock":
        return _call_mock(messages)
    if LLM_PROVIDER == "claude":
        return _call_claude(system_prompt, messages)
    if LLM_PROVIDER == "openai":
        return _call_openai(system_prompt, messages)
    raise ValueError(f"Unknown LLM_PROVIDER: {LLM_PROVIDER!r}. Set to 'mock', 'claude', or 'openai'.")


def _call_mock(messages: list[dict]) -> str:
    """
    Mock LLM — returns a valid DONE response for pipeline testing.
    No API calls, no cost. Set LLM_PROVIDER=mock in .env to use.
    """
    import json as _json
    from datetime import datetime, timezone
    goal = messages[-1]["content"] if messages else "unknown task"
    return _json.dumps({
        "status": "DONE",
        "action_taken": f"[MOCK] Completed task: {goal[:80]}",
        "evidence": {
            "run_id":       "mock-run-001",
            "log_summary":  "Mock execution completed successfully. All steps verified.",
            "artifact_link": "https://github.com/HJN-Bot/local-automation-stack",
            "writeback_ts": datetime.now(timezone.utc).isoformat(),
        },
        "next_step": "Task complete.",
        "needs_human": False,
        "blocked_reason": None,
        "next_recovery_step": None,
    })


def _call_claude(system_prompt: str, messages: list[dict]) -> str:
    import anthropic

    client = anthropic.Anthropic(api_key=CLAUDE_API_KEY)
    response = client.messages.create(
        model=LLM_MODEL,
        max_tokens=2048,
        system=system_prompt,
        messages=messages,
    )
    return response.content[0].text


def _call_openai(system_prompt: str, messages: list[dict]) -> str:
    from openai import OpenAI

    client = OpenAI(api_key=OPENAI_API_KEY)
    full_messages = [{"role": "system", "content": system_prompt}, *messages]
    response = client.chat.completions.create(
        model=LLM_MODEL,
        messages=full_messages,
        response_format={"type": "json_object"},
    )
    return response.choices[0].message.content


def _parse_and_validate(raw: str) -> dict:
    """
    Parse raw LLM output as JSON and validate required fields.
    Raises ValueError or json.JSONDecodeError on failure.
    """
    # Strip markdown code fences if model wrapped response
    text = raw.strip()
    if text.startswith("```"):
        lines = text.split("\n")
        text = "\n".join(lines[1:-1] if lines[-1].strip() == "```" else lines[1:])

    data = json.loads(text)

    missing = REQUIRED_OUTPUT_KEYS - set(data.keys())
    if missing:
        raise ValueError(f"Missing required keys in LLM output: {missing}")

    if data["status"] not in VALID_STATUSES:
        raise ValueError(f"Invalid status {data['status']!r}. Must be one of {VALID_STATUSES}")

    # Ensure evidence sub-fields exist
    evidence = data.get("evidence") or {}
    for key in ("run_id", "log_summary", "artifact_link", "writeback_ts"):
        if key not in evidence:
            evidence[key] = None
    data["evidence"] = evidence

    return data
