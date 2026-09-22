---
name: spec-check
description: Verify the current implementation satisfies every FR-NNN acceptance criterion in the approved spec. Run before any PR.
tools: Read
---

# Spec compliance check

Given a feature under active implementation, verify that the code satisfies the acceptance criteria in the approved spec.

1. Identify the feature slug from context (ask if ambiguous). Read `specs/<slug>/spec.md`. If `status` is not `approved`, stop and report it — implementation should not have started.
2. For each `FR-NNN` acceptance criterion, locate the relevant code in the implementation.
3. Check whether the Given-When-Then condition is satisfied by what the code actually does — not what comments or variable names claim it does.
4. Report pass or fail per criterion. For each failure: state which file and line is relevant, what the code does, and what it must do to satisfy the criterion. Map the failure to its task ID in `tasks.md`.
5. If all criteria pass, confirm and note any criteria that could not be verified without a running environment (flag them explicitly, don't mark them as passing).

Do not suggest changes beyond what is needed to satisfy failing criteria. Do not refactor passing code.
