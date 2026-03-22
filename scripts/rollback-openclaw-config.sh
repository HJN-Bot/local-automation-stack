#!/usr/bin/env bash
set -euo pipefail

CFG="${OPENCLAW_CONFIG:-$HOME/.openclaw/openclaw.json}"
SRC="${1:-}"

if [[ -z "$SRC" ]]; then
  # pick latest backup automatically
  SRC=$(ls -t "$CFG".bak-* 2>/dev/null | head -n1 || true)
fi

if [[ -z "$SRC" || ! -f "$SRC" ]]; then
  echo "[rollback] backup file not found. Pass one explicitly:"
  echo "  scripts/rollback-openclaw-config.sh ~/.openclaw/openclaw.json.bak-YYYY-MM-DD..."
  exit 1
fi

cp "$CFG" "${CFG}.pre-rollback-$(date -u +%Y%m%dT%H%M%SZ)"
cp "$SRC" "$CFG"

echo "[rollback] restored: $SRC -> $CFG"
openclaw gateway restart >/dev/null 2>&1 || true
openclaw gateway status || true
