#!/usr/bin/env python3
"""Sync Active Threads from Airtable (Ideas+Tasks) into dashboard/index.html.

Selection policy:
- Recently updated items from the last 14 days
- All Doing items, even if they have not been touched recently
- Explicit long-running mainline ToDo items, so paused-but-important work does not
  disappear from the dashboard after OpenClaw downtime or quiet periods

Reads secrets from:
  /Users/jianan/.openclaw/secrets/airtable_token
  /Users/jianan/.openclaw/secrets/airtable_base

Tables (from your OpenAPI spec):
  Tasks:   tblpbkdMcmNaYSfzp
  Ideas:   tbldGXAvoU1jP0CJo

Output target:
  ~/.openclaw/workspace/dashboard/index.html  (threadsData JSON)
"""

from __future__ import annotations

import json
import os
import re
import sys
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import requests

# local helper
# (kept standalone so it can run without package setup)

SECRETS_DIR = Path("/Users/jianan/.openclaw/secrets")
TOKEN_PATH = SECRETS_DIR / "airtable_token"
BASE_PATH = SECRETS_DIR / "airtable_base"

BASE = BASE_PATH.read_text(encoding="utf-8").strip()
TOKEN = TOKEN_PATH.read_text(encoding="utf-8").strip()

API = "https://api.airtable.com/v0"

TASKS_TABLE = "tblpbkdMcmNaYSfzp"
IDEAS_TABLE = "tbldGXAvoU1jP0CJo"

DASHBOARD = Path("/Users/jianan/.openclaw/workspace/dashboard/index.html")


@dataclass
class ThreadItem:
    title: str
    related: str
    summary: str
    status: str
    date: str  # YYYY-MM-DD
    priority_rank: int


def _get(url: str, params: Dict[str, Any]) -> Dict[str, Any]:
    headers = {"Authorization": f"Bearer {TOKEN}"}
    r = requests.get(url, headers=headers, params=params, timeout=30)
    r.raise_for_status()
    return r.json()


def _fetch_all(table: str, max_records: int = 200) -> List[Dict[str, Any]]:
    url = f"{API}/{BASE}/{table}"
    out: List[Dict[str, Any]] = []
    offset: Optional[str] = None
    while True:
        params: Dict[str, Any] = {"pageSize": 100}
        if offset:
            params["offset"] = offset
        data = _get(url, params)
        out.extend(data.get("records", []))
        offset = data.get("offset")
        if not offset or len(out) >= max_records:
            return out[:max_records]


def _prio_rank(p: Optional[str]) -> int:
    if not p:
        return 2
    p = p.lower()
    return {"high": 0, "medium": 1, "low": 2}.get(p, 2)


def _safe_date(s: Optional[str]) -> Optional[datetime]:
    if not s:
        return None
    s = str(s).strip()
    # try YYYY-MM-DD
    try:
        return datetime.strptime(s, "%Y-%m-%d").replace(tzinfo=timezone.utc)
    except Exception:
        pass
    # try ISO
    try:
        return datetime.fromisoformat(s.replace("Z", "+00:00")).astimezone(timezone.utc)
    except Exception:
        return None


def _within_14d(dt: datetime) -> bool:
    now = datetime.now(timezone.utc)
    return dt >= (now - timedelta(days=14))


def _within_90d(dt: datetime) -> bool:
    now = datetime.now(timezone.utc)
    return dt >= (now - timedelta(days=90))


MAINLINE_KEYWORDS = (
    "mae主线",
    "ai主线",
    "内容采集流水线",
    "视频生产流水线",
    "openclaw 从 ec2 迁移到 mini mac",
)


