# Cruthúnas

**Cruthúnas** (Irish: *evidence or argument sufficient to establish that something is true*) is a reusable framework for governing the complete lifecycle of a mathematical (or scientific) claim:

```
candidate → attribution → exploration → claim → verification → paper → external review → release → correction
```

It exists to prevent the class of avoidable failures that occur when exploratory research, formal verification, and release engineering evolve informally and out of order: late attribution fixes, proof gaps found only during formalization, stale PR/issue descriptions, accidental generated-artifact commits, and reproducibility that means "same machine twice" instead of "canonical environment."

## Core principle

Every claim carries three independent status axes. They are never collapsed into a single label:

- **Epistemic status** — OPEN, HEURISTIC, COMPUTATIONAL, PROVED, REFUTED
- **Verification status** — UNCHECKED, INTERNAL_AUDIT, INDEPENDENT_REPRODUCTION, FORMALIZED, EXTERNAL_REVIEW
- **Publication status** — WORKING, FROZEN, PREPRINT, SUBMITTED, PUBLISHED, CORRECTED, WITHDRAWN

## Lifecycle gates

See [RESEARCH_CHARTER.md](RESEARCH_CHARTER.md) for the full gate specification (Gate 0 Candidate Intake through Gate 10 Post-Release Correction).

## Repository layout

See [docs/STRUCTURE.md](docs/STRUCTURE.md) for the canonical directory layout.

## Status

This project is at maturity level **CW-0 — Exploration**. No reliability claim is made until Gate 1 (Research Charter) is frozen and CI enforcement exists.

## License

TBD.
