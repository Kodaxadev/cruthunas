# Research Charter

This document defines the operational requirements for Cruthúnas Gate 0 through Gate 10. `CRUTHUNAS_SPEC.md` is normative when wording here is ambiguous.

## Claim statuses and gates are separate

Every registered claim carries:

- one epistemic status: `OPEN`, `HEURISTIC`, `COMPUTATIONAL`, `PROVED`, or `REFUTED`;
- a cumulative verification set: `UNCHECKED`, `INTERNAL_AUDIT`, `INDEPENDENT_REPRODUCTION`, `FORMALIZED`, and/or `EXTERNAL_REVIEW`;
- one publication status: `WORKING`, `FROZEN`, `PREPRINT`, `SUBMITTED`, `PUBLISHED`, `CORRECTED`, or `WITHDRAWN`;
- the highest lifecycle gate supported by evidence.

`UNCHECKED` appears alone. Formalization, publication, computation, and external review are not interchangeable.

## Gate 0 — Candidate intake

Required before serious work begins:

- exact candidate statement, with ambiguity preserved rather than silently resolved;
- earliest verified source and attribution history;
- known variants and equivalent formulations;
- current status and best known partial results;
- prior computational bounds and available datasets/code;
- active researchers and recent activity;
- plausible mathematical or real-world importance;
- estimated tractability and likely bottlenecks;
- expected software, computation, and formalization requirements;
- reason AI-assisted methods may add leverage now;
- duplication and saturation risk;
- decision: `GO`, `PARK`, or `REJECT`;
- decision date, decision maker, and recheck condition for `PARK`.

No candidate receives an informal eponym before its attribution audit. Gate 0 output is a candidate dossier, not a claim record.

## Gate 1 — Research charter

Freeze:

- definitions;
- notation;
- indexing conventions;
- domain and codomain;
- quantifier order;
- boundary and degenerate cases;
- what constitutes a full solution;
- what constitutes a partial result;
- what does not constitute a solution;
- assumptions and imported facts;
- computational and arithmetic requirements;
- explicit stop conditions;
- repository, branch, and evidence rules;
- amendment procedure.

Changing a frozen definition requires a dated charter amendment and an impact review of existing claims, fixtures, code, and manuscript text.

## Gate 2 — Baseline reproduction

Before claiming new mathematics:

- reproduce published terms, examples, tables, or special cases;
- independently implement the recurrence or mathematical object;
- test boundary cases and index conventions;
- locate conflicting definitions or transcription errors;
- establish canonical fixtures with provenance;
- record tool versions, commands, inputs, outputs, and hashes;
- compare independent and project implementations;
- record every disagreement rather than choosing the preferred output silently.

The independent implementation lives under `independent/` and MUST NOT import project implementation code. Shared published definitions and fixtures are allowed; shared logic embodying the result under test is not.

## Gate 3 — Exploration

Exploration may generate:

- observations;
- candidate invariants;
- failed arguments;
- computational patterns;
- possible lemmas;
- counterexamples;
- alternative formulations;
- parked directions.

Exploration records belong in `docs/research-logs/`, `docs/heuristics/`, `docs/refutations/`, or `docs/future-directions/` as appropriate.

Nothing discovered at Gate 3 is automatically a numbered claim. Exploratory language MUST NOT be copied into a manuscript as an established theorem without Gate 4 registration and later evidence.

## Gate 4 — Claim registration

Every promoted claim receives a permanent ID and a record in `claims/claims.yaml` that validates against `claims/schema.json`.

Example:

```yaml
id: T018
kind: THEOREM
title: "Finite-start stabilization"
statement: "For every integer start s with 1 <= s <= 259, ..."
scope: "Integer starts 1 through 259 inclusive"
epistemic_status: COMPUTATIONAL
verification_statuses:
  - INTERNAL_AUDIT
  - INDEPENDENT_REPRODUCTION
publication_status: WORKING
gate: 6
dependencies: [L003, T014]
evidence:
  - E-T018-0001
  - E-T018-0002
source_document: docs/proofs/T018.md
proof_location: null
computational_support:
  - E-T018-0001
  - E-T018-0002
formal_declarations: []
external_reviews: []
limitations:
  - "Does not establish the corresponding universal claim."
introduced_at: "2026-07-30T19:00:00Z"
updated_at: "2026-07-30T19:00:00Z"
```

Registration requirements:

- exact statement and scope;
- permanent unique ID;
- claim kind;
- complete dependency list;
- source document;
- limitations;
- initial evidence links, if any;
- initial status values;
- date fields.

A restricted result is a separate claim. The broader conjecture remains `OPEN` unless independently resolved.

The ledger is canonical. Markdown tables and dependency graphs are generated from it.

## Gate 5 — Adversarial proof review

A proof cannot be approved solely by the context that derived it. Required roles are executed separately enough to preserve disagreement:

- **Prover** — constructs the argument.
- **Falsifier** — searches for counterexamples, hidden assumptions, and invalid generalization.
- **Dependency auditor** — verifies imported results and conditions.
- **Statement auditor** — checks the proof establishes the exact registered statement.
- **Formalizer** — where feasible, attempts an independent formal translation.

Each review records:

- claim ID and exact version reviewed;
- reviewer identity or system/context identifier;
- inputs provided;
- findings and severity;
- unresolved objections;
- response and disposition;
- whether the reviewer is internal or external.

