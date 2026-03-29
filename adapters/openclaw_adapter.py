"""
OpenClaw Adapter — thin HTTP server that bridges MAE into OpenClaw's tool layer.

Deploy this inside the OpenClaw environment (where sessions_send / sessions_spawn
are available as Python-importable tools).

MAE sends:
  POST /dispatch  { agent, system_prompt, messages }

Adapter routes:
  SAM / ANDREW   → sessions_send   (persistent session, long-term memory)
  REX / LULU / ALEX / FORGE / INK / AUX  → sessions_spawn  (isolated run)

Start:
  pip install fastapi uvicorn python-dotenv
  uvicorn adapters.openclaw_adapter:app --host 0.0.0.0 --port 8765

.env (in OpenClaw's environment):
  OPENCLAW_ADAPTER_KEY=<optional bearer token MAE will send>
  OPENCLAW_SESSION_SAM=sess_xxxxxxxxxxxxxxxx
  OPENCLAW_SESSION_REX=sess_xxxxxxxxxxxxxxxx
  OPENCLAW_SESSION_LULU=sess_xxxxxxxxxxxxxxxx
  OPENCLAW_SESSION_ALEX=sess_xxxxxxxxxxxxxxxx
"""
from __future__ import annotations

import logging
import os
from typing import Any

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Request
from pydantic import BaseModel

load_dotenv()

log = logging.getLogger("openclaw_adapter")
logging.basicConfig(level=logging.INFO, format="%(asctime)s  %(levelname)-8s  %(message)s")

# ── OpenClaw tool imports ─────────────────────────────────────────────────────
# TODO: Replace with the actual import path from your OpenClaw Python SDK.
#
# What you need:
#   sessions_send(session_id: str, content: str) -> dict
#     — Sends a user message to an existing persistent session.
#       Returns the assistant's response dict.
#
#   sessions_spawn(agent_id: str, system_prompt: str,
#                  messages: list[dict], wait: bool = True) -> dict
#     — Spawns a new isolated sub-agent run and waits for completion.
#       Returns the run output dict.
#
# Examples (fill in based on your OpenClaw SDK):
#   from openclaw.tools import sessions_send, sessions_spawn
#   from openclaw.client import sessions_send, sessions_spawn
#   from openclaw import sessions_send, sessions_spawn
#
# Until you fill this in, the adapter falls back to stub implementations
# that return a RUNNING response so MAE doesn't crash.

try:
    from openclaw.tools import sessions_send as _sessions_send  # type: ignore[import]
    from openclaw.tools import sessions_spawn as _sessions_spawn  # type: ignore[import]
    _OPENCLAW_AVAILABLE = True
    log.info("openclaw_adapter: OpenClaw tools loaded successfully")
except ImportError:
    _OPENCLAW_AVAILABLE = False
    log.warning("openclaw_adapter: OpenClaw tools not importable — running in STUB mode")

    def _sessions_send(session_id: str, content: str) -> dict:  # type: ignore[misc]
        return {"content": f"[STUB sessions_send] session={session_id[:8]}... received: {content[:80]}"}

    def _sessions_spawn(agent_id: str, system_prompt: str,  # type: ignore[misc]
                        messages: list[dict], wait: bool = True) -> dict:
        return {"output": {"content": f"[STUB sessions_spawn] agent={agent_id} received {len(messages)} messages"}}


# ── Config ────────────────────────────────────────────────────────────────────

ADAPTER_KEY = os.getenv("OPENCLAW_ADAPTER_KEY", "")

# Agent → session ID mapping (read from env)
_SESSION_MAP: dict[str, str] = {
    "SAM":    os.getenv("OPENCLAW_SESSION_SAM",  ""),
    "ANDREW": os.getenv("OPENCLAW_SESSION_SAM",  ""),  # Andrew uses Sam's session
    "REX":    os.getenv("OPENCLAW_SESSION_REX",  ""),
    "FORGE":  os.getenv("OPENCLAW_SESSION_REX",  ""),
    "LULU":   os.getenv("OPENCLAW_SESSION_LULU", ""),
    "INK":    os.getenv("OPENCLAW_SESSION_LULU", ""),
    "ALEX":   os.getenv("OPENCLAW_SESSION_ALEX", ""),
    "AUX":    os.getenv("OPENCLAW_SESSION_ALEX", ""),
}

