---
name: phase-gate
description: Check all exit criteria for the current phase before advancing to the next one. Use between any two phases (spec→plan, plan→tasks, tasks→implement).
tools: Read
---

# Phase gate check

Before starting a new spec-driven phase, verify all exit criteria for the previous phase are satisfied.

1. Identify the feature slug and the phase transition being attempted (e.g., spec → plan, plan → tasks, tasks → implement). Ask if not clear from context.
2. Read the previous phase file (`spec.md`, `plan.md`, or `tasks.md` in `specs/<slug>/`).
3. Check the frontmatter `status` field. If not `approved`, stop and report who the required approver is per the phase table in `spec-driven-development.md`.
4. Check the phase's exit criteria against the file contents:
   - `spec.md`: all open questions resolved, every FR-NNN has a testable Given-When-Then, no FRs require another FR to test.
   - `plan.md`: all FR-NNN requirements traceable to a component, Constitution check fully ticked, every ADR has explicit reasoning.
   - `tasks.md`: every task has a `Verify:` line, every FR maps to at least one task, dependency tree is present.
5. Report which criteria pass and which fail. For failures, state exactly what is missing and what needs to be added before the gate can open.

Do not begin work on the next phase. This skill only checks — it does not advance.
