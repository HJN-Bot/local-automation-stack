"""
Notification dispatcher — Discord bot (primary) + Feishu App OpenAPI (visible collab).

Feishu design:
  - Each agent uses its own Feishu self-built app → distinct avatar + name in chat.
  - Per-agent credentials (FEISHU_APP_ID_ANDREW etc.) take precedence.
  - Falls back to FEISHU_APP_ID / FEISHU_APP_SECRET if agent-specific ones aren't set.
  - tenant_access_token is cached per app_id (2-hour TTL) to avoid redundant API calls.
  - Threading: send_task_start() creates the root message and returns its message_id.
    Pass that as thread_id to subsequent calls to group messages into one thread.
  - thread_id=None → message posted as standalone; warning is logged but task continues.

Discord: uses Bot Token + channel_id (backup channel, plain-text embeds).
"""
from __future__ import annotations

import json
import logging
import time
from datetime import datetime, timezone
from typing import NamedTuple

import requests

from runtime.config import (
    DISCORD_BOT_TOKEN,
    DISCORD_NOTIFY_CHANNEL_ID,
    FEISHU_APP_ID,
    FEISHU_APP_SECRET,
    FEISHU_APP_ID_ANDREW, FEISHU_APP_SECRET_ANDREW,
    FEISHU_APP_ID_REX,    FEISHU_APP_SECRET_REX,
    FEISHU_APP_ID_LULU,   FEISHU_APP_SECRET_LULU,
    FEISHU_APP_ID_ALEX,   FEISHU_APP_SECRET_ALEX,
    FEISHU_NOTIFY_CHAT_ID,
)

log = logging.getLogger(__name__)

_TIMEOUT = 8  # seconds
_DISCORD_API = "https://discord.com/api/v10"
_FEISHU_API  = "https://open.feishu.cn/open-apis"
_TOKEN_TTL   = 7000  # seconds — Feishu tokens last 7200s; refresh 200s early


# ── Agent → Feishu app credentials ───────────────────────────────────────────

class _BotCreds(NamedTuple):
    app_id: str
    app_secret: str
    color: str
    icon: str
    display_name: str


# Maps any agent name variant to its Feishu app + visual style.
# Falls back to the default bot when per-agent creds are missing.
_AGENT_BOT: dict[str, _BotCreds] = {
    "ANDREW": _BotCreds(FEISHU_APP_ID_ANDREW, FEISHU_APP_SECRET_ANDREW, "blue",   "🧠", "Andrew · SAM"),
    "SAM":    _BotCreds(FEISHU_APP_ID_ANDREW, FEISHU_APP_SECRET_ANDREW, "blue",   "🧠", "Andrew · SAM"),
    "REX":    _BotCreds(FEISHU_APP_ID_REX,    FEISHU_APP_SECRET_REX,    "orange", "⚙️",  "Rex · FORGE"),
    "FORGE":  _BotCreds(FEISHU_APP_ID_REX,    FEISHU_APP_SECRET_REX,    "orange", "⚙️",  "Rex · FORGE"),
    "LULU":   _BotCreds(FEISHU_APP_ID_LULU,   FEISHU_APP_SECRET_LULU,   "purple", "✏️",  "Lulu · INK"),
    "INK":    _BotCreds(FEISHU_APP_ID_LULU,   FEISHU_APP_SECRET_LULU,   "purple", "✏️",  "Lulu · INK"),
    "ALEX":   _BotCreds(FEISHU_APP_ID_ALEX,   FEISHU_APP_SECRET_ALEX,   "green",  "🌿", "Alex · AUX"),
    "AUX":    _BotCreds(FEISHU_APP_ID_ALEX,   FEISHU_APP_SECRET_ALEX,   "green",  "🌿", "Alex · AUX"),
    "LENS":   _BotCreds(FEISHU_APP_ID,        FEISHU_APP_SECRET,        "wathet", "🔍", "LENS · QA"),
    "SWEEP":  _BotCreds(FEISHU_APP_ID,        FEISHU_APP_SECRET,        "grey",   "🧹", "SWEEP · GC"),
}

_DEFAULT_BOT = _BotCreds(FEISHU_APP_ID, FEISHU_APP_SECRET, "grey", "🤖", "MAE-Bot")

_MSG_COLORS: dict[str, str] = {
    "TASK_START": "blue",
    "HEARTBEAT":  "wathet",
    "BLOCKED":    "red",
    "DONE":       "green",
    "HANDOFF":    "orange",
    "REVIEW":     "yellow",
}

_MSG_ICONS: dict[str, str] = {
    "TASK_START": "🚀",
    "HEARTBEAT":  "🟡",
    "BLOCKED":    "🔴",
    "DONE":       "✅",
    "HANDOFF":    "🔁",
    "REVIEW":     "🟠",
}


