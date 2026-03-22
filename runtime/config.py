"""
Harness config — loads from .env, exposes typed constants.
All field names mirror the actual Airtable column names exactly.
"""
import os
from pathlib import Path
from dotenv import load_dotenv

# Always load from the repo root, regardless of where Python is invoked from
_REPO_ROOT = Path(__file__).parent.parent
load_dotenv(_REPO_ROOT / ".env")

# ── Airtable ──────────────────────────────────────────────────────────────────
AIRTABLE_API_KEY: str = os.environ["AIRTABLE_API_KEY"]
AIRTABLE_BASE_ID: str = os.environ["AIRTABLE_BASE_ID"]
TABLE_TASKSTATELOG: str = os.getenv("AIRTABLE_TABLE_TASKSTATELOG", "tblmb8402TJiPz5h9")

# Airtable field name → Python attribute name mapping
# Left = exact Airtable column name, Right = key used in code
FIELDS = {
    "task_id":            "TaskId",
    "session_id":         "SessionId",
    "status":             "Status",
    "progress":           "Progress",
    "run_id":             "RunId",
    "owner_agent":        "OwnerAgent",
    "blocked_reason":     "BlockedReason",
    "next_recovery_step": "NextRecoveryStep",
    "updated_at":         "UpdatedAt",
    "artifact_links":     "ArtifactLinks",
    "task_context":       "TaskContext",
    "source":             "Source",
    # NEW — must be added to Airtable before use (see deploy/airtable_schema_patch.md)
    "lock_token":         "LockToken",
    "lease_until":        "LeaseUntil",
    "lease_owner":        "LeaseOwner",
}

# ── LLM ───────────────────────────────────────────────────────────────────────
LLM_PROVIDER: str = os.getenv("LLM_PROVIDER", "claude").lower()  # "claude" | "openai"
LLM_MODEL: str = os.getenv("LLM_MODEL", "claude-opus-4-6")
CLAUDE_API_KEY: str = os.getenv("CLAUDE_API_KEY", "")
OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
LLM_RETRY_MAX: int = int(os.getenv("LLM_RETRY_MAX", "3"))

# ── Notifications ─────────────────────────────────────────────────────────────
# Discord — Bot Token mode (from openclaw.json bot token)
DISCORD_BOT_TOKEN: str          = os.getenv("DISCORD_BOT_TOKEN", "")
DISCORD_NOTIFY_CHANNEL_ID: str  = os.getenv("DISCORD_NOTIFY_CHANNEL_ID", "")

# Feishu — App OpenAPI mode (from ~/.openclaw/secrets/)
FEISHU_APP_ID: str              = os.getenv("FEISHU_APP_ID", "")
FEISHU_APP_SECRET: str          = os.getenv("FEISHU_APP_SECRET", "")
FEISHU_NOTIFY_CHAT_ID: str      = os.getenv("FEISHU_NOTIFY_CHAT_ID", "")

# ── Harness behaviour ─────────────────────────────────────────────────────────
LEASE_DURATION_SECONDS: int = int(os.getenv("LEASE_DURATION_SECONDS", "1800"))
POLL_INTERVAL_SECONDS: int = int(os.getenv("POLL_INTERVAL_SECONDS", "600"))

# States that the poller should pick up
CLAIMABLE_STATUSES: list[str] = ["LOADED"]
# States where harness continues running
RUNNING_STATUSES: list[str] = ["RUNNING"]
# Terminal states — harness stops
TERMINAL_STATUSES: list[str] = ["DONE", "BLOCKED", "FAILED"]
