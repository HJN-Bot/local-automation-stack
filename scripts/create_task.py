#!/usr/bin/env python3
"""
CLI wrapper — Sam (Andrew) calls this via exec tool to create a MAE task.

Usage:
  python3 scripts/create_task.py --goal "调研竞品 XX 的定价策略" --eta "2小时"
  python3 scripts/create_task.py --goal "..." --agent REX --source discord

Output (JSON to stdout):
  {
    "task_id": "task-20260329-1430-a1b2",
    "record_id": "recXXXXXXXXXXXXXX",
    "feishu_thread_id": "om_XXXXXXXXXXXX",
    "airtable_url": "https://airtable.com/...",
    "status": "LOADED",
    "message": "任务已创建，MAE 将在下次 cron（约10分钟内）自动认领执行。"
  }
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

# Ensure repo root is on sys.path when called from scripts/
sys.path.insert(0, str(Path(__file__).parent.parent))

from runtime.task_creator import create_task


def main() -> None:
    parser = argparse.ArgumentParser(description="Create a MAE task from Sam's trigger")
    parser.add_argument("--goal",   required=True, help="One-sentence task description")
    parser.add_argument("--agent",  default="SAM",     help="Owner agent (SAM/REX/LULU/ALEX)")
    parser.add_argument("--eta",    default="—",       help="Human-readable time estimate")
    parser.add_argument("--source", default="discord", help="Trigger source")
    parser.add_argument("--task-id", default=None,     help="Optional custom task ID")
    args = parser.parse_args()

    result = create_task(
        goal=args.goal,
        owner_agent=args.agent.upper(),
        eta=args.eta,
        source=args.source,
        task_id=args.task_id,
    )

    output = {
        "task_id":          result.task_id,
        "record_id":        result.record_id,
        "feishu_thread_id": result.feishu_thread_id,
        "airtable_url":     result.airtable_url,
        "status":           "LOADED",
        "message": (
            f"任务 {result.task_id} 已创建，MAE 将在下次 cron（约10分钟内）自动认领执行。"
            + (f" 飞书任务线程：{result.feishu_thread_id}" if result.feishu_thread_id else "")
        ),
    }
    print(json.dumps(output, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
