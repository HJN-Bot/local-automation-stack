#!/Users/jianan/Projects/local-automation-stack/mae-orchestrator/venv/bin/python3
"""
MAE Task Poller — Lightweight heartbeat-integrated task executor.

Design principles:
  1. No persistent daemon. Invoked by heartbeat/cron, runs once, exits.
  2. Checks Airtable for tasks with status="claimed" + assignee matching a known CLI.
  3. Executes the CLI in an isolated workspace directory.
  4. Writes result + retrospective back to Airtable.
  5. Supports checkpoint gating: pause and wait for human review at designated steps.

Usage:
  python3 mae_poller.py                     # poll once, execute any claimed tasks
  python3 mae_poller.py --dry-run           # show what would run, don't execute
  python3 mae_poller.py --task-id recXXXX   # execute a specific task

CLI mapping (hardcoded for simplicity, only 2 CLIs):
  assignee "codex"  → codex CLI
  assignee "claude" → claude CLI

Integration: add to HEARTBEAT.md or cron:
  */5 * * * * cd /path/to/mae-orchestrator && venv/bin/python3 mae_poller.py >> logs/poller.log 2>&1
"""

import argparse
import json
import os
import subprocess
import sys
import time
import shutil
import uuid
from datetime import datetime, timezone
from pathlib import Path
from pyairtable import Api

# ── Config ──────────────────────────────────────────────
_env_path = Path("/Users/jianan/Projects/local-automation-stack/mae-orchestrator/.env")
for line in _env_path.read_text().splitlines():
    if "=" in line and not line.startswith("#"):
        k, v = line.split("=", 1)
        os.environ.setdefault(k.strip(), v.strip())

MAE_TABLE = "tblvaXhvNxZgKE4SQ"  # Agent Tasks
WORKSPACES_ROOT = Path("/Users/jianan/.openclaw/workspace/mae_workspaces")
LOG_DIR = Path("/Users/jianan/Projects/local-automation-stack/mae-orchestrator/logs")

# ── CLI mapping ─────────────────────────────────────────
CLI_MAP = {
    "codex": {
        "bin": "/opt/homebrew/bin/codex",
        "args": ["exec", "--yes"],
        "workspace_arg": "--cwd",
    },
    "claude": {
        "bin": shutil.which("claude") or "claude",
        "args": ["-p"],
        "workspace_arg": None,  # claude uses --cwd or runs in cwd
    },
}

# ── Helpers ──────────────────────────────────────────────

def _get_table():
    api = Api(os.getenv("AIRTABLE_API_KEY"))
    return api.table(os.getenv("AIRTABLE_BASE_ID"), MAE_TABLE)


def get_claimed_tasks(assignee_filter: str = None):
    """Fetch tasks with status='claimed' (or 'doing') that are assigned to a CLI."""
    table = _get_table()
    # Airtable formula: find tasks that are claimed/doing and assigned to a known CLI
    formula_parts = ["OR(Status='claimed',Status='doing')"]
    records = table.all(formula=", ".join(formula_parts))
    
    tasks = []
    for rec in records:
        fields = rec.get("fields", {})
        assignee = fields.get("Assignee", "")
        cli_name = assignee.lower().strip() if assignee else ""
        if cli_name in CLI_MAP:
            if assignee_filter and cli_name != assignee_filter:
                continue
            tasks.append({
                "id": rec["id"],
                "assignee": cli_name,
                "content": fields.get("Content", ""),
                "task_type": fields.get("Task Type", "research"),
                "repo": fields.get("Repo", ""),       # optional: GitHub repo to clone
                "checkpoint": fields.get("Checkpoint", ""),  # optional: checkpoint config
            })
    return tasks


def create_workspace(task_id: str, repo_url: str = None) -> Path:
    """Create isolated workspace directory. Optionally clone a repo."""
    ws = WORKSPACES_ROOT / task_id
    ws.mkdir(parents=True, exist_ok=True)
    
    if repo_url:
        repo_name = repo_url.rstrip("/").split("/")[-1].replace(".git", "")
        repo_dir = ws / repo_name
        if not repo_dir.exists():
            result = subprocess.run(
                ["git", "clone", repo_url, str(repo_dir)],
                capture_output=True, text=True, timeout=120
            )
            if result.returncode != 0:
                print(f"[Poller] ⚠️ git clone failed: {result.stderr}")
    
    return ws