# ── Token cache (per app_id) ──────────────────────────────────────────────────

# { app_id: (token, expire_at_epoch) }
_token_cache: dict[str, tuple[str, float]] = {}


def _get_feishu_token(app_id: str, app_secret: str) -> str | None:
    """Return a valid tenant_access_token, using a per-app cache."""
    now = time.monotonic()
    cached = _token_cache.get(app_id)
    if cached and now < cached[1]:
        return cached[0]

    url = f"{_FEISHU_API}/auth/v3/tenant_access_token/internal"
    try:
        resp = requests.post(
            url,
            json={"app_id": app_id, "app_secret": app_secret},
            timeout=_TIMEOUT,
        )
        resp.raise_for_status()
        data = resp.json()
        token = data.get("tenant_access_token")
        if not token:
            log.error("notify: Feishu token missing (app_id=%s): %s", app_id, data)
            return None
        _token_cache[app_id] = (token, now + _TOKEN_TTL)
        return token
    except Exception as exc:
        log.error("notify: Feishu token fetch failed (app_id=%s) — %s", app_id, exc)
        return None


# ── Bot credential resolution ─────────────────────────────────────────────────

def _resolve_bot(agent_name: str) -> _BotCreds:
    """
    Return the Feishu bot credentials for the given agent.
    If per-agent creds are not configured, falls back to the default bot.
    """
    creds = _AGENT_BOT.get(agent_name.upper(), _DEFAULT_BOT)
    if not creds.app_id:
        log.debug("notify: no per-agent Feishu app for %s, using default bot", agent_name)
        return _BotCreds(
            FEISHU_APP_ID, FEISHU_APP_SECRET,
            creds.color, creds.icon, creds.display_name,
        )
    return creds


# ── Public API ────────────────────────────────────────────────────────────────

def send_task_start(
    task_id: str,
    goal: str,
    owner_agent: str = "SAM",
    eta: str = "—",
) -> str | None:
    """
    Post the task anchor card to Feishu (as the task root / thread opener).
    Returns the feishu message_id — store this as feishu_thread_id in Airtable
    and pass it to all subsequent calls for this task.
    """
    bot = _resolve_bot(owner_agent)
    title = f"{bot.icon} {bot.display_name} · 🚀 任务已锁定"
    card = _build_card(title, "blue", {
        "任务ID": task_id,
        "目标":   goal,
        "ETA":    eta,
        "发起时间": _now(),
    })
    msg_id = _send_feishu_card(card, bot, thread_id=None)
    if not msg_id:
        log.warning("notify: send_task_start failed for %s — thread will be missing", task_id)
    return msg_id


def send_agent_update(
    thread_id: str | None,
    agent_name: str,
    msg_type: str,
    title: str,
    fields: dict[str, str],
) -> None:
    """
    Post an agent progress card, optionally threaded under a root message.
    msg_type: "HEARTBEAT" | "BLOCKED" | "DONE" | "HANDOFF" | "REVIEW"
    thread_id: feishu_thread_id from send_task_start(); None → standalone message.
    """
    if thread_id is None:
        log.warning("notify: send_agent_update called with thread_id=None (agent=%s, type=%s) "
                    "— posting as standalone message", agent_name, msg_type)
    bot = _resolve_bot(agent_name)
    icon = _MSG_ICONS.get(msg_type, "📌")
    color = _MSG_COLORS.get(msg_type, "blue")
    card_title = f"{icon} {bot.display_name} · {title}"
    card = _build_card(card_title, color, fields)
    _send_feishu_card(card, bot, thread_id=thread_id)


def send_heartbeat(
    running_count: int,
    blocked_count: int,
    thread_id: str | None = None,
) -> None:
    bot = _resolve_bot("SAM")
    title = f"🟡 {bot.display_name} · Heartbeat"
    card = _build_card(title, "wathet", {
        "RUNNING": str(running_count),
        "BLOCKED": str(blocked_count),
        "时间":    _now(),
    })
    _send_feishu_card(card, bot, thread_id=thread_id)


def send_blocked(
    task_id: str,
    record_id: str,
    blocked_reason: str,
    next_recovery_step: str | None,
    owner_agent: str = "SAM",
    thread_id: str | None = None,
) -> None:
    if thread_id is None:
        log.warning("notify: send_blocked without thread_id (task=%s)", task_id)
    bot = _resolve_bot(owner_agent)
    title = f"🔴 {bot.display_name} · BLOCKED"
    card = _build_card(title, "red", {
        "任务ID":  task_id,
        "Record":  record_id,
        "阻塞原因": blocked_reason,
        "恢复方案": next_recovery_step or "— 未指定 —",
        "时间":    _now(),
    })
    _send_feishu_card(card, bot, thread_id=thread_id)

    # Discord backup (plain embed)
    _send_discord(
        f"[BLOCKED] {task_id}",
        f"**Agent:** {owner_agent}\n**Reason:** {blocked_reason}\n"
        f"**Recovery:** {next_recovery_step or '—'}\n**Time:** {_now()}",
        color=0xE74C3C,
    )


