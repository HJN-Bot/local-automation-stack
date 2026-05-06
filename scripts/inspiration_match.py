#!/usr/bin/env python3
"""
Inspiration Matcher — query the inspiration database by problem type.

Usage:
  python3 scripts/inspiration_match.py "state-machine-design"
  python3 scripts/inspiration_match.py "animation-stagger" --json
  python3 scripts/inspiration_match.py --list-types    # list all problem types
"""
from __future__ import annotations
import json, os, sys
from pathlib import Path
from datetime import datetime, timezone

# ── Config ──
INSPIRATION_INDEX = Path(__file__).parent.parent.parent / ".openclaw" / "workspace" / "AI-Intelligence-Vault" / "30_Inspiration" / "inspiration-index.json"

PROBLEM_TYPES = [
    "layout-asymmetry", "state-machine-design", "animation-stagger",
    "prompt-engineering", "eval-framework", "skill-authoring",
    "pipeline-orchestration", "lock-manager", "degradation-chain",
    "content-digest", "tts-pipeline", "video-rendering",
    "mcp-server", "agent-routing", "frontend-theming",
    "responsive-design", "type-safety", "ci-cd",
    "testing", "code-review", "stakeholder-alignment",
    "feature-fusion", "scope-definition", "delivery-automation",
    "self-evolution",
]

PHASE_LABELS = {
    "phase-1": "Feature Fusion",
    "phase-2": "Scope",
    "phase-3": "Architecture",
    "phase-4": "Design",
    "phase-5": "Development",
    "phase-6": "Delivery",
    "phase-7": "Review",
}


def load_index() -> list[dict]:
    """Load the inspiration index. Returns empty list if file doesn't exist."""
    if not INSPIRATION_INDEX.exists():
        return []
    return json.loads(INSPIRATION_INDEX.read_text())


def match(problem_type: str, items: list[dict], top_n: int = 3) -> list[dict]:
    """Find items matching the given problem type, ranked by signal_score descending."""
    matches = []
    for item in items:
        tags = item.get("inspiration_tags", {})
        types = tags.get("problem_type", [])
        if problem_type in types:
            matches.append(item)
    matches.sort(key=lambda x: x.get("signal_score", 0), reverse=True)
    return matches[:top_n]


def format_result(matches: list[dict], json_out: bool = False) -> str:
    """Format matches for display."""
    if json_out:
        return json.dumps(matches, ensure_ascii=False, indent=2)

    if not matches:
        return "No matches found. Try a different problem type."

    lines = [f"Found {len(matches)} match(es):", ""]
    for i, m in enumerate(matches, 1):
        tags = m.get("inspiration_tags", {})
        phase = tags.get("phase", "unknown")
        lines.append(f"  {i}. {m.get('title', 'Untitled')}")
        lines.append(f"     URL: {m.get('url', 'N/A')}")
        lines.append(f"     Phase: {PHASE_LABELS.get(phase, phase)} | Reusability: {tags.get('reusability', '?')}")
        lines.append(f"     Summary: {m.get('summary', 'N/A')[:120]}")
        lines.append("")
    return "\n".join(lines)


def main():
    if "--list-types" in sys.argv:
        print("Available problem types:")
        for t in PROBLEM_TYPES:
            print(f"  {t}")
        return

    if len(sys.argv) < 2:
        print("Usage: python3 inspiration_match.py <problem_type> [--json] [--list-types]")
        sys.exit(1)

    problem_type = sys.argv[1]
    json_out = "--json" in sys.argv

    items = load_index()
    if not items:
        print("Inspiration index is empty. Add items via the content pipeline digest tagging.")
        # Show mock result so the pipeline is demonstrable
        print("\n-- Mock result (demonstration) --")
        print(format_result([
            {
                "title": "frontend-slides: Animation Patterns Reference",
                "url": "https://github.com/zarazhangrui/frontend-slides",
                "signal_score": 0.92,
                "inspiration_tags": {
                    "phase": "phase-4",
                    "problem_type": [problem_type, "responsive-design", "frontend-theming"],
                    "reusability": "direct-copy"
                },
                "summary": "Animation-rich HTML presentation framework with scroll-snap, staggered reveals, and cinematic transitions."
            }
        ], json_out))
        return

    matches = match(problem_type, items)
    print(format_result(matches, json_out))


if __name__ == "__main__":
    main()
