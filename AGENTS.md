# Cruthúnas Agent Map

Use this file as a map, not as a replacement for the specification.

## Read order

1. `CRUTHUNAS_SPEC.md` — canonical rules and status model.
2. `RESEARCH_CHARTER.md` — Gate 0 through Gate 10 requirements.
3. `docs/EXECUTION_ARCHITECTURE.md` — skills, hooks, CLI, CI, and adoption model.
4. `docs/POLICY_MATRIX.md` — gate-to-enforcement summary.
5. `claims/claims.yaml` and `claims/schema.json` — canonical ledger and contract.

## Non-negotiable rules

- Do not mutate this repository without explicit authorization.
- Do not run `git add -A`, `git add .`, force-push, destructive reset, or move a release tag.
- Stage named paths only.
- Do not edit generated reports as if they were canonical sources.
- Do not promote a claim from exploration notes directly.
- Do not change a claim status without a transition record and linked evidence.
- Do not call AI-only review external review or peer review.
- Do not call CI success mathematical review.
- Do not describe a computation without exact bounds, inclusivity, arithmetic behavior, command, environment, and output evidence.
- Do not let an independent verifier import the project implementation under test.
- Do not publish, tag, submit, archive, or release without explicit authorization.
- Report uncertainty and unresolved gaps; never repair them by weakening a statement silently.

## Canonical status model

- Epistemic: `OPEN`, `HEURISTIC`, `COMPUTATIONAL`, `PROVED`, `REFUTED`.
- Verification set: `UNCHECKED`, `INTERNAL_AUDIT`, `INDEPENDENT_REPRODUCTION`, `FORMALIZED`, `EXTERNAL_REVIEW`.
- Publication: `WORKING`, `FROZEN`, `PREPRINT`, `SUBMITTED`, `PUBLISHED`, `CORRECTED`, `WITHDRAWN`.

`UNCHECKED` must appear alone. Verification marks are cumulative. Publication is not evidence of truth.

## Working procedure

Before changing files:

1. identify the affected gate, claim IDs, and canonical sources;
2. inspect the ledger and linked evidence;
3. state whether the task is exploratory, evidentiary, governance, or release-related;
4. use a branch for substantive work;
5. preserve existing history and record limitations.

Before declaring completion:

1. inspect the diff;
2. run the available Cruthúnas policy checks;
3. confirm no protected status changed without evidence;
4. list commands run and anything not run;
5. identify remaining uncertainty explicitly.

## Portable skills

Canonical skills live under `skills/`. Use the narrowest applicable skill. A skill may propose artifacts, but it cannot declare its own gate passed.

## Current maturity

Until the policy kernel, hooks, and required CI are implemented and tested, the framework remains `CR-0` regardless of document completeness.