def send_done(
    task_id: str,
    record_id: str,
    evidence: dict,
    owner_agent: str = "SAM",
    thread_id: str | None = None,
) -> None:
    if thread_id is None:
        log.warning("notify: send_done without thread_id (task=%s)", task_id)
    bot = _resolve_bot(owner_agent)
    title = f"✅ {bot.display_name} · DONE"
    card = _build_card(title, "green", {
        "任务ID":  task_id,
        "run_id":  evidence.get("run_id", "?"),
        "摘要":    evidence.get("log_summary", "—"),
        "产出物":  evidence.get("artifact_link") or "—",
        "时间":    _now(),
    })
    _send_feishu_card(card, bot, thread_id=thread_id)

    # Discord backup (plain embed)
    _send_discord(
        f"[DONE] {task_id}",
        f"**Agent:** {owner_agent}\n**run_id:** `{evidence.get('run_id', '?')}`\n"
        f"**Artifact:** {evidence.get('artifact_link') or '—'}\n"
        f"**Summary:** {evidence.get('log_summary', '—')}\n**Time:** {_now()}",
        color=0x2ECC71,
    )


# ── Card builder ──────────────────────────────────────────────────────────────

def _build_card(title: str, color: str, fields: dict[str, str]) -> dict:
    """Build a Feishu Interactive Card (schema 2.0), 2-column field layout."""
    elements: list[dict] = []
    keys = list(fields.keys())
    for i in range(0, len(keys), 2):
        row = []
        for k in keys[i : i + 2]:
            row.append({
                "is_short": True,
                "text": {"tag": "lark_md", "content": f"**{k}**\n{fields[k]}"},
            })
        elements.append({"tag": "div", "fields": row})

    elements += [
        {"tag": "hr"},
        {"tag": "note", "elements": [{"tag": "plain_text", "content": _now()}]},
    ]

    return {
        "schema": "2.0",
        "config": {"wide_screen_mode": True},
        "header": {
            "title": {"tag": "plain_text", "content": title},
            "template": color,
        },
        "body": {"elements": elements},
    }


# ── Feishu send ───────────────────────────────────────────────────────────────

def _send_feishu_card(
    card: dict,
    bot: _BotCreds,
    thread_id: str | None,
) -> str | None:
    """
    Send an interactive card using the given bot's credentials.
    Returns the message_id on success (use as thread_id for replies).
    """
    if not (bot.app_id and bot.app_secret and FEISHU_NOTIFY_CHAT_ID):
        log.debug("notify: Feishu creds not set for bot %s, skipping", bot.display_name)
        return None

    token = _get_feishu_token(bot.app_id, bot.app_secret)
    if not token:
        return None

    payload: dict = {
        "receive_id": FEISHU_NOTIFY_CHAT_ID,
        "msg_type":   "interactive",
        "content":    json.dumps(card),
    }
    if thread_id:
        payload["root_id"] = thread_id  # groups message into existing thread

    try:
        resp = requests.post(
            f"{_FEISHU_API}/im/v1/messages?receive_id_type=chat_id",
            json=payload,
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type":  "application/json",
            },
            timeout=_TIMEOUT,
        )
        resp.raise_for_status()
        msg_id = resp.json().get("data", {}).get("message_id")
        log.info("notify: Feishu card sent by %s (msg_id=%s, thread=%s)",
                 bot.display_name, msg_id, thread_id or "root")
        return msg_id
    except Exception as exc:
        log.error("notify: Feishu card failed (bot=%s) — %s", bot.display_name, exc)
        return None


# ── Discord ───────────────────────────────────────────────────────────────────

def _send_discord(title: str, body: str, color: int = 0x95A5A6) -> None:
    if not (DISCORD_BOT_TOKEN and DISCORD_NOTIFY_CHANNEL_ID):
        log.debug("notify: Discord creds not set, skipping")
        return
    try:
        resp = requests.post(
            f"{_DISCORD_API}/channels/{DISCORD_NOTIFY_CHANNEL_ID}/messages",
            json={"embeds": [{"title": title, "description": body, "color": color}]},
            headers={"Authorization": f"Bot {DISCORD_BOT_TOKEN}", "Content-Type": "application/json"},
            timeout=_TIMEOUT,
        )
        resp.raise_for_status()
        log.info("notify: Discord sent (%s)", title)
    except Exception as exc:
        log.error("notify: Discord failed — %s", exc)


# ── Helpers ───────────────────────────────────────────────────────────────────

def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
