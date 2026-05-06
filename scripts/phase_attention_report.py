#!/usr/bin/env python3
"""
Phase Attention Report — aggregates Airtable tasks by Phase field.

Usage:
  python3 scripts/phase_attention_report.py              # print to stdout
  python3 scripts/phase_attention_report.py --json       # JSON output for Dashboard
  python3 scripts/phase_attention_report.py --dashboard  # write to dashboard/data/

Purpose:
  Weekly cron runs this. If any phase has 0 tasks for 4+ consecutive weeks,
  flags it as a potential blind spot.
"""
from __future__ import annotations
import json, os, sys
from datetime import datetime, timezone, timedelta
from pathlib import Path
from collections import Counter

# ── Config (from .env or environment) ──
try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).parent.parent / ".env")
except ImportError:
    pass

AIRTABLE_KEY = os.environ.get("AIRTABLE_API_KEY", "")
AIRTABLE_BASE = os.environ.get("AIRTABLE_BASE_ID", "")
TABLE = os.environ.get("AIRTABLE_TABLE_TASKSTATELOG", "tblmb8402TJiPz5h9")

PHASES = [
    "mode-detect",
    "phase-1", "phase-2", "phase-3",
    "phase-4", "phase-5", "phase-6", "phase-7",
]

PHASE_LABELS = {
    "mode-detect": "Mode Detection",
    "phase-1": "Stakeholder / Feature Fusion",
    "phase-2": "Constraint / Scope",
    "phase-3": "Architecture",
    "phase-4": "Design & UX",
    "phase-5": "Development",
    "phase-6": "Delivery",
    "phase-7": "Review & Evolve",
}


def fetch_tasks() -> list[dict]:
    """Fetch all tasks from Airtable. Falls back to mock for dry-run."""
    if not AIRTABLE_KEY or not AIRTABLE_BASE:
        return _mock_tasks()

    from pyairtable import Api
    api = Api(AIRTABLE_KEY)
    records = api.base(AIRTABLE_BASE).table(TABLE).all()
    return [r.get("fields", {}) for r in records]


def _mock_tasks() -> list[dict]:
    """Mock data for testing without Airtable credentials."""
    return [
        {"Phase": "phase-5", "TaskId": "mock-dev-1", "Status": "Doing"},
        {"Phase": "phase-5", "TaskId": "mock-dev-2", "Status": "Todo"},
        {"Phase": "phase-4", "TaskId": "mock-design-1", "Status": "Done"},
        {"Phase": "phase-4", "TaskId": "mock-design-2", "Status": "Doing"},
        {"Phase": "phase-6", "TaskId": "mock-deliver-1", "Status": "Todo"},
        {"Phase": "phase-3", "TaskId": "mock-arch-1", "Status": "Done"},
        {"Phase": "",           "TaskId": "mock-nophase-1", "Status": "Todo"},
    ]


def aggregate(tasks: list[dict]) -> dict:
    """Count tasks per phase."""
    counter: Counter = Counter()
    for t in tasks:
        phase = t.get("Phase", "") or "(unset)"
        counter[phase] += 1
    return dict(counter)


def check_blind_spots(counts: dict) -> list[str]:
    """Return phases with 0 tasks. In production, this should check 4-week history."""
    missing = []
    for p in PHASES:
        if counts.get(p, 0) == 0:
            missing.append(p)
    return missing


def format_report(counts: dict, blind_spots: list[str], json_out: bool = False) -> str:
    """Generate report in text or JSON format."""
    now = datetime.now(timezone.utc).isoformat()

    if json_out:
        report = {
            "generated_at": now,
            "phases": {},
            "blind_spots": blind_spots,
            "total_tasks": sum(counts.values()),
        }
        for p in PHASES:
            report["phases"][p] = {
                "label": PHASE_LABELS.get(p, p),
                "count": counts.get(p, 0),
            }
        return json.dumps(report, ensure_ascii=False, indent=2)

    # Text format
    lines = [f"Phase Attention Report — {now}", "=" * 50]
    total = sum(counts.values())
    for p in PHASES:
        count = counts.get(p, 0)
        bar = "█" * min(count, 20)
        flag = " ← BLIND SPOT" if p in blind_spots else ""
        lines.append(f"  {PHASE_LABELS.get(p,p):35s} {count:3d}  {bar}{flag}")
    lines.append(f"  {'(unset)':35s} {counts.get('(unset)',0):3d}")
    lines.append(f"\n  Total: {total} tasks across {len(PHASES)} phases")
    if blind_spots:
        lines.append(f"\n  WARNING: {len(blind_spots)} phases have zero tasks.")
        lines.append(f"  Consider whether these are intentional gaps or blind spots.")
    return "\n".join(lines)


def write_dashboard(counts: dict, blind_spots: list[str]):
    """Write report JSON to dashboard data directory."""
    dashboard_dir = Path(__file__).parent.parent.parent / ".openclaw" / "workspace" / "dashboard" / "data"
    dashboard_dir.mkdir(parents=True, exist_ok=True)
    path = dashboard_dir / "phase-attention.json"
    report = format_report(counts, blind_spots, json_out=True)
    path.write_text(report)
    print(f"Written to {path}")


def main():
    json_out = "--json" in sys.argv
    dashboard = "--dashboard" in sys.argv

    tasks = fetch_tasks()
    counts = aggregate(tasks)
    blind_spots = check_blind_spots(counts)

    if dashboard:
        write_dashboard(counts, blind_spots)
    else:
        print(format_report(counts, blind_spots, json_out=json_out))


if __name__ == "__main__":
    main()
