# Repository Structure

Canonical layout for a Cruthúnas-governed project.

```
/
├── RESEARCH_CHARTER.md      Gate 1: frozen definitions, notation, scope, stop conditions
├── ATTRIBUTION.md           Gate 0: attribution audits, eponym history
├── LITERATURE.md            Verified prior sources and citations
├── AI_USE.md                AI tool disclosure log
├── CONTRIBUTIONS.md         Human contributor roles (CRediT), AI disclosed separately
├── CORRECTIONS.md           Public post-release correction log and withdrawal procedure
├── CITATION.cff             Machine-readable citation metadata
├── claims/
│   ├── claims.yaml          Canonical machine-readable claim ledger
│   └── schema.json          JSON Schema for claim records
├── docs/
│   ├── STRUCTURE.md         This file
│   ├── proofs/              Written proofs, referenced by claims.yaml source_document
│   ├── research-logs/       Gate 3 exploration: observations, failed arguments, patterns
│   ├── heuristics/          Heuristic arguments not yet promoted to claims
│   ├── refutations/         Documented counterexamples and refuted claims
│   └── future-directions/   Parked or deferred conjectures (Gate 0 PARK decisions)
├── experiments/             Exploratory computational experiments
├── independent/             Independent reproductions; MUST NOT import project code (Gate 2)
├── formal/                  Proof-assistant formalizations (Gate 7)
├── certificates/            Computational certificates / verifiable evidence artifacts
├── data/                    Input data, fixtures, canonical test cases
├── manuscript/              Paper source; release PDFs live on tagged releases, not in history
├── audit/
│   ├── evidence-manifest.yaml   Gate 9 release evidence manifest
│   ├── dependency-graph.md      Claim dependency graph
│   ├── attribution-audit.md     Rerun attribution audit before release (Gate 8)
│   └── review-log.md            Gate 5 adversarial review log (Prover/Falsifier/etc.)
├── scripts/                 Automation, ledger validation, release tooling
└── .github/workflows/       CI: schema validation, pinned toolchains, reproducibility checks
```

## Rules tied to this layout

- Generated PDFs and other build artifacts are never committed to `manuscript/` history; only the tagged release carries the final PDF.
- `independent/` must never import code from elsewhere in the repository (Gate 2).
- `claims/claims.yaml` is canonical; any Markdown claim tables elsewhere are generated output, not sources of truth.
- Nothing in `docs/research-logs/`, `docs/heuristics/`, or `experiments/` is a registered claim until it is promoted into `claims/claims.yaml` via Gate 4.
