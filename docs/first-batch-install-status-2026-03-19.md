# First Batch Install Status (2026-03-19)

## Scope
- Goal: install first-batch baseline capabilities for OpenClaw globally.
- Priority: **safety + foundation**, then browser automation.

## Installed (success)
- `openclaw-backup` (via npm)
- `openclaw-mission-control` (via npm)
- Skills unpacked to global skills dir (`/home/ubuntu/.openclaw/workspace/skills`):
  - `skill-vetter`
  - `agent-browser-clawdbot`
  - `self-improving-agent`

## Blocked / partial
- ClawdHub installs currently rate-limited (`Rate limit exceeded`) for several slugs.
- Some slugs not found in registry (`lossless-claw`, `control-center`).

## Notes
- Browser capability is marked P0 for second batch due to login/session pain-point.
- `openclaw-backup` requires `GITHUB_TOKEN` and target repo settings before first backup/restore run.

## Next actions
1. Run backup/restore dry-run with safe test target.
2. Start mission-control wizard and bind to current gateway.
3. Retry ClawdHub second batch after rate-limit window.
