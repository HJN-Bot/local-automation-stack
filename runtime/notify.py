"""
Notification dispatcher — Discord bot (primary) + Feishu App OpenAPI (visible collab).
Only called by the harness on BLOCKED or DONE events (and task start / heartbeat).

Discord: uses Bot Token + channel_id  (not webhook URL)
Feishu:  uses App ID + App Secret to get access token, then sends interactive card
         supports threading via root_id — each task gets its own thread
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

# Agent visual identity for Feishu cards
_AGENT_STYLE: dict[str, dict[str, str]] = {
    "ANDREW": {"color": "blue",   "icon": "🧠", "label": "Andrew · SAM"},
    "SAM":    {"color": "blue",   "icon": "🧠", "label": "Andrew · SAM"},
    "REX":    {"color": "orange", "icon": "⚙️", "label": "Rex · FORGE"},
    "FORGE":  {"color": "orange", "icon": "⚙️", "label": "Rex · FORGE"},
    "LULU":   {"color": "purple", "icon": "✏️",  "label": "Lulu · INK"},
    "INK":    {"color": "purple", "icon": "✏️",  "label": "Lulu · INK"},
    "ALEX":   {"color": "green",  "icon": "🌿", "label": "Alex · AUX"},
    "AUX":    {"color": "green",  "icon": "🌿", "label": "Alex · AUX"},
    "LENS":   {"color": "wathet", "icon": "🔍", "label": "LENS · QA"},
    "SWEEP":  {"color": "grey",   "icon": "🧹", "label": "SWEEP · GC"},
}

_MSG_PREFIX: dict[str, str] = {
    "TASK_START": "🚀",
    "HEARTBEAT":  "🟡",
    "BLOCKED":    "🔴",
    "DONE":       "✅",
    "HANDOFF":    "🔁",
    "REVIEW":     "🟠",
}


# ── Public API ────────────────────────────────────────────────────────────────

def send_task_start(
    task_id: str,
    goal: str,
    owner_agent: str = "SAM",
    eta: str = "—",
) -> str | None:
    """
    Post the task anchor message to Feishu, creating a new thread.
    Returns the feishu message_id (use as thread_id for subsequent replies).
    """
    ts = _now()
    style = _agent_style(owner_agent)
    title = f"{style['icon']} {style['label']} · 任务已锁定"
    fields = {
        "任务ID": task_id,
        "目标": goal,
        "ETA": eta,
        "发起时间": ts,
    }
    card = _build_card(title, style["color"], "TASK_START", fields)
    return _send_feishu_card(card, thread_id=None)


def send_heartbeat(
    running_count: int,
    blocked_count: int,
    thread_id: str | None = None,
) -> None:
    ts = _now()
    title = "🟡 Heartbeat · MAE Harness"
    fields = {
        "RUNNING": str(running_count),
        "BLOCKED": str(blocked_count),
        "时间": ts,
    }
    card = _build_card(title, "wathet", "HEARTBEAT", fields)
    _dispatch_card(title, card, thread_id)


def send_blocked(
    task_id: str,
    record_id: str,
    blocked_reason: str,
    next_recovery_step: str | None,
    owner_agent: str = "SAM",
    thread_id: str | None = None,
) -> None:
    ts = _now()
    style = _agent_style(owner_agent)
    title = f"{style['icon']} {style['label']} · BLOCKED"
    fields = {
        "任务ID": task_id,
        "Record": record_id,
        "阻塞原因": blocked_reason,
        "恢复方案": next_recovery_step or "— 未指定 —",
        "时间": ts,
    }
    card = _build_card(title, "red", "BLOCKED", fields)
    _dispatch_card(title, card, thread_id)

    # Discord: keep plain-text embed as backup
    body = (
        f"**Task:** `{task_id}`\n"
        f"**Record:** `{record_id}`\n"
        f"**Agent:** {owner_agent}\n"
        f"**Reason:** {blocked_reason}\n"
        f"**Recovery:** {next_recovery_step or '— not specified —'}\n"
        f"**Time:** {ts}"
    )
    _send_discord(f"[BLOCKED] {task_id}", body, color=0xE74C3C)


def send_done(
    task_id: str,
    record_id: str,
    evidence: dict,
    owner_agent: str = "SAM",
    thread_id: str | None = None,
) -> None:
    ts = _now()
    style = _agent_style(owner_agent)
    title = f"{style['icon']} {style['label']} · DONE"
    fields = {
        "任务ID": task_id,
        "run_id": evidence.get("run_id", "?"),
        "摘要": evidence.get("log_summary", "—"),
        "产出物": evidence.get("artifact_link") or "—",
        "时间": ts,
    }
    card = _build_card(title, "green", "DONE", fields)
    _dispatch_card(title, card, thread_id)

    # Discord: keep plain-text embed as backup
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
    _send_discord(f"[DONE] {task_id}", body, color=0x2ECC71)


def send_agent_update(
    thread_id: str,
    agent_name: str,
    msg_type: str,
    title: str,
    fields: dict[str, str],
) -> None:
    """
    Post an agent update card into an existing Feishu thread.
    msg_type: "HEARTBEAT" | "BLOCKED" | "DONE" | "HANDOFF" | "REVIEW"
    thread_id: feishu message_id returned by send_task_start()
    """
    style = _agent_style(agent_name)
    prefix = _MSG_PREFIX.get(msg_type, "📌")
    card_title = f"{prefix} {style['label']} · {title}"
    color_map = {
        "HEARTBEAT": "wathet",
        "BLOCKED":   "red",
        "DONE":      "green",
        "HANDOFF":   "orange",
        "REVIEW":    "yellow",
    }
    color = color_map.get(msg_type, "blue")
    card = _build_card(card_title, color, msg_type, fields)
    _send_feishu_card(card, thread_id=thread_id)


# ── Card builder ──────────────────────────────────────────────────────────────

def _build_card(
    title: str,
    color: str,
    msg_type: str,
    fields: dict[str, str],
) -> dict:
    """Build a Feishu interactive card (schema 2.0)."""
    elements: list[dict] = []

    # Field rows — pair them into 2-column layout
    keys = list(fields.keys())
    for i in range(0, len(keys), 2):
        row_fields = []
        for k in keys[i:i+2]:
            row_fields.append({
                "is_short": True,
                "text": {
                    "tag": "lark_md",
                    "content": f"**{k}**\n{fields[k]}",
                },
            })
        elements.append({"tag": "div", "fields": row_fields})

    elements.append({"tag": "hr"})
    elements.append({
        "tag": "note",
        "elements": [{"tag": "plain_text", "content": _now()}],
    })

    return {
        "schema": "2.0",
        "config": {"wide_screen_mode": True},
        "header": {
            "title": {"tag": "plain_text", "content": title},
            "template": color,
        },
        "body": {"elements": elements},
    }


# ── Internal dispatch ─────────────────────────────────────────────────────────

def _dispatch_card(title: str, card: dict, thread_id: str | None) -> None:
    _send_feishu_card(card, thread_id=thread_id)


def _agent_style(agent_name: str) -> dict[str, str]:
    key = agent_name.upper()
    return _AGENT_STYLE.get(key, {"color": "grey", "icon": "🤖", "label": agent_name})


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")


# ── Feishu ────────────────────────────────────────────────────────────────────

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


def _send_feishu_card(card: dict, thread_id: str | None = None) -> str | None:
    """
    Send an interactive card to Feishu chat.
    If thread_id is provided, replies into that thread (root_id).
    Returns the message_id on success (use as thread_id for follow-ups).
    """
    if not (FEISHU_APP_ID and FEISHU_APP_SECRET and FEISHU_NOTIFY_CHAT_ID):
        log.debug("notify: Feishu creds not set, skipping card")
        return None

    token = _get_feishu_token()
    if not token:
        return None

    url = f"{_FEISHU_API}/im/v1/messages?receive_id_type=chat_id"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type":  "application/json",
    }
    payload: dict = {
        "receive_id": FEISHU_NOTIFY_CHAT_ID,
        "msg_type":   "interactive",
        "content":    json.dumps(card),
    }
    if thread_id:
        payload["root_id"] = thread_id  # reply into existing thread

    try:
        resp = requests.post(url, json=payload, headers=headers, timeout=_TIMEOUT)
        resp.raise_for_status()
        data = resp.json()
        msg_id = data.get("data", {}).get("message_id")
        log.info("notify: Feishu card sent (msg_id=%s)", msg_id)
        return msg_id
    except Exception as exc:
        log.error("notify: Feishu card failed — %s", exc)
        return None


# ── Discord ───────────────────────────────────────────────────────────────────

def _send_discord(title: str, body: str, color: int = 0x95A5A6) -> None:
    """Send an embed message via Discord Bot API."""
    if not (DISCORD_BOT_TOKEN and DISCORD_NOTIFY_CHANNEL_ID):
        log.debug("notify: Discord creds not set, skipping")
        return

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
