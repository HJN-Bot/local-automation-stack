# Inspiration Tagging: Digest Output Schema Extension

## Purpose
Extend the content pipeline digest output format to include structured tags that enable later inspiration matching.

## New Fields (append to existing digest output)

```json
{
  "title": "Original title from source",
  "url": "https://...",
  "source_type": "github_repo | blog_post | tweet | video | paper | tool",
  "summary": "2-3 sentence summary",
  "signal_score": 0.85,

  "inspiration_tags": {
    "phase": "phase-1 | phase-2 | phase-3 | phase-4 | phase-5 | phase-6 | phase-7",
    "problem_type": [
      "layout-asymmetry | state-machine-design | animation-stagger | prompt-engineering | eval-framework | skill-authoring | pipeline-orchestration | lock-manager | degradation-chain | content-digest | tts-pipeline | video-rendering | mcp-server | agent-routing | frontend-theming | responsive-design | type-safety | ci-cd | testing | code-review | stakeholder-alignment | feature-fusion | scope-definition | delivery-automation | self-evolution"
    ],
    "reusability": "direct-copy | adapt-with-changes | conceptual-inspiration",
    "related_skills": ["skill-name-1", "skill-name-2"]
  }
}
```

## Auto-Tagging Prompt

When the content pipeline processes an item, append this prompt to classify it:

```
Classify this content item for the inspiration database:

Content: {title} — {summary}

1. Which product lifecycle phase does this best serve?
   Options: phase-1 (Feature Fusion), phase-2 (Scope), phase-3 (Architecture),
            phase-4 (Design), phase-5 (Development), phase-6 (Delivery),
            phase-7 (Review)

2. What problem type(s) does this address?
   Choose from: [list above, up to 3]

3. How reusable is this?
   - direct-copy: I can use this as-is
   - adapt-with-changes: I need to modify it
   - conceptual-inspiration: The idea is valuable but implementation differs

Output JSON only: {"phase": "...", "problem_type": [...], "reusability": "..."}
```

## Manual Tagging (override when needed)

If auto-tagging is wrong, manually edit the `inspiration_tags` in the digest JSON.
After 2 weeks of manual corrections, analyze patterns and update the auto-tagging prompt.

## Storage
Append tagged items to: `AI-Intelligence-Vault/30_Inspiration/inspiration-index.json`
Or: Airtable `Inspirations` table with columns: Title, URL, SourceType, Phase, ProblemType, Reusability, DateAdded
