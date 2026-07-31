# Repository Structure

Cruthúnas distinguishes the framework repository from repositories that adopt the framework.

## Framework repository

```text
/
├── README.md
├── CRUTHUNAS_SPEC.md             Canonical normative specification
├── RESEARCH_CHARTER.md           Gate 0–10 operational requirements
├── AGENTS.md                     Short vendor-neutral agent map
├── CLAUDE.md                     Claude Code adapter; no independent policy
├── AI_USE.md
├── ATTRIBUTION.md
├── CONTRIBUTIONS.md
├── CORRECTIONS.md
├── LITERATURE.md
├── CITATION.cff
├── claims/
│   ├── claims.yaml               Framework's own claim ledger
│   └── schema.json               Canonical claim-ledger schema
├── schemas/                      Evidence, transition, manifest, exemption schemas
├── skills/                       Canonical portable Agent Skills
│   └── <skill>/
│       ├── SKILL.md
│       ├── scripts/
│       ├── references/
│       └── evals/
├── hooks/                        Deterministic local/agent hook programs
├── src/cruthunas/                Policy CLI and rule engine
├── tests/                        Unit, fixture, mutation, and integration tests
├── templates/                    Governed-project and evidence templates
├── docs/
│   ├── STRUCTURE.md
│   ├── EXECUTION_ARCHITECTURE.md
│   ├── POLICY_MATRIX.md
│   ├── AMENDMENTS.md
│   ├── migration/
│   └── design/
├── .claude/                      Generated Claude skill/hook adapters
├── .codex/                       Generated Codex skill adapters
└── .github/workflows/
    ├── policy.yml                Framework-repository policy checks
    ├── reusable-policy.yml       Reusable governed-project policy workflow
    ├── reusable-reproduce.yml
    ├── reusable-formal.yml
    ├── reusable-manuscript.yml
    ├── release.yml
    └── drift.yml
```

Generated adapters under `.claude/` and `.codex/` derive from `skills/` and hook wiring. CI fails when they drift.

## Governed research repository

```text
/
├── .cruthunas/
│   └── project.yaml              Pinned framework adoption manifest
├── RESEARCH_CHARTER.md           Gate 1 frozen definitions and scope
├── ATTRIBUTION.md                Gate 0 attribution audit
├── LITERATURE.md                 Verified prior sources and searches
├── AI_USE.md                     AI disclosure log
├── CONTRIBUTIONS.md              Human contributor roles; AI separate
├── CORRECTIONS.md                Public correction/withdrawal history
├── CITATION.cff
├── AGENTS.md                     Short project map and local restrictions
├── claims/
│   ├── claims.yaml               Canonical registered-claim ledger
│   └── schema.json               Pinned/copied or referenced compatible schema
├── audit/
│   ├── evidence/
│   │   └── <claim-id>/           Typed evidence records
│   ├── transitions/
│   │   └── <claim-id>/           Status and gate transition records
│   ├── exemptions/               Dated, scoped, expiring policy exemptions
│   ├── evidence-manifest.yaml    Gate 9 release evidence manifest
│   ├── dependency-graph.md       Generated claim dependency graph
│   ├── attribution-audit.md      Gate 8 rerun
│   └── review-log.md             Gate 5 review index
├── docs/
│   ├── proofs/                   Written proofs, normally one per claim ID
│   ├── research-logs/            Gate 3 dated exploration
│   ├── heuristics/               Non-rigorous arguments
│   ├── refutations/              Counterexamples and disproofs
│   └── future-directions/        Parked/deferred work
├── experiments/                  Exploratory and evidentiary computations
├── independent/                  Independent reproductions; no project-code imports
├── formal/                       Proof-assistant formalizations
├── certificates/                 Verifiable computational certificates
├── data/                         Inputs, fixtures, canonical test cases
├── manuscript/                   Paper source; PDFs normally release artifacts
├── scripts/                      Project automation and exact commands
└── .github/workflows/
    ├── cruthunas-policy.yml      Pinned caller for reusable policy workflow
    ├── reproduce.yml
    ├── formal.yml
    └── manuscript.yml
```

## Rules tied to the layout

- `CRUTHUNAS_SPEC.md` is the framework's normative source; project charters may tighten but not weaken it.
- `claims/claims.yaml` is canonical. Markdown claim tables are generated output.
- Exploration is not a registered claim until Gate 4 promotion.
- Every protected status change has a record under `audit/transitions/` and linked evidence.
- Evidence records state both what they establish and what they do not establish.
- `independent/` must not import the implementation under test.
- Generated PDFs and large build artifacts are not committed to ordinary history unless explicitly designated archival source material.
- Release artifacts and source archives carry hashes and provenance records.
- Tool-specific agent adapters may not contain policy absent from canonical specification/skills.
