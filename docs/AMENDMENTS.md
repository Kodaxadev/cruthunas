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

### 2026-07-31 — Evidence-class authority alignment

**Status:** Draft, pre-release  
**Version decision:** Remain at draft specification v1.0; no released specification exists to version or migrate.

- Replaced the obsolete broad evidence identifiers in Section 8 with the exact typed identifiers already used by the evidence schema and deterministic policy kernel.
- Split internal and external review evidence so AI-only review cannot be represented as external review.
- Added an authority-alignment regression test covering the specification, schema, and CLI constants.

**Compatibility impact:** The executable schema and command interface are unchanged. Pre-release prose references to `SOURCE`, `DERIVATION`, `REVIEW`, or `MANUSCRIPT` as evidence identifiers must use the corresponding typed class.  
**Migration:** None for released projects; no Cruthúnas release or governed-project adoption exists yet.

No released-specification amendments exist yet. These entries record pre-v1.0.0 design evolution and make no backward-compatibility claim.