# Agents that use sessions_send (preserve long-term context)
_SEND_AGENTS = {"SAM", "ANDREW"}

# Maps internal agent key → OpenClaw agent_id used in sessions_spawn
_SPAWN_AGENT_IDS: dict[str, str] = {
    "REX":   "rex",
    "FORGE": "rex",
    "LULU":  "lulu",
    "INK":   "lulu",
    "ALEX":  "alex",
    "AUX":   "alex",
}


# ── App ───────────────────────────────────────────────────────────────────────

app = FastAPI(title="OpenClaw Adapter", version="1.0")


class DispatchRequest(BaseModel):
    agent: str
    system_prompt: str
    messages: list[dict]


def _check_auth(request: Request) -> None:
    """Validate bearer token if OPENCLAW_ADAPTER_KEY is configured."""
    if not ADAPTER_KEY:
        return  # no auth configured, allow all
    auth = request.headers.get("Authorization", "")
    if not auth.startswith("Bearer ") or auth[7:] != ADAPTER_KEY:
        raise HTTPException(status_code=401, detail="Unauthorized")


def _build_send_content(system_prompt: str, messages: list[dict]) -> str:
    """Collapse system_prompt + messages into a single content string for sessions_send."""
    parts = [f"[TASK CONTEXT]\n{system_prompt}"]
    for m in messages:
        role = m.get("role", "user").upper()
        content = m.get("content", "")
        parts.append(f"[{role}]\n{content}")
    return "\n\n---\n\n".join(parts)


@app.post("/dispatch")
async def dispatch(req: DispatchRequest, request: Request) -> dict[str, Any]:
    """
    Route an agent call to the appropriate OpenClaw execution path.

    SAM / ANDREW → sessions_send  (persistent session)
    REX / LULU / ALEX / ... → sessions_spawn  (isolated run)
    """
    _check_auth(request)
    agent_key = req.agent.upper()
    log.info("dispatch: agent=%s send_path=%s", agent_key, agent_key in _SEND_AGENTS)

    if agent_key in _SEND_AGENTS:
        return _do_sessions_send(agent_key, req.system_prompt, req.messages)
    else:
        return _do_sessions_spawn(agent_key, req.system_prompt, req.messages)


def _do_sessions_send(agent_key: str, system_prompt: str, messages: list[dict]) -> dict:
    session_id = _SESSION_MAP.get(agent_key)
    if not session_id:
        raise HTTPException(
            status_code=500,
            detail=f"OPENCLAW_SESSION_{agent_key} not configured in adapter .env",
        )

    content = _build_send_content(system_prompt, messages)
    log.info("sessions_send → session=%s...", session_id[:8])

    # ── Call OpenClaw sessions_send ───────────────────────────────────────────
    # Expected return: { "content": "<assistant reply text or JSON>" }
    # Adjust the call signature if your SDK differs.
    result = _sessions_send(session_id=session_id, content=content)
    return result


def _do_sessions_spawn(agent_key: str, system_prompt: str, messages: list[dict]) -> dict:
    agent_id = _SPAWN_AGENT_IDS.get(agent_key, agent_key.lower())
    log.info("sessions_spawn → agent_id=%s", agent_id)

    # ── Call OpenClaw sessions_spawn ──────────────────────────────────────────
    # Expected return: { "output": { "content": "<reply>" } }  or similar.
    # Adjust the call signature / return unwrapping if your SDK differs.
    result = _sessions_spawn(
        agent_id=agent_id,
        system_prompt=system_prompt,
        messages=messages,
        wait=True,  # synchronous — block until the agent run completes
    )

    # Unwrap spawn output envelope if present
    if isinstance(result, dict) and "output" in result:
        return result["output"]
    return result


@app.get("/health")
async def health() -> dict:
    return {
        "status": "ok",
        "openclaw_available": _OPENCLAW_AVAILABLE,
        "agents_configured": {k: bool(v) for k, v in _SESSION_MAP.items()},
    }
