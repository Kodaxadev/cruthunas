# Cruthúnas Governance Specification v1.0

Status: DRAFT
Applies to: all claims tracked under this repository and any repository that adopts Cruthúnas as its governance layer.

## 1. Purpose

Cruthúnas is a provenance and verification governance framework for mathematical (and mathematics-adjacent computational) research. It exists to prevent unverified or prematurely-confident claims from being mistaken for established results, by enforcing:

- machine-checkable status tracking for every claim
- a staged lifecycle (Gate 0 through Gate 10) that a claim must pass through
- separation of authorship from AI tooling assistance
- reproducibility of every computational claim
- an auditable history of corrections

## 2. Three-Axis Status Model

Every claim tracked in claims/claims.yaml MUST carry three independent status axes. No axis may be inferred from another.

### 2.1 Epistemic status
- conjecture — believed plausible, no proof attempt formalized
- heuristic — supported by non-rigorous argument or pattern
- partial-proof — rigorous proof of a restricted case
- proof — complete rigorous proof, gate-verified
- refuted — counterexample or disproof found
- withdrawn — retracted by author(s) independent of refutation

### 2.2 Verification status
- unverified
- self-checked — author-only review
- peer-reviewed — reviewed by a qualified independent party (named in claims.yaml)
- machine-checked — verified by formal proof assistant or exhaustive computation with pinned environment
- independently-reproduced — a separate party reproduced the result from scratch

### 2.3 Publication status
- internal — not released
- preprint
- published
- corrected — published with a linked correction in CORRECTIONS.md
- retracted

## 3. Stage Gates

A claim advances linearly. A claim MAY be demoted at any time; it may never skip a gate.

- Gate 0 — Intake: claim registered in claims.yaml with a unique ID, plain-language statement, and epistemic status = conjecture.
- Gate 1 — Formalization: claim restated in precise mathematical language with all quantifiers, domains, and edge cases explicit.
- Gate 2 — Literature check: search performed and logged in LITERATURE.md confirming the claim is not already proven, refuted, or trivially equivalent to known results.
- Gate 3 — Dependency mapping: every lemma/result the claim depends on is itself listed in claims.yaml with its own status. A claim may not cite an unregistered dependency.
- Gate 4 — Heuristic/exploratory evidence: numerical or heuristic support gathered under experiments/, with exact parameter ranges and seeds recorded.
- Gate 5 — Proof attempt: a proof draft is written in docs/proofs/ with every step justified or explicitly marked as a gap.
- Gate 6 — Internal review: self-check against the proof draft; all gaps from Gate 5 resolved or the claim is demoted to heuristic.
- Gate 7 — Independent review: a named qualified reviewer (human or accepted formal method) checks the proof; disagreements logged.
- Gate 8 — Machine verification (where applicable): formal proof assistant certificate, or exhaustive/verified computation with a pinned, reproducible toolchain.
- Gate 9 — Reproducibility packaging: environment, code, data, and exact commands archived so an independent party can reproduce the result without contacting the author.
- Gate 10 — Release: claim is eligible for preprint/publication with a permanent identifier (e.g., DOI via Zenodo) and a frozen snapshot of all supporting artifacts.

## 4. Hard Rules

1. No claim may be promoted in epistemic status by the person or process that originated it without passing through Gate 7 (independent review).
2. No computational claim may be recorded without an exact parameter range, toolchain version, and seed/locale where randomness or locale-dependent behavior is possible.
3. No theorem-level claim may be registered without its dependency list (Gate 3).
4. No `git add -A` (or equivalent bulk-stage) in this repository; every commit stages named files deliberately.
5. No silent mutation of a claim's status fields — every status change is a new commit with a message referencing the claim ID and the gate transition.
6. Every correction to a published claim is logged in CORRECTIONS.md before the claim's publication status may read "corrected."
7. AI tool usage in producing or checking any claim must be disclosed in AI_USE.md, including which gates it assisted with. AI assistance never substitutes for Gate 7 independent review.

## 5. Reproducibility Standard

Any claim resting on computation must ship:
- exact toolchain name and pinned version
- fixed random seeds
- fixed locale/environment where behavior could vary
- the exact command(s) used to produce the result
- raw output retained under experiments/ or data/

## 6. Framework Maturity Levels (CW-0 .. CW-6)

- CW-0 — Skeleton only; no claims processed end-to-end.
- CW-1 — At least one claim has passed Gate 0–3.
- CW-2 — At least one claim has passed Gate 4 (heuristic evidence gathered and reproducible).
- CW-3 — At least one claim has a full proof draft (Gate 5) with internal review (Gate 6).
- CW-4 — At least one claim has passed independent review (Gate 7).
- CW-5 — At least one claim is machine-checked or fully reproducibility-packaged (Gate 8–9).
- CW-6 — At least one claim has been released (Gate 10) with a permanent identifier.

## 7. Repository Roles

- claims/claims.yaml — canonical machine-readable ledger; all Markdown claim tables are generated from this file, never edited by hand independently.
- claims/schema.json — JSON Schema validating claims.yaml.
- docs/proofs/ — proof drafts, one file per claim ID.
- docs/research-logs/ — dated working logs.
- docs/heuristics/ — non-rigorous supporting arguments.
- docs/refutations/ — counterexamples and disproofs.
- docs/future-directions/ — open threads not yet claims.
- experiments/ — reproducible computational evidence.
- AI_USE.md, ATTRIBUTION.md, CONTRIBUTIONS.md, CORRECTIONS.md, LITERATURE.md, RESEARCH_CHARTER.md — governance and provenance documents as defined in this repository's root.

## 8. Amendments

This specification may only be amended by a dated entry appended below this line, never by silently editing prior sections.

---

_No amendments recorded yet._
