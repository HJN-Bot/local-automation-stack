#!/usr/bin/env bash
set -euo pipefail

echo "[verify] OpenClaw deep status"
openclaw status --deep

echo "\n[verify] Security audit (deep)"
openclaw security audit --deep

echo "\n[verify] Gateway service"
openclaw gateway status

echo "\n[verify] Key listeners"
ss -ltnp | grep -E ':8080|:18789|:18800|:5678' || true

echo "\n[verify] Done"
