"""
OpenClaw Bridge — routes agent calls to the OpenClaw adapter.

Architecture
============
                ┌─────────────────────────────────┐
  MAE Harness   │  openclaw_bridge.call()           │
  (this file)   │    POST adapter_url/dispatch      │
                └───────────────┬─────────────────-─┘
                                │  HTTP
                                ▼
                ┌──────────────────────────────────┐
  OpenClaw ctx  │  adapters/openclaw_adapter.py     │
                │    SAM / ANDREW  → sessions_send  │
                │    REX / LULU / ALEX → sessions_spawn │
                └──────────────────────────────────┘

The bridge is a DROP-IN replacement for llm_caller.call():
  - Same input:  system_prompt (str) + messages (list[dict]) + agent_name (str)
  - Same output: structured dict matching MAE JSON schema

Fallback:
  If OPENCLAW_ADAPTER_URL is not set, or the adapter call fails, the harness
  automatically falls back to runtime/llm_caller.py.
"""
from __future__ import annotations

import json
import logging
from typing import Any

import requests

from runtime.config import OPENCLAW_ADAPTER_URL, OPENCLAW_ADAPTER_KEY
from runtime import llm_caller as _fallback

log = logging.getLogger(__name__)

_TIMEOUT = 120  # seconds — agent runs can be slow


def is_available() -> bool:
    """Return True if the OpenClaw adapter is configured."""
    return bool(OPENCLAW_ADAPTER_URL)


def call(
    system_prompt: str,
    messages: list[dict],
    agent_name: str = "SAM",
) -> dict[str, Any]:
    """
    Route an agent call through the OpenClaw adapter, with automatic fallback.

    Args:
        system_prompt: Task-specific instructions for the agent.
        messages:      Conversation history (role/content dicts).
        agent_name:    Which OpenClaw agent to invoke.

    Returns:
        Structured dict in MAE JSON schema (status, action_taken, evidence, ...).
    """
    if not is_available():
        log.debug("openclaw_bridge: adapter not configured, using llm_caller fallback")
        return _fallback.call(system_prompt, messages)

    agent_key = agent_name.upper()
    payload = {
        "agent":         agent_key,
        "system_prompt": system_prompt,
        "messages":      messages[-10:],  # last 10 only — keep adapter payload lean
    }

    try:
        url = f"{OPENCLAW_ADAPTER_URL.rstrip('/')}/dispatch"
        log.info("openclaw_bridge: dispatch → agent=%s adapter=%s", agent_key, OPENCLAW_ADAPTER_URL)
        raw = _post(url, payload)
        return _normalize_response(raw, agent_key)
    except Exception as exc:
        log.error("openclaw_bridge: dispatch failed for %s — %s; falling back to llm_caller",
                  agent_name, exc)
        return _fallback.call(system_prompt, messages)


# ── Helpers ───────────────────────────────────────────────────────────────────

def _post(url: str, payload: dict) -> dict:
    headers = {"Content-Type": "application/json"}
    if OPENCLAW_ADAPTER_KEY:
        headers["Authorization"] = f"Bearer {OPENCLAW_ADAPTER_KEY}"
    resp = requests.post(url, json=payload, headers=headers, timeout=_TIMEOUT)
    resp.raise_for_status()
    return resp.json()


def _normalize_response(raw: dict, agent_key: str) -> dict[str, Any]:
    """
    Normalize adapter response to MAE JSON schema.

    The adapter should return the agent's output directly.
    We try to parse it as MAE JSON; if not, we wrap it as RUNNING.
    """
    # Adapter may return { "content": "..." } or the MAE JSON directly
    content = raw.get("content") if isinstance(raw, dict) else None

    # If the adapter returned MAE JSON directly (no "content" wrapper), use as-is
    if isinstance(raw, dict) and "status" in raw:
        log.debug("openclaw_bridge: response is valid MAE JSON")
        return raw

    # If wrapped in "content", try to parse that
    if content:
        try:
            parsed = json.loads(content)
            if isinstance(parsed, dict) and "status" in parsed:
                log.debug("openclaw_bridge: content field contains valid MAE JSON")
                return parsed
        except (json.JSONDecodeError, TypeError):
            pass

    # Free-text fallback — wrap as RUNNING so harness can continue
    text = content or str(raw)
    log.warning("openclaw_bridge: %s returned non-JSON, wrapping as RUNNING", agent_key)
    return {
        "status":       "RUNNING",
        "action_taken": text[:500] if text else "(no response)",
        "tool_calls":   [],
        "evidence": {
            "run_id":        f"ocbridge-{agent_key.lower()}",
            "log_summary":   text[:200] if text else "(empty)",
            "artifact_link": None,
            "writeback_ts":  None,
        },
        "next_step":          "Continue executing based on agent output above.",
        "needs_human":        False,
        "blocked_reason":     None,
        "next_recovery_step": None,
    }
