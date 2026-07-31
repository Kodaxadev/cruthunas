# Cruthúnas Amendments

Normative changes to a released Cruthúnas specification are recorded here. Tagged historical specifications are immutable.

## Entry template

```yaml
date: YYYY-MM-DD
specification_from: vX.Y.Z
specification_to: vX.Y.Z
pull_request: <reference>
classification: PATCH | MINOR | MAJOR
summary: <what changed>
rationale: <why>
compatibility_impact: <affected schemas, commands, projects, or evidence>
migration: <migration document or none>
```

## Draft history

### 2026-07-30 — Execution-layer reconciliation

**Status:** Draft, pre-release

- Established `CRUTHUNAS_SPEC.md` as the single normative source.
- Reconciled the duplicate Gate 0–10 models.
- Replaced a destructive single verification enum with cumulative verification marks.
- Corrected the claim schema to validate the actual ledger root.
- Removed self-referential commit fields from claim records.
- Renamed framework maturity levels from `CW-*` to `CR-*`.
- Defined the authority boundary among specifications, policy code, CI, hooks, skills, and agents.
- Added typed evidence, transition, project-adoption, and exemption records.
- Required a Gate 3 → Gate 4 registration transition backed by `CLAIM_REGISTRATION` evidence.
- Defined transition records as full before/after axis states so their chains can be audited deterministically.
- Implemented the first policy kernel, generated-adapter checks, local hooks, Claude Code hooks, and reusable policy CI.

No released-specification amendments exist yet. This entry records pre-v1.0.0 design evolution and makes no backward-compatibility claim.
