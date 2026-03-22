#!/usr/bin/env bash
# MAE Harness — local cron setup
# Usage: bash cron/setup_cron.sh
# Installs a crontab entry that runs task_poller every 10 minutes.

set -euo pipefail

REPO_DIR="$(cd "$(dirname "$0")/.." && pwd)"
PYTHON="${PYTHON:-$(which python3)}"
LOG_DIR="$REPO_DIR/logs"
CRON_LOG="$LOG_DIR/harness.log"
ENV_FILE="$REPO_DIR/.env"

# Validate prerequisites
if [[ ! -f "$ENV_FILE" ]]; then
  echo "[ERROR] $ENV_FILE not found. Copy .env.example → .env and fill in your credentials."
  exit 1
fi

if [[ ! -f "$REPO_DIR/requirements.txt" ]]; then
  echo "[ERROR] requirements.txt not found at $REPO_DIR"
  exit 1
fi

# Install Python dependencies
echo "[INFO] Installing Python dependencies..."
"$PYTHON" -m pip install -q -r "$REPO_DIR/requirements.txt"

# Create log dir
mkdir -p "$LOG_DIR"

# Build the cron line
# Runs every 10 minutes; stderr+stdout → log file (appended, not overwritten)
CRON_LINE="*/10 * * * * cd '$REPO_DIR' && '$PYTHON' -m runtime.task_poller >> '$CRON_LOG' 2>&1"

# Install (remove duplicate if exists, then add)
CURRENT_CRONTAB="$(crontab -l 2>/dev/null || true)"
CLEANED="$(echo "$CURRENT_CRONTAB" | grep -v 'runtime.task_poller' || true)"
NEW_CRONTAB="$(printf '%s\n%s\n' "$CLEANED" "$CRON_LINE")"
echo "$NEW_CRONTAB" | crontab -

echo ""
echo "[OK] Cron installed:"
echo "     $CRON_LINE"
echo ""
echo "[OK] Logs will be written to: $CRON_LOG"
echo ""
echo "To verify, run:  crontab -l | grep task_poller"
echo "To tail logs:    tail -f $CRON_LOG"
echo "To run manually: cd '$REPO_DIR' && '$PYTHON' -m runtime.task_poller"
echo ""
echo "To remove the cron:  crontab -l | grep -v task_poller | crontab -"
