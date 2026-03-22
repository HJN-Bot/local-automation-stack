#!/usr/bin/env bash
set -euo pipefail

OUT_DIR="${1:-backups/$(date -u +%F)}"
mkdir -p "$OUT_DIR"

OUT_DIR="$OUT_DIR" python3 - <<'PY'
import json, pathlib, datetime, os
src=pathlib.Path('/home/ubuntu/.openclaw/openclaw.json')
out=pathlib.Path(os.environ['OUT_DIR'])
out.mkdir(parents=True, exist_ok=True)
obj=json.loads(src.read_text())
# redact common secret-ish fields
if isinstance(obj.get('channels',{}).get('discord'), dict):
    for acct in obj['channels']['discord'].get('accounts', []):
        if isinstance(acct, dict) and 'token' in acct:
            acct['token'] = 'REDACTED'
if isinstance(obj.get('auth'), dict):
    for k,v in list(obj['auth'].items()):
        if isinstance(v, dict):
            for kk in list(v.keys()):
                if any(x in kk.lower() for x in ['token','secret','key','password']):
                    v[kk]='REDACTED'

target=out/'openclaw.redacted.json'
target.write_text(json.dumps(obj,ensure_ascii=False,indent=2)+"\n")
summary={
  'generatedAtUtc': datetime.datetime.now(datetime.UTC).isoformat(),
  'defaultModel': obj.get('agents',{}).get('defaults',{}).get('model',{}).get('primary'),
  'agentCount': len(obj.get('agents',{}).get('list',[])),
  'agents': [
    {'id': a.get('id'), 'model': (a.get('model') or {}).get('primary')}
    for a in obj.get('agents',{}).get('list',[])
  ]
}
(out/'openclaw.summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2)+"\n")
PY

OUT_DIR="$OUT_DIR" python3 - <<'PY'
import pathlib, os
skills_dir=pathlib.Path('/home/ubuntu/.openclaw/workspace/skills')
out=pathlib.Path(os.environ['OUT_DIR'])
items=[p.name for p in sorted(skills_dir.iterdir()) if p.is_dir()]
(out/'skills.installed.txt').write_text('\n'.join(items)+"\n")
PY

echo "Snapshot written to $OUT_DIR"
