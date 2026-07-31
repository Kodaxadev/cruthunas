# Cruthúnas Specification v1.0

**Status:** DRAFT  
**Authority:** This file is the canonical normative specification. `RESEARCH_CHARTER.md` expands the gates; implementation documents may not redefine them.  
**Scope:** Mathematical and mathematics-adjacent computational research governed by Cruthúnas.

## 1. Purpose

Cruthúnas governs the path from an interesting candidate to a traceable scholarly result:

```text
candidate → attribution → charter → reproduction → exploration → claim
          → adversarial review → computation/formalization → manuscript
          → release → correction
```

Its purpose is not to guarantee that a result is correct. Its purpose is to make the basis for every confidence claim explicit, machine-checkable where possible, independently inspectable, and correctable without rewriting history.

## 2. Normative language

The words **MUST**, **MUST NOT**, **REQUIRED**, **SHOULD**, **SHOULD NOT**, and **MAY** are normative.

A repository claiming Cruthúnas conformance MUST identify the exact framework version or commit it follows. It MUST NOT claim conformance to an unpinned moving branch.

## 3. Sources of truth

The following precedence order applies:

1. `CRUTHUNAS_SPEC.md` — normative rules and invariants.
2. `RESEARCH_CHARTER.md` — gate requirements and research procedure.
3. `claims/claims.yaml` — canonical registered-claim ledger.
4. `claims/schema.json` — machine-readable ledger contract.
5. `audit/` evidence records — transitions, reviews, release evidence, and corrections.
6. `docs/` — explanatory material and human-readable reports.
7. Generated reports — derived output only; never independent sources of truth.

When two sources disagree, the higher source wins and the disagreement MUST fail validation until corrected.

## 4. Core invariants

1. A claim has a permanent ID and is never deleted to conceal a failed result.
2. Exploration is not a registered claim.
3. A computation is not a proof merely because it is large, exhaustive over an unspecified range, or reproducible.
4. Formalization is not peer review.
5. CI success is not mathematical review.
6. A fresh AI context is still internal AI-assisted review, not external review.
7. No status may be promoted without evidence linked from the ledger.
8. No published artifact may be silently replaced.
9. Every correction identifies affected claims and downstream dependencies.
10. The originating context or agent may not serve as the sole approving reviewer of its own claim.

## 5. Three-axis claim model

The lifecycle gate and the claim statuses are separate concepts. A gate records process completion. The three axes record what is currently known about a claim.

### 5.1 Epistemic status

Exactly one value is active:

- `OPEN` — registered question or statement not established.
- `HEURISTIC` — supported by non-rigorous reasoning, patterns, or incomplete argument.
- `COMPUTATIONAL` — established only for an explicitly bounded computational domain or by a computational certificate whose scope is stated.
- `PROVED` — supported by a complete mathematical proof for the exact registered statement.
- `REFUTED` — contradicted by a valid counterexample or disproof.

A restricted theorem MUST be registered as its own claim. It MUST NOT be represented by labeling a broader unresolved statement `PROVED` with a limitation hidden in prose.

`COMPUTATIONAL` and `PROVED` are not ordered substitutes. A claim may have computational support while its epistemic status is `PROVED`; that support is recorded as evidence, not by replacing the proof status.

### 5.2 Verification axis

Verification is a cumulative set because different forms may coexist:

- `UNCHECKED` — no recorded review. This value MUST appear alone.
- `INTERNAL_AUDIT` — checked by the author, originating team, or internal AI process.
- `INDEPENDENT_REPRODUCTION` — independently reproduced without importing the project implementation under test.
- `FORMALIZED` — represented and checked in a named proof assistant with declarations and assumptions recorded.
- `EXTERNAL_REVIEW` — reviewed by a named human independent of the originating process or through a documented venue process.

Adding one verification mark MUST NOT erase another. `EXTERNAL_REVIEW` requires a reviewer identity or venue record. AI-only review cannot set it.

### 5.3 Publication status

Exactly one value is active:

- `WORKING`
- `FROZEN`
- `PREPRINT`
- `SUBMITTED`
- `PUBLISHED`
- `CORRECTED`
- `WITHDRAWN`

Publication status describes dissemination, not truth. `PUBLISHED` does not imply `PROVED`; `FORMALIZED` does not imply `PUBLISHED`.

## 6. Lifecycle gates

The canonical gates are:

- **Gate 0 — Candidate intake:** exact candidate, attribution status, prior work, activity, impact, tractability, tooling, and GO/PARK/REJECT decision.
- **Gate 1 — Research charter:** definitions, notation, scope, edge cases, solution criteria, assumptions, stop conditions, and repository rules frozen.
- **Gate 2 — Baseline reproduction:** published examples and terms reproduced by an implementation independent of project code; canonical fixtures established.
- **Gate 3 — Exploration:** observations, failed approaches, patterns, counterexamples, and candidate lemmas recorded without claim promotion.
- **Gate 4 — Claim registration:** exact statement, scope, dependencies, evidence links, limitations, and permanent ID entered in the ledger.
- **Gate 5 — Adversarial proof review:** prover, falsifier, dependency auditor, and statement auditor roles executed and recorded.
- **Gate 6 — Computational evidence:** ranges, inclusivity, arithmetic, algorithm, environment, commands, outputs, hashes, and independent implementation recorded.
- **Gate 7 — Formal verification:** formal statement correspondence, toolchain, dependencies, axioms, placeholders, and out-of-assistant computations recorded. A justified `not_applicable` disposition is permitted.
- **Gate 8 — Manuscript audit:** every theorem maps to the ledger; citations, attribution, novelty language, notation, limitations, computational ranges, and AI disclosure are checked.
- **Gate 9 — Release:** frozen source, protected tag, deterministic build, evidence manifest, hashes, release notes, immutable assets, archival record, and review status published.
- **Gate 10 — Post-release correction:** corrections, dependency impact, replacement versions, withdrawals, and public history maintained.