def _is_active_thread(title: str, summary: str, status: str, dt: datetime) -> bool:
    """Return whether an item should stay visible in Active Threads.

    The old rule only showed items updated in the last 14 days. That hid real
    unfinished mainlines after a quiet period. Keep the recent rule, but always
    include Doing and named strategic ToDo mainlines.
    """
    if _within_14d(dt):
        return True
    st = (status or "").strip().lower()
    title_l = (title or "").lower()
    if st == "doing" and (_within_90d(dt) or any(k in title_l for k in MAINLINE_KEYWORDS)):
        return True
    return st in {"todo", "to do", "to-do"} and any(k in title_l for k in MAINLINE_KEYWORDS)


def build_threads() -> List[ThreadItem]:
    tasks = _fetch_all(TASKS_TABLE)
    ideas = _fetch_all(IDEAS_TABLE)

    threads: List[ThreadItem] = []

    # Tasks
    for r in tasks:
        f = r.get("fields", {})
        title = f.get("Tasks")
        if not title:
            continue
        dt = _safe_date(f.get("Update_At"))
        if not dt:
            continue
        status = f.get("State") or "ToDo"
        related = f.get("Field") or "Work"
        summary = (f.get("Desc") or "").strip()
        summary = re.sub(r"\s+", " ", summary)
        if not _is_active_thread(str(title), summary, str(status), dt):
            continue
        pr = _prio_rank(f.get("Priority"))
        threads.append(
            ThreadItem(
                title=str(title).strip(),
                related=str(related).strip(),
                summary=summary[:160] + ("…" if len(summary) > 160 else ""),
                status=str(status).strip(),
                date=dt.strftime("%Y-%m-%d"),
                priority_rank=pr,
            )
        )

    # Ideas
    for r in ideas:
        f = r.get("fields", {})
        title = f.get("Name")
        if not title:
            continue
        dt = _safe_date(f.get("Last Progress")) or _safe_date(f.get("Start"))
        if not dt:
            continue
        status = f.get("Status") or "Todo"
        related = "Idea"
        summary = (f.get("Notes") or "").strip()
        summary = re.sub(r"\s+", " ", summary)
        if not _is_active_thread(str(title), summary, str(status), dt):
            continue
        pr = 1  # default Medium for ideas
        threads.append(
            ThreadItem(
                title=str(title).strip(),
                related=str(related),
                summary=summary[:160] + ("…" if len(summary) > 160 else ""),
                status=str(status).strip(),
                date=dt.strftime("%Y-%m-%d"),
                priority_rank=pr,
            )
        )

    # sort: date desc, then priority
    threads.sort(key=lambda x: (x.date, -1 * (2 - x.priority_rank)), reverse=True)

    # dedupe by title
    seen = set()
    uniq: List[ThreadItem] = []
    for t in threads:
        if t.title in seen:
            continue
        seen.add(t.title)
        uniq.append(t)

    return uniq[:8]


def update_dashboard(threads: List[ThreadItem]) -> None:
    html = DASHBOARD.read_text(encoding="utf-8")
    payload = [
        {
            "title": t.title,
            "related": t.related,
            "summary": t.summary,
            "status": t.status,
            "date": t.date,
        }
        for t in threads
    ]
    new_json = json.dumps(payload, ensure_ascii=False)

    # Replace threadsData JSON
    pat = re.compile(r'(<script type="application/json" id="threadsData">)([\s\S]*?)(</script>)')
    m = pat.search(html)
    if not m:
        raise RuntimeError("threadsData block not found")
    html = pat.sub(r"\1" + new_json + r"\3", html, count=1)

    # Update header timestamp
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M")
    html = re.sub(r'<div class="update-time">[^<]*更新</div>', f'<div class="update-time">{ts} 更新</div>', html, count=1)

    DASHBOARD.write_text(html, encoding="utf-8")


def main() -> None:
    threads = build_threads()
    update_dashboard(threads)
    print(json.dumps({"ok": True, "count": len(threads), "threads": [t.title for t in threads]}, ensure_ascii=False))


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(json.dumps({"ok": False, "error": str(e)}, ensure_ascii=False))
        raise
