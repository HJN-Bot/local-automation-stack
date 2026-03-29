"""
OpenClaw Bridge — replaces llm_caller.py for agents that run inside OpenClaw.

Two execution paths:
  sessions_send  — send a message to an existing long-lived session (SAM main brain)
  sessions_spawn — create a new isolated sub-agent run (REX / LULU / ALEX / ALEX)

The bridge is a DROP-IN replacement for llm_caller.call():
  - Same input:  system_prompt (str) + messages (list[dict]) + agent_name (str)
  - Same output: structured dict matching MAE JSON schema

Fallback:
  If OPENCLAW_API_URL is not set, or the bridge call fails, the harness
  automatically falls back to runtime/llm_caller.py so nothing breaks during
  the migration period.

Agent → session routing:
  SAM / ANDREW → sessions_send  (preserve long-term context, main brain)
  REX / FORGE  → sessions_spawn (isolated coding run, clean context each time)
  LULU / INK   → sessions_spawn (isolated writing run)
  ALEX / AUX   → sessions_spawn (isolated support run)
"""
from __future__ import annotations

import json
import logging
from typing import Any

import requests

from runtime.config import (
    OPENCLAW_API_URL,
    OPENCLAW_API_KEY,
    OPENCLAW_SESSION_SAM,
    OPENCLAW_SESSION_REX,
    OPENCLAW_SESSION_LULU,
    OPENCLAW_SESSION_ALEX,
)
from runtime import llm_caller as _fallback

log = logging.getLogger(__name__)

_TIMEOUT = 120  # seconds — agent runs can be slow

# Agents that use sessions_send (persistent session, context preserved)
_SEND_AGENTS = {"SAM", "ANDREW"}

# Maps agent name → fixed session ID for sessions_send
_SESSION_MAP: dict[str, str] = {
    "SAM":    OPENCLAW_SESSION_SAM,
    "ANDREW": OPENCLAW_SESSION_SAM,
    "REX":    OPENCLAW_SESSION_REX,
    "FORGE":  OPENCLAW_SESSION_REX,
    "LULU":   OPENCLAW_SESSION_LULU,
    "INK":    OPENCLAW_SESSION_LULU,
    "ALEX":   OPENCLAW_SESSION_ALEX,
    "AUX":    OPENCLAW_SESSION_ALEX,
}


def is_available() -> bool:
    """Return True if OpenClaw bridge is configured and should be used."""
    return bool(OPENCLAW_API_URL and OPENCLAW_API_KEY)


def call(
    system_prompt: str,
    messages: list[dict],
    agent_name: str = "SAM",
) -> dict[str, Any]:
    """
    Route an agent call through OpenClaw, with automatic fallback to llm_caller.

    Args:
        system_prompt: Task-specific instructions for the agent.
        messages:      Conversation history (role/content dicts).
        agent_name:    Which OpenClaw agent to invoke.

    Returns:
        Structured dict in MAE JSON schema (status, action_taken, evidence, ...).
    """
    if not is_available():
        log.debug("openclaw_bridge: not configured, using llm_caller fallback")
        return _fallback.call(system_prompt, messages)

    agent_key = agent_name.upper()

    try:
        if agent_key in _SEND_AGENTS:
            return _sessions_send(agent_key, system_prompt, messages)
        else:
            return _sessions_spawn(agent_key, system_prompt, messages)
    except Exception as exc:
        log.error("openclaw_bridge: call failed for %s — %s; falling back", agent_name, exc)
        return _fallback.call(system_prompt, messages)


# ── sessions_send ─────────────────────────────────────────────────────────────

def _sessions_send(
    agent_key: str,
    system_prompt: str,
    messages: list[dict],
) -> dict[str, Any]:
    """
    Send a message to an existing OpenClaw session and wait for the response.
    Used for SAM (main brain) to preserve long-term context.

    OpenClaw API:
      POST {OPENCLAW_API_URL}/sessions/{session_id}/messages
      Body: { "content": "...", "role": "user" }
      Response: { "id": "...", "content": "...", "role": "assistant" }
    """
    session_id = _SESSION_MAP.get(agent_key)
    if not session_id:
        raise ValueError(f"No session_id configured for agent {agent_key}")

    # Build the user message: system_prompt + conversation so far
    user_content = _build_user_content(system_prompt, messages)

    url = f"{OPENCLAW_API_URL.rstrip('/')}/sessions/{session_id}/messages"
    payload = {
        "content": user_content,
        "role":    "user",
    }

    log.info("openclaw_bridge: sessions_send → session=%s", session_id[:8] + "...")
    resp = _post(url, payload)
    return _normalize_response(resp, agent_key)


