#!/usr/bin/env python3
"""
CLI wrapper — Sam (Andrew) calls this via exec tool to create a MAE task or plan.

Single task:
  python3 scripts/create_task.py --goal "调研竞品 XX 的定价策略" --eta "2小时"
  python3 scripts/create_task.py --goal "..." --agent REX --source discord

Multi-agent plan (JSON sub-tasks):
  python3 scripts/create_task.py --plan --goal "调研竞品并产出报告" --sub-tasks '[
    {"goal": "搜集竞品数据", "owner_agent": "REX",  "eta": "30min"},
    {"goal": "写报告框架",   "owner_agent": "LULU", "eta": "30min"}
  ]'
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from runtime.task_creator import create_task, create_plan


def main() -> None:
    parser = argparse.ArgumentParser(description="Create a MAE task or multi-agent plan")
    parser.add_argument("--goal",      required=True, help="Overall goal (one sentence)")
    parser.add_argument("--agent",     default="SAM",     help="Owner agent for single task")
    parser.add_argument("--eta",       default="—",       help="Time estimate")
    parser.add_argument("--source",    default="discord", help="Trigger source")
    parser.add_argument("--task-id",   default=None,      help="Optional custom task ID")
    parser.add_argument("--plan",      action="store_true", help="Create a multi-agent plan")
    parser.add_argument("--sub-tasks", default=None,
                        help="JSON array of sub-tasks (required with --plan)")
    args = parser.parse_args()

    if args.plan:
        if not args.sub_tasks:
            print(json.dumps({"error": "--sub-tasks required with --plan"}, ensure_ascii=False))
            sys.exit(1)
        sub_tasks = json.loads(args.sub_tasks)
        result = create_plan(
            parent_goal=args.goal,
            sub_tasks=sub_tasks,
            source=args.source,
        )
        output = {
            "mode":             "plan",
            "parent_task_id":   result.parent_task_id,
            "parent_record_id": result.parent_record_id,
            "feishu_thread_id": result.feishu_thread_id,
            "sub_tasks":        result.sub_tasks,
            "message": (
                f"计划 {result.parent_task_id} 已创建，"
                f"{len(result.sub_tasks)} 个子任务已分配，MAE 将在下次 cron 自动认领执行。"
            ),
        }
    else:
        result = create_task(
            goal=args.goal,
            owner_agent=args.agent.upper(),
            eta=args.eta,
            source=args.source,
            task_id=args.task_id,
        )
        output = {
            "mode":             "single",
            "task_id":          result.task_id,
            "record_id":        result.record_id,
            "feishu_thread_id": result.feishu_thread_id,
            "airtable_url":     result.airtable_url,
            "status":           "LOADED",
            "message": f"任务 {result.task_id} 已创建，MAE 将在下次 cron 自动认领执行。",
        }

    print(json.dumps(output, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
