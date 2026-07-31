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

### 2026-07-31 — Transition-evidence support rules

**Status:** Draft, pre-release  
**Version decision:** Remain at draft specification v1.0; no released specification exists to version or migrate.

- Added `DERIVATION` for heuristic mathematical reasoning that is neither a complete proof nor merely an internal review.
- Added `GATE_DISPOSITION` for typed `not_applicable` gate closures permitted by the lifecycle specification.
- Required the evidence cited by each transition record to support that transition's exact gate or status change; unrelated evidence linked elsewhere on the claim is insufficient.
- Added deterministic requester/originator versus sole-human-approver checks for transitions and claim registration.

**Compatibility impact:** Draft evidence records may use the two new typed classes. Existing draft transitions that cite evidence unrelated to their own promoted axis will fail validation until corrected.  
**Migration:** None for released projects; no Cruthúnas release or governed-project adoption exists yet.

### 2026-07-31 — Experimental project bootstrap and adoption reporting

**Status:** Draft, pre-release  
**Version decision:** Remain at draft specification v1.0; no framework release or conformant governed-project adoption exists.

- Added atomic `cruthunas init` for the minimum governed project structure.
- Separated `experimental` non-conformant commit-pinned use from release-attested `released` adoption.
- Added optional normalized historical aliases while preserving canonical claim IDs for all machine references.
- Added deterministic, non-mutating adoption-gap reporting for structure, historical IDs, pinning, identity, independence, adapters, release compatibility, and manual migrations.
- Clarified proposal originator, record creator, requester, approver, and reviewer roles. Agent-created computation evidence records provenance but cannot establish independent reproduction or external review.

**Compatibility impact:** Existing canonical IDs and transaction commands remain valid. Project manifests created under the draft pre-release schema require an explicit mode when migrated. Historical aliases are optional and cannot replace canonical IDs in dependencies, evidence commands, or transitions.  
**Migration:** Use `cruthunas adoption gaps` to identify required work. Initialization refuses to overwrite existing governed files and does not migrate records automatically.

No released-specification amendments exist yet. These entries record pre-v1.0.0 design evolution and make no backward-compatibility claim.
