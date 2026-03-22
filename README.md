# OpenClaw Config Kit (private)

Reusable config hardening + restore scripts for Discord multi-agent setups.

## What it does
- backup current `~/.openclaw/openclaw.json`
- set Discord `groupPolicy=allowlist`
- restore channel `systemPrompt` blocks from a backup config
- run health checks (`openclaw status --deep`, `openclaw security audit --deep`)

## Usage
```bash
node scripts/backup-and-harden.mjs
node scripts/restore-prompts-from-backup.mjs ~/.openclaw/openclaw.json.bak.4
```
