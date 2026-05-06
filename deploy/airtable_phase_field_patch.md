# Airtable Schema Patch: Phase Field

## Task
Add `Phase` field to the Tasks table to enable attention tracking across the 7-phase product lifecycle.

## Field Spec
- **Field Name:** `Phase`
- **Field Type:** Single select
- **Options:**
  - `mode-detect` — Phase 0: Mode Detection
  - `phase-1` — Stakeholder Alignment (B2B) / Feature Fusion (Personal)
  - `phase-2` — Constraint Elicitation (B2B) / Scope Definition (Personal)
  - `phase-3` — Technical Architecture
  - `phase-4` — Design & UX
  - `phase-5` — Development (TDD + Evals + Code Review)
  - `phase-6` — Delivery (Feishu, Dashboard, Notifications)
  - `phase-7` — Review & Evolve (8D, Self-Reflection, Skill Update)

## Usage
- Every new task created via `task_creator.py` should default to `mode-detect` until overridden
- SAM updates the Phase field as the task progresses through phases
- Weekly cron aggregation script sums tasks per phase and outputs a blind-spot report

## Backfill
Manual: review existing tasks, assign Phase based on content.
Automated (future): LLM reads task description → predicts Phase → writes back.
