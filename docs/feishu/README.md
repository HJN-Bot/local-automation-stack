# Feishu Integration Docs

This directory is the source of truth for Feishu capability design inside `local-automation-stack`.

It covers:
- current Feishu assets already present on the machine
- dual-track architecture: WikiBot + Feishu CLI/MCP
- writing spec for WikiBot outputs
- agent-to-Feishu responsibility mapping
- MAE thread / FeishuThreadId workflow

## Why this exists
Feishu capabilities have already been partially implemented in multiple forms (Wiki writing, MCP smoke tests, shared SOPs, MAE-related thread experiments), but the knowledge is fragmented. This directory consolidates that system knowledge so future prompt / workflow / skill decisions do not lose context.

## Document map
- `feishu-capability-map.md` — current machine assets and status
- `feishu-dual-track-architecture.md` — why Feishu should run as dual track
- `wikibot-writing-spec.md` — how Feishu Wiki writing should feel more natural and useful
- `agent-feishu-responsibility-matrix.md` — which agent owns which Feishu surfaces and style
- `mae-feishu-thread-workflow.md` — MAE, threads, FeishuThreadId, and group visualization workflow
