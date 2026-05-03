#!/bin/bash
cd ~/Projects/local-automation-stack/mae-orchestrator
source venv/bin/activate

while true; do
  echo "[$(date)] Starting orchestrator..."
  python main.py
  echo "[$(date)] Exited with code $?, restarting in 5s..."
  sleep 5
done