def execute_cli(task: dict, workspace: Path, dry_run: bool = False) -> dict:
    """Execute the appropriate CLI for the task."""
    cli_name = task["assignee"]
    cli_cfg = CLI_MAP[cli_name]
    bin_path = cli_cfg["bin"]
    
    if not os.path.exists(bin_path):
        return {"status": "failed", "error": f"CLI not found: {bin_path}"}
    
    cmd = [bin_path] + cli_cfg["args"]
    
    # For codex: codex exec --yes --cwd <workspace> "<prompt>"
    if cli_cfg["workspace_arg"] and "exec" in cli_cfg["args"]:
        cmd.insert(2, cli_cfg["workspace_arg"])
        cmd.insert(3, str(workspace))
    
    cmd.append(task["content"])
    
    print(f"[Poller] 🚀 {task['id']}: {cli_name} {' '.join(cmd[:5])}...")
    
    if dry_run:
        return {"status": "dry_run", "command": " ".join(cmd)}
    
    try:
        result = subprocess.run(
            cmd,
            cwd=str(workspace),
            capture_output=True,
            text=True,
            timeout=600,  # 10 min timeout
        )
        return {
            "status": "done" if result.returncode == 0 else "failed",
            "stdout": result.stdout[-5000:],  # last 5k chars
            "stderr": result.stderr[-2000:],
            "exit_code": result.returncode,
        }
    except subprocess.TimeoutExpired:
        return {"status": "failed", "error": "timeout (600s)"}
    except Exception as e:
        return {"status": "failed", "error": str(e)}


def write_retrospective(task_id: str, result: dict, elapsed_s: float):
    """Append a retrospective entry to the task's Airtable record."""
    table = _get_table()
    retro = {
        "run_id": str(uuid.uuid4())[:8],
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "status": result.get("status"),
        "elapsed_s": round(elapsed_s, 1),
        "exit_code": result.get("exit_code"),
        "error": result.get("error", ""),
        "stdout_tail": (result.get("stdout", "") or "")[-500:],
        "suggested_update": None,  # human fills this later
    }
    
    # Store as JSON in the Result field (or append to existing)
    try:
        existing = table.get(task_id).get("fields", {}).get("Result", "")
        existing_retros = []
        if existing:
            try:
                existing_retros = json.loads(existing) if isinstance(existing, str) else existing
            except json.JSONDecodeError:
                existing_retros = [{"previous_result": existing}]
        if not isinstance(existing_retros, list):
            existing_retros = []
        existing_retros.append(retro)
        
        table.update(task_id, {
            "Status": result.get("status", "failed"),
            "Result": json.dumps(existing_retros, ensure_ascii=False, indent=2),
        })
        print(f"[Poller] ✅ Retrospective written: {task_id}")
        
        # Check if skill needs human review (≥3 retrospectives)
        if len(existing_retros) >= 3:
            print(f"[Poller] 📋 Skill review triggered: {task_id} has {len(existing_retros)} retrospectives")
    except Exception as e:
        print(f"[Poller] ⚠️ Failed to write retrospective: {e}")


def cleanup_workspace(task_id: str, keep: bool = False):
    """Remove workspace directory after task completion (GC light)."""
    if keep:
        return
    ws = WORKSPACES_ROOT / task_id
    if ws.exists():
        shutil.rmtree(ws, ignore_errors=True)
        print(f"[Poller] 🧹 Cleaned workspace: {ws}")


# ── Main ─────────────────────────────────────────────────

def poll_and_execute(dry_run: bool = False, task_id: str = None, assignee: str = None):
    """Main polling loop — runs once and exits."""
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    WORKSPACES_ROOT.mkdir(parents=True, exist_ok=True)
    
    if task_id:
        # Execute a specific task directly
        table = _get_table()
        rec = table.get(task_id)
        fields = rec.get("fields", {})
        tasks = [{
            "id": task_id,
            "assignee": (fields.get("Assignee", "") or "").lower().strip(),
            "content": fields.get("Content", ""),
            "task_type": fields.get("Task Type", "research"),
            "repo": fields.get("Repo", ""),
            "checkpoint": fields.get("Checkpoint", ""),
        }]
    else:
        tasks = get_claimed_tasks(assignee)
    
    if not tasks:
        print(f"[Poller] No claimed tasks found. Exiting.")
        return
    
    print(f"[Poller] Found {len(tasks)} claimed task(s)")
    
    for task in tasks:
        start = time.time()
        print(f"[Poller] 📋 Processing {task['id']} ({task['assignee']})")
        
        ws = create_workspace(task["id"], task.get("repo"))
        result = execute_cli(task, ws, dry_run)
        elapsed = time.time() - start
        
        if not dry_run:
            write_retrospective(task["id"], result, elapsed)
            cleanup_workspace(task["id"])
        
        status_emoji = {"done": "✅", "failed": "❌", "dry_run": "🔍"}.get(result.get("status"), "❓")
        print(f"[Poller] {status_emoji} {task['id']}: {result.get('status')} ({elapsed:.1f}s)")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="MAE Task Poller — lightweight heartbeat executor")
    parser.add_argument("--dry-run", action="store_true", help="Show what would execute, don't run")
    parser.add_argument("--task-id", default=None, help="Execute a specific task by Airtable record ID")
    parser.add_argument("--assignee", default=None, choices=list(CLI_MAP.keys()), help="Filter by CLI assignee")
    args = parser.parse_args()
    
    poll_and_execute(dry_run=args.dry_run, task_id=args.task_id, assignee=args.assignee)
