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
- [`docs/POLICY_KERNEL.md`](docs/POLICY_KERNEL.md) — implemented validation and atomic mutation surface.
- [`AGENTS.md`](AGENTS.md) — short operational map for coding and research agents.
- [`claims/claims.yaml`](claims/claims.yaml) — canonical machine-readable claim ledger.
- [`claims/schema.json`](claims/schema.json) — ledger contract.

## Enforcement model

```text
specification → schema/policy → CI → local hooks → agent skills → agent output
```

Agent skills guide repeatable work. Hooks catch mistakes early. CI independently enforces merge and release policy. None of these mechanisms confer mathematical external review; that requires a named independent human or documented venue process.

The deterministic implementation currently provides:

- claim-ledger, claim-proposal, evidence, transition, adoption-manifest, and exemption schemas;
- semantic checks for dependencies, evidence-backed statuses, registration history, and transition chains;
- validated-before-write commands for claim proposal, registration, evidence creation, and status/gate transitions;
- workflow action pinning and generated-binary checks;
- independent-verifier import-boundary checks;
- generated Claude/Codex skill adapters with drift detection;
- `cruthunas check`, `cruthunas status`, and adapter commands;
- pre-commit, commit-message, pre-push, and Claude Code hooks;
- a pinned reusable GitHub Actions policy workflow and regression tests.

## Governed mutation workflow

```bash
cruthunas claim propose --help
cruthunas claim register --help
cruthunas evidence add --help
cruthunas claim transition --help
```

Each mutating command validates the complete prospective repository before writing, previews the affected files, and requires confirmation. Use `--dry-run --json` for a machine-readable non-mutating preview. Use `--yes` only when the current task explicitly authorizes the mutation.

## Development quick start

```bash
python -m pip install --requirement requirements/policy.txt --editable .
python -m pytest
cruthunas adapters check
cruthunas check --all
```

Install local Git hooks after the policy checks pass:

```bash
python -m pip install pre-commit
pre-commit install --hook-type pre-commit --hook-type commit-msg --hook-type pre-push
```

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

See [`docs/STRUCTURE.md`](docs/STRUCTURE.md) for the governed-project layout. The framework repository publishes portable skills, schemas, the policy CLI, hook wiring, reusable GitHub Actions workflows, templates, and migration guidance.

## Status

This project remains **CR-0 — Exploration**. The deterministic policy kernel and initial atomic command layer are implemented, but no framework release or end-to-end governed claim has been completed. No project should claim Cruthúnas conformance against an unreleased moving branch.

## License

TBD before the first public framework release.
