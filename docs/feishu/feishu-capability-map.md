# Feishu Capability Map

## Current confirmed local assets

### Secrets
- `/home/ubuntu/.openclaw/secrets/feishu_app_id`
- `/home/ubuntu/.openclaw/secrets/feishu_app_secret`

### Scripts
- `/home/ubuntu/.openclaw/workspace/tools/feishu_wiki_mvp.py`
- `/home/ubuntu/.openclaw/workspace/tools/feishu_mcp_smoketest.sh`

### Repos / MCP assets
- `/home/ubuntu/.openclaw/workspace/repos/lark-openapi-mcp`
- `/home/ubuntu/.local/state/lark-mcp-nodejs`

### Shared agent skills / SOP
- `agents/andrew/skills/feishu-write-shared`
- `agents/rex/skills/feishu-write-shared`
- `agents/lulu/skills/feishu-write-shared`
- `agents/alex/skills/feishu-write-shared`
- `agents/andrew/skills/feishu-agent-workflow`

### Supporting drafts / scans / deliverables
- `agents/andrew/feishu_wiki_content_scan.json`
- `agents/andrew/feishu_wiki_scan.json`
- `agents/andrew/feishu_workflow_drafts.json`
- `agents/andrew/tmp/mae_v3_from_feishu.txt`
- `agents/lulu/deliverables/wiki-bot-onboarding-flow.excalidraw`
- `agents/lulu/deliverables/wiki-bot-onboarding-flow.png`

## Confirmed capability levels

### Level A — Strongly confirmed
- Feishu app credentials exist locally
- Wiki node read capability exists
- Wiki child page creation MVP exists
- Shared Feishu Wiki writing SOP exists
- Agent workflow design exists for Feishu + Airtable + GitHub writeback

### Level B — Partially confirmed
- Feishu / Lark MCP startup path exists
- MCP smoke test exists
- local MCP state exists
- likely Feishu CLI / MCP exploration has started

### Level C — Needs more tracing
- group message / bot message sending path
- FeishuThreadId round-trip flow
- exact successful MAE group-thread smoke tests

## Practical interpretation
Feishu is not a missing future feature. It already exists in three lines:
1. Wiki document line
2. MAE / thread / group visualization line
3. MCP / CLI line
