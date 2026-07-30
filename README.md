# Cruthúnas

**Cruthúnas** (Irish: *evidence or argument sufficient to establish that something is true*) is a reusable governance and verification framework for the complete lifecycle of a mathematical or mathematics-adjacent computational claim:

```text
candidate → attribution → charter → reproduction → exploration → claim
          → adversarial review → computation/formalization → manuscript
          → release → correction
```

It exists to prevent avoidable failures caused by research, formal verification, AI assistance, and release engineering evolving informally or out of order: late attribution corrections, proof gaps found only during formalization, bounded computations described as universal results, stale claim ledgers, accidental generated-artifact commits, and reproducibility that means only “the same machine twice.”

## Core principle

Every registered claim separates:

- **Epistemic status** — `OPEN`, `HEURISTIC`, `COMPUTATIONAL`, `PROVED`, `REFUTED`.
- **Verification marks** — `UNCHECKED`, `INTERNAL_AUDIT`, `INDEPENDENT_REPRODUCTION`, `FORMALIZED`, `EXTERNAL_REVIEW`.
- **Publication status** — `WORKING`, `FROZEN`, `PREPRINT`, `SUBMITTED`, `PUBLISHED`, `CORRECTED`, `WITHDRAWN`.

Verification marks are cumulative; `UNCHECKED` appears alone. Publication never implies correctness. Formalization and CI never imply peer review.

## Canonical documents

- [`CRUTHUNAS_SPEC.md`](CRUTHUNAS_SPEC.md) — normative specification and invariants.
- [`RESEARCH_CHARTER.md`](RESEARCH_CHARTER.md) — Gate 0 through Gate 10 procedure.
- [`docs/EXECUTION_ARCHITECTURE.md`](docs/EXECUTION_ARCHITECTURE.md) — portable skills, local hooks, CLI, CI, releases, and adoption.
- [`docs/POLICY_MATRIX.md`](docs/POLICY_MATRIX.md) — gate-to-evidence and enforcement map.
- [`AGENTS.md`](AGENTS.md) — short operational map for coding and research agents.
- [`claims/claims.yaml`](claims/claims.yaml) — canonical machine-readable claim ledger.
- [`claims/schema.json`](claims/schema.json) — ledger contract.

## Enforcement model

```text
specification → schema/policy → CI → local hooks → agent skills → agent output
```

Agent skills guide repeatable work. Hooks catch mistakes early. CI independently enforces merge and release policy. None of these mechanisms confer mathematical external review; that requires a named independent human or documented venue process.

## Lifecycle gates

The canonical lifecycle is defined in [`RESEARCH_CHARTER.md`](RESEARCH_CHARTER.md):

0. Candidate intake
1. Research charter
2. Baseline reproduction
3. Exploration
4. Claim registration
5. Adversarial proof review
6. Computational evidence
7. Formal verification
8. Manuscript audit
9. Release
10. Post-release correction

## Repository layout

See [`docs/STRUCTURE.md`](docs/STRUCTURE.md) for the governed-project layout. The framework repository will additionally publish portable skills, schemas, a policy CLI, hook wiring, reusable GitHub Actions workflows, templates, and migration guides.

## Status

This project is at maturity level **CR-0 — Exploration**. The specification and execution architecture exist, but the deterministic policy kernel, tested hooks, required CI, and first end-to-end governed case are not yet complete. No reliability or conformance claim is made yet.

## License

TBD before the first public framework release.