A fresh AI context is internal AI-assisted review. It may justify `INTERNAL_AUDIT`; it may not justify `EXTERNAL_REVIEW`.

A claim may become `PROVED` after a complete derivation and required internal review, but the originating context may not be the sole approving reviewer. `EXTERNAL_REVIEW` remains a separate verification mark requiring a named independent human or documented venue process.

## Gate 6 — Computational evidence

Every computational evidence record states:

- exhaustive versus sampled method;
- exact search range and inclusivity;
- arithmetic representation and overflow policy;
- algorithm and implementation revision;
- command and working directory;
- inputs, random seeds, locale, timezone, and relevant environment variables;
- toolchain and dependency versions;
- raw output location, count/summary, and hashes;
- runtime and resource requirements;
- independent implementation and its import boundary;
- known missing or unarchived artifacts;
- what the computation establishes;
- what it does not establish.

“Checked extensively,” “verified by computer,” and similarly unbounded wording are prohibited.

A finite computation may support `COMPUTATIONAL` only when the registered statement itself states that finite scope. It does not promote a universal parent claim.

## Gate 7 — Formal verification

Formalization records:

- exact human claim ID and statement version;
- declaration names;
- proof assistant and pinned version;
- dependency lock and versions;
- axioms, classical principles, and trusted code base assumptions;
- absence or presence of placeholders/admitted results;
- whether the formal statement is weaker, equivalent, or stronger;
- mapping of every material hypothesis;
- computations or finite exhaustions that remain outside the assistant;
- exact build command and successful log/hash.

Formalization is a proof-development and verification modality, not decorative validation. Passing Gate 7 may add `FORMALIZED`; it never adds `EXTERNAL_REVIEW` automatically.

Gate 7 may be marked `not_applicable` only with a recorded rationale, approver, and date. A project cannot claim formal verification when the gate is not applicable.

## Gate 8 — Manuscript audit

Before a release candidate:

- every theorem, lemma, corollary, conjecture, and computational statement maps to the claim ledger;
- every citation is verified against its primary source where available;
- attribution audit is rerun;
- novelty language is bounded by documented search evidence;
- code, formalization, ledger, and paper notation agree;
- limitations and unresolved questions are visible;
- computational ranges and inclusivity are preserved exactly;
- AI-use disclosure is complete;
- author responsibility is explicit;
- external-review status is described accurately;
- no stale TODOs, model comments, placeholders, fabricated references, or obsolete results remain;
- manuscript source builds in the canonical environment;
- PDF/source hashes are recorded as draft release evidence.

Gate 8 may set publication status to `FROZEN`. It does not alter epistemic status merely because the prose is polished.

## Gate 9 — Release

A release requires:

- frozen source commit;
- immutable protected version tag;
- deterministic source archive;
- canonical build environment;
- manuscript/source/artifact hashes;
- required CI logs at the exact release revision;
- complete evidence manifest;
- release notes and known limitations;
- correction and withdrawal policy;
- immutable release assets where available;
- archival identifier or explicit statement that one is pending/not used;
- external human review status stated without inflation;
- explicit human authorization to publish.

Generated PDFs and large certificates normally live in workflow or release artifacts, not ordinary Git history.

No release tag may move. A changed artifact requires a new version.

## Gate 10 — Post-release correction

Assume errors will eventually be discovered. Required mechanisms:

- public correction log;
- severity classification;
- affected claim IDs;
- dependency-impact analysis;
- status demotions or refutations where required;
- corrected release and new archival version where appropriate;
- no silent rewriting of published artifacts;
- withdrawal procedure for central failures;
- preservation of the historical record where the venue permits.

A safety-motivated demotion is always allowed. CI must not prevent a correction because the previous promotion record was incomplete.

## Hard operating rules

- No repository mutation without explicit authorization.
- No `git add -A`, `git add .`, or equivalent bulk staging in governed research repositories.
- Stage explicit paths.
- No claim promotion by its originating context acting as sole approver.
- No theorem without a dependency record.
- No computational statement without an exact range and scope.
- No independent verifier that imports project implementation code.
- No generated binary in Git unless explicitly designated archival source material.
- No moving release tags.
- No unpinned action, installer, container, or formal toolchain in a release workflow.
- No novelty or attribution claim based solely on secondary summaries.
- No `EXTERNAL_REVIEW` mark without a named human reviewer or documented venue process.
- No silent correction.
- No continuation of a mathematical branch while its claim ledger is stale.
- No paper release while code, formal statement, ledger, and manuscript statement disagree.

## Framework maturity levels

- **CR-0 — Exploration:** specification exists; enforcement incomplete; no reliability claim.
- **CR-1 — Registered:** canonical spec, charter, schema, and ledger validate.
- **CR-2 — Locally enforced:** portable skills and deterministic local hooks are tested.
- **CR-3 — CI enforced:** policy, transition, and documentation checks are required on protected branches.
- **CR-4 — Reproducible:** a governed project passes clean-room reproduction and evidence packaging.
- **CR-5 — Externally reviewed:** framework and a governed result receive named independent human review.
- **CR-6 — Released:** immutable versioned framework release, adoption path, and correction process are operational.

A project cannot skip levels because a proof assistant, large computation, or AI review is available.
