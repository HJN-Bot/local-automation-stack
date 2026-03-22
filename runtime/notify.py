"""
Notification dispatcher — Discord bot (primary) + Feishu App OpenAPI (backup).
Only called by the harness on BLOCKED or DONE events.
Fire-and-forget: logs errors but never raises.

Discord: uses Bot Token + channel_id  (not webhook URL)
Feishu:  uses App ID + App Secret to get access token, then sends message
"""
from __future__ import annotations

import json
import logging
from datetime import datetime, timezone

import requests

from runtime.config import (
    DISCORD_BOT_TOKEN,
    DISCORD_NOTIFY_CHANNEL_ID,
    FEISHU_APP_ID,
    FEISHU_APP_SECRET,
    FEISHU_NOTIFY_CHAT_ID,
)

log = logging.getLogger(__name__)

_TIMEOUT = 8  # seconds
_DISCORD_API = "https://discord.com/api/v10"
_FEISHU_API  = "https://open.feishu.cn/open-apis"


# ── Public API ────────────────────────────────────────────────────────────────

def send_blocked(
    task_id: str,
    record_id: str,
    blocked_reason: str,
    next_recovery_step: str | None,
    owner_agent: str = "SAM",
) -> None:
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    title = f"[BLOCKED] {task_id}"
    body = (
        f"**Task:** `{task_id}`\n"
        f"**Record:** `{record_id}`\n"
        f"**Agent:** {owner_agent}\n"
        f"**Reason:** {blocked_reason}\n"
        f"**Recovery:** {next_recovery_step or '— not specified —'}\n"
        f"**Time:** {ts}"
    )
    _dispatch(title, body, color=0xE74C3C)


def send_done(
    task_id: str,
    record_id: str,
    evidence: dict,
    owner_agent: str = "SAM",
) -> None:
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    title = f"[DONE] {task_id}"
    artifact = evidence.get("artifact_link") or "—"
    body = (
        f"**Task:** `{task_id}`\n"
        f"**Record:** `{record_id}`\n"
        f"**Agent:** {owner_agent}\n"
        f"**run_id:** `{evidence.get('run_id', '?')}`\n"
        f"**Artifact:** {artifact}\n"
        f"**Summary:** {evidence.get('log_summary', '—')}\n"
        f"**Time:** {ts}"
    )
    _dispatch(title, body, color=0x2ECC71)


def send_heartbeat(running_count: int, blocked_count: int) -> None:
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    title = "[Heartbeat] MAE Harness"
    body = (
        f"**RUNNING:** {running_count}  |  **BLOCKED:** {blocked_count}\n"
        f"**Time:** {ts}"
    )
    _dispatch(title, body, color=0x3498DB)


# ── Internal ──────────────────────────────────────────────────────────────────

def _dispatch(title: str, body: str, color: int = 0x95A5A6) -> None:
    if DISCORD_BOT_TOKEN and DISCORD_NOTIFY_CHANNEL_ID:
        _send_discord(title, body, color)
    else:
        log.debug("notify: Discord creds not set, skipping")

    if FEISHU_APP_ID and FEISHU_APP_SECRET and FEISHU_NOTIFY_CHAT_ID:
        _send_feishu(title, body)
    else:
        log.debug("notify: Feishu creds not set, skipping")


def _send_discord(title: str, body: str, color: int) -> None:
    """Send an embed message via Discord Bot API."""
    payload = {
        "embeds": [
            {
                "title":       title,
                "description": body,
                "color":       color,
            }
        ]
    }
    url = f"{_DISCORD_API}/channels/{DISCORD_NOTIFY_CHANNEL_ID}/messages"
    headers = {
        "Authorization": f"Bot {DISCORD_BOT_TOKEN}",
        "Content-Type":  "application/json",
    }
    try:
        resp = requests.post(url, json=payload, headers=headers, timeout=_TIMEOUT)
        resp.raise_for_status()
        log.info("notify: Discord sent (%s)", title)
    except Exception as exc:
        log.error("notify: Discord failed — %s", exc)


def _get_feishu_token() -> str | None:
    """Fetch Feishu tenant_access_token using app credentials."""
    url = f"{_FEISHU_API}/auth/v3/tenant_access_token/internal"
    payload = {"app_id": FEISHU_APP_ID, "app_secret": FEISHU_APP_SECRET}
    try:
        resp = requests.post(url, json=payload, timeout=_TIMEOUT)
        resp.raise_for_status()
        data = resp.json()
        token = data.get("tenant_access_token")
        if not token:
            log.error("notify: Feishu token missing in response: %s", data)
        return token
    except Exception as exc:
        log.error("notify: Feishu token fetch failed — %s", exc)
        return None


def _send_feishu(title: str, body: str) -> None:
    """Send a text message to a Feishu chat via App OpenAPI."""
    token = _get_feishu_token()
    if not token:
        return

    url = f"{_FEISHU_API}/im/v1/messages?receive_id_type=chat_id"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type":  "application/json",
    }
    payload = {
        "receive_id": FEISHU_NOTIFY_CHAT_ID,
        "msg_type":   "text",
        "content":    json.dumps({"text": f"{title}\n\n{body}"}),
    }
    try:
        resp = requests.post(url, json=payload, headers=headers, timeout=_TIMEOUT)
        resp.raise_for_status()
        log.info("notify: Feishu sent (%s)", title)
    except Exception as exc:
        log.error("notify: Feishu failed — %s", exc)