A project MUST NOT skip a gate. A gate that is genuinely inapplicable MAY be closed with a recorded `not_applicable` disposition, rationale, approver, and date. Gate 7 is the expected use case; Gate 0, Gate 1, Gate 4, Gate 8, Gate 9, and Gate 10 are never optional for a released claim.

## 7. Transitions

Every status or gate transition MUST:

1. identify the claim ID;
2. record the previous and new value;
3. link the evidence that justifies the change;
4. identify the actor requesting the transition;
5. identify the reviewer or automated policy that approved it;
6. be committed separately enough to remain auditable;
7. use a commit or pull-request title containing the claim ID and transition.

Demotions and refutations are always permitted when new evidence requires them. CI MUST block promotions that lack required evidence. CI MUST NOT block a safety-motivated demotion merely because the earlier promotion evidence is unavailable.

## 8. Evidence classes

Every evidence record uses exactly one of these typed classes:

- `ATTRIBUTION` — primary literature, provenance, or attribution evidence.
- `CHARTER` — frozen definitions, scope, assumptions, or research-charter evidence.
- `BASELINE` — published examples, canonical fixtures, or baseline-reproduction evidence.
- `CLAIM_REGISTRATION` — evidence that an exact statement, scope, dependencies, and limitations were registered at Gate 4.
- `PROOF` — a written mathematical derivation or proof for the exact registered statement.
- `COMPUTATION` — an executable search, experiment, certificate, or bounded computational result.
- `REPRODUCTION` — an independent reimplementation and result-comparison record.
- `FORMALIZATION` — proof-assistant declarations, assumptions, mappings, and build evidence.
- `REVIEW_INTERNAL` — structured review by the originator, originating team, or an internal AI-assisted process.
- `REVIEW_EXTERNAL` — structured review by a named independent human or documented venue process.
- `MANUSCRIPT_AUDIT` — audited manuscript source, theorem mapping, citation review, and build evidence.
- `RELEASE` — frozen artifacts, hashes, attestations, archival identifiers, and release evidence.
- `CORRECTION` — a post-release correction, replacement, or withdrawal record.
- `REFUTATION` — a counterexample, disproof, or other evidence establishing that a registered claim is false.

`REVIEW_EXTERNAL` MUST identify a human reviewer or venue. AI-only review uses `REVIEW_INTERNAL` and cannot establish `EXTERNAL_REVIEW`. Every evidence record MUST state what it establishes and what it does not establish.

## 9. Independence

An independent reproduction or review MUST document:

- the person, context, or system performing it;
- its relationship to the originator;
- the inputs it received;
- whether it saw the original implementation or proof;
- the implementation and dependency boundary;
- the result and any disagreement.

An independent computational verifier MUST NOT import project implementation code. Shared fixtures and published mathematical definitions are permitted; shared algorithms or helper libraries that embody the result under test are not.

## 10. AI use

AI systems are tools, not authors. Every material use MUST be disclosed by gate and task. Records SHOULD include provider, product, model identifier when available, date, context role, inputs or references supplied, and whether outputs were independently checked.

AI may assist with exploration, implementation, proof search, falsification, formalization, editing, and policy checks. It may not create an `EXTERNAL_REVIEW` mark. The named human authors remain responsible for claims released under their names.

## 11. Reproducibility

A computational result MUST include:

- exact source revision;
- exact command;
- pinned interpreter/compiler and dependencies;
- operating-system or container identity;
- locale, timezone, environment variables, and random seeds when relevant;
- exact inclusive/exclusive bounds;
- integer representation and overflow policy;
- input and output hashes;
- raw or content-addressed outputs;
- expected runtime and resource requirements;
- a statement of scope and non-implications.

A release build MUST succeed in a clean canonical environment. Repeating a build twice on the same mutable machine is not independent reproduction.

## 12. Agent guidance, hooks, and CI

Agent instructions and skills are advisory workflow guidance. Hooks are local deterministic guardrails. CI is the repository authority. A local bypass never changes the validity requirements enforced by CI.

The binding execution architecture is defined in `docs/EXECUTION_ARCHITECTURE.md`.

## 13. Framework maturity

- **CR-0 — Exploration:** specification exists; enforcement is incomplete; no reliability claim.
- **CR-1 — Registered:** canonical spec, charter, schemas, and ledger validate.
- **CR-2 — Locally enforced:** portable skills and deterministic local hooks are tested.
- **CR-3 — CI enforced:** policy, schema, transition, and documentation checks are required on protected branches.
- **CR-4 — Reproducible:** at least one governed project passes clean-room reproduction and evidence packaging.
- **CR-5 — Externally reviewed:** the framework and at least one governed result have named independent human review.
- **CR-6 — Released:** versioned framework release, immutable artifacts, adoption documentation, and correction process are operational.

Maturity is determined by evidence, not declaration.

## 14. Amendments

Normative amendments require:

- a pull request describing the problem and compatibility impact;
- a specification version decision;
- schema and test updates where applicable;
- migration notes for governed repositories;
- a dated entry in `docs/AMENDMENTS.md`.

Historical tagged specifications are immutable. Corrections create a new version; they do not rewrite a published tag.
