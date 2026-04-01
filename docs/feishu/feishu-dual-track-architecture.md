# Feishu Dual-Track Architecture

## Core judgment
Feishu should not be treated as a single integration path. The system should run two parallel but connected tracks:

## Track A — WikiBot / document persistence
Primary purpose:
- stable page writing
- Airtable / Dashboard / GitHub linked deliverables
- structured document persistence
- `... - Sam` draft workflow

Best for:
- learning notes
- agent deliverables
- task writeback evidence
- knowledge base building
- clean, repeatable document output

## Track B — Feishu CLI / MCP / native object operations
Primary purpose:
- more native Feishu object manipulation
- richer page / block / table interactions
- multidimensional tables
- thread / group workflows
- future board / frame / diagram-like interactions

Best for:
- visual collaboration surfaces
- thread-linked workflows
- native Feishu operations beyond markdown-ish page writing
- more interactive MAE visual workflows

## Why both are needed
If only WikiBot exists:
- document persistence is strong
- native Feishu interaction is weak

If only CLI / MCP exists:
- native manipulation may be stronger
- stable task-linked document persistence may become less reliable

## Recommended convergence
- WikiBot remains the main persistence layer
- Feishu CLI / MCP becomes the native collaboration enhancement layer
- Airtable / Dashboard / GitHub / Feishu writeback should converge into one evidence chain
