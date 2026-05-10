# CONTEXT · local-automation-stack

> Shared domain language for this repository.
> 
> Goal: keep engineers + PM + agents aligned on terms, boundaries, and invariants.
> Keep it domain-level (not implementation details).

---

## 1) What this repo is
- Purpose: automation stack + MAE orchestrator + operational tooling for Jianan.
- Primary users: Jianan (owner), agents (SAM/Andrew/Rex/Lulu/Alex), and any engineers collaborating.

## 2) Glossary (canonical terms)
- **MAE**: Multi-Agent Execution — the orchestrated execution system.
- **Skill**: a reusable SOP + tool protocol unit invoked by agents.
- **Gate**: a mandatory quality/approval checkpoint for T2+ tasks (e.g. PLO).
- **PLO**: Product Lifecycle Orchestrator — router + gate system for T2+ product/design/release tasks.
- **Layer 1/2/3 (Hermes-style learning loop)**: self-eval (suggest) → self-evolve (draft) → semi-auto (low-risk + fuse).

## 3) Non-goals
- This file is not a runbook. Runbooks live in docs/.
- This file does not record transient chat history.

## 4) Decisions (high-level)
- System-level changes must be versioned (commit) and, when possible, pushed to the ops/baseline repo.

## 5) Invariants / constraints
- Changes must be reversible (archive/rollback) when touching system-level mechanisms.
- Avoid noisy push channels; daily 07:15 digest is the primary reminder cadence.