# ── sessions_spawn ────────────────────────────────────────────────────────────

def _sessions_spawn(
    agent_key: str,
    system_prompt: str,
    messages: list[dict],
) -> dict[str, Any]:
    """
    Spawn a new isolated sub-agent run in OpenClaw.
    Used for REX / LULU / ALEX — clean context, parallel-safe.

    OpenClaw API:
      POST {OPENCLAW_API_URL}/sessions/spawn
      Body: {
        "agent_id":      "rex",
        "system_prompt": "...",
        "messages":      [...],
        "wait":          true      ← block until run completes
      }
      Response: {
        "session_id": "...",
        "run_id":     "...",
        "output":     { "content": "..." }
      }
    """
    # Map internal agent key to OpenClaw agent_id
    # Adjust these to match your actual OpenClaw agent IDs
    agent_id_map = {
        "REX":   "rex",
        "FORGE": "rex",
        "LULU":  "lulu",
        "INK":   "lulu",
        "ALEX":  "alex",
        "AUX":   "alex",
    }
    agent_id = agent_id_map.get(agent_key, agent_key.lower())

    url = f"{OPENCLAW_API_URL.rstrip('/')}/sessions/spawn"
    payload = {
        "agent_id":      agent_id,
        "system_prompt": system_prompt,
        "messages":      messages,
        "wait":          True,    # synchronous — block until agent finishes
    }

    log.info("openclaw_bridge: sessions_spawn → agent_id=%s", agent_id)
    resp = _post(url, payload)

    # Spawn response wraps the output — unwrap it
    output = resp.get("output", resp)
    return _normalize_response(output, agent_key)


# ── Helpers ───────────────────────────────────────────────────────────────────

def _post(url: str, payload: dict) -> dict:
    headers = {
        "Authorization": f"Bearer {OPENCLAW_API_KEY}",
        "Content-Type":  "application/json",
    }
    resp = requests.post(url, json=payload, headers=headers, timeout=_TIMEOUT)
    resp.raise_for_status()
    return resp.json()


def _build_user_content(system_prompt: str, messages: list[dict]) -> str:
    """
    Collapse system_prompt + message history into a single user message string.
    OpenClaw sessions already have their own system prompt; this carries task context.
    """
    parts = [f"[TASK CONTEXT]\n{system_prompt}"]
    for m in messages[-10:]:   # last 10 messages only (avoid flooding context)
        role = m.get("role", "user")
        content = m.get("content", "")
        parts.append(f"[{role.upper()}]\n{content}")
    return "\n\n---\n\n".join(parts)


def _normalize_response(raw: dict, agent_key: str) -> dict[str, Any]:
    """
    Normalize OpenClaw response to MAE JSON schema.

    OpenClaw returns free-form text or JSON depending on agent config.
    We try to parse it as MAE JSON first; if not, we wrap it.
    """
    content = raw.get("content", "")

    # Try to parse as MAE structured JSON directly
    try:
        parsed = json.loads(content)
        if isinstance(parsed, dict) and "status" in parsed:
            log.debug("openclaw_bridge: response is valid MAE JSON")
            return parsed
    except (json.JSONDecodeError, TypeError):
        pass

    # If the agent returned free text, wrap it in a RUNNING response
    # so the harness can continue. Next cycle the agent should produce structured output.
    log.warning(
        "openclaw_bridge: %s returned non-JSON, wrapping as RUNNING", agent_key
    )
    return {
        "status":       "RUNNING",
        "action_taken": content[:500] if content else "(no response)",
        "tool_calls":   [],
        "evidence":     {
            "run_id":        f"ocbridge-{agent_key.lower()}",
            "log_summary":   content[:200] if content else "(empty)",
            "artifact_link": None,
            "writeback_ts":  None,
        },
        "next_step":         "Continue executing based on agent output above.",
        "needs_human":       False,
        "blocked_reason":    None,
        "next_recovery_step": None,
    }
