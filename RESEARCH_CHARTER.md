# Research Charter

This document defines Cruthúnas's mandatory lifecycle gates. A conjecture, theorem, or scientific claim governed by this framework must pass through these gates in order. Skipping a gate, or collapsing distinct statuses into one label, is a process violation.

## Three independent status axes

Every claim record carries three separate statuses, tracked independently:

**Epistemic status**: OPEN, HEURISTIC, COMPUTATIONAL, PROVED, REFUTED

**Verification status**: UNCHECKED, INTERNAL_AUDIT, INDEPENDENT_REPRODUCTION, FORMALIZED, EXTERNAL_REVIEW

**Publication status**: WORKING, FROZEN, PREPRINT, SUBMITTED, PUBLISHED, CORRECTED, WITHDRAWN

Common errors this prevents: formalized therefore peer-reviewed; computed to 10^7 therefore proved; CI green therefore mathematically reviewed; preprint therefore published; AI adversarial review therefore external review.

## Gate 0 — Candidate intake

Required before serious work begins:

- exact conjecture/claim statement
- earliest verified source
- attribution history
- known variants
- current status
- prior computational bounds
- active researchers and recent activity
- likely importance or application
- estimated tractability
- expected software and formalization requirements
- reason new tooling (including AI-assisted methods) may add leverage
- decision: GO, PARK, or REJECT

No conjecture receives an informal eponym before the attribution audit.

## Gate 1 — Research charter

Freeze:

- definitions
- notation
- index conventions
- domain and edge cases
- what constitutes a solution
- what does not constitute a solution
- initial assumptions
- computational/arithmetic requirements
- explicit stop conditions
- repository and branch rules

Changing a definition later requires a recorded charter amendment.

## Gate 2 — Baseline reproduction

Before looking for new mathematics:

- reproduce published terms and examples
- independently implement the recurrence or mathematical object
- test boundary cases
- locate conflicting definitions
- establish canonical fixtures
- record tool versions and hashes

The independent implementation must not import project code. This separation lives in `independent/`.

## Gate 3 — Exploration

Exploration can generate: observations, candidate invariants, failed arguments, computational patterns, possible lemmas, counterexamples.

Nothing discovered here is automatically a numbered claim. Exploration belongs in `docs/research-logs/` until promoted through the claim gate.

## Gate 4 — Claim registration

Every promoted claim receives a permanent ID and record in `claims/claims.yaml`:

```yaml
id: T018
statement: "..."
status: PROVED
dependencies: [L003, T014]
source_document: docs/proofs/finite-start.md
proof_location: theorem-18
computational_support: null
formal_declaration: Conjecture.finite_start_of_increment
independent_review: pending
limitations: "..."
introduced_commit: "..."
last_changed_commit: "..."
```

The machine-readable claim ledger is canonical. Markdown tables are generated from it, never maintained separately.

## Gate 5 — Adversarial proof review

A proof cannot be approved by the same context that derived it. Required roles:

- **Prover** — constructs the argument
- **Falsifier** — searches for counterexamples and hidden assumptions
- **Dependency auditor** — verifies every imported result
- **Statement auditor** — checks the proved statement exactly matches the registered statement
- **Formalizer** (where feasible) — translates the argument independently

A fresh model context is useful, but remains internal AI-assisted review, not external mathematical review.

## Gate 6 — Computational evidence

Every computational claim must record: exhaustive vs. sampled; exact search range; inclusivity of bounds; integer type or arbitrary precision; algorithm; source commit; command; inputs and random seeds; output row count; output hash; runtime environment; independent implementation; known unarchived artifacts; what the computation does not establish.

"Checked extensively" is prohibited wording.

## Gate 7 — Formal verification

Formalization must record: exact human theorem it corresponds to; declaration name; proof-assistant and version; dependency versions; admitted axioms; absence of placeholders (e.g. `sorry`); whether the formal statement is weaker, equivalent, or stronger; which computational exhaustions remain outside the assistant.

Formalization is a proof-development tool, not final decorative validation.

## Gate 8 — Manuscript audit

Before a release candidate:

- every theorem maps to the claim ledger
- every citation is verified against the primary source
- attribution audit rerun
- novelty claims softened unless independently established
- code and paper notation compared
- limitations included
- computational ranges preserved
- AI-use disclosure included
- author responsibility explicit
- no stale TODOs, model comments, placeholders, or fabricated references

## Gate 9 — Release

A release requires: frozen commit; protected tag; deterministic source archive; canonical build environment; PDF and source hashes; CI logs; evidence manifest; release notes; correction policy; immutable release assets where available; DOI archival; external human review status accurately stated.

## Gate 10 — Post-release correction

Assume errors will eventually be discovered. Required mechanisms: public correction log; severity classification; affected claim IDs; whether dependencies remain valid; corrected release; new DOI version where appropriate; no silent rewriting of published artifacts; withdrawal procedure for central failures.

## Hard operating rules

- No repository mutation without explicit authorization.
- No `git add -A` in research repositories. Stage explicit paths.
- No claim promotion by its originating context.
- No theorem without a dependency record.
- No computational statement without an exact range.
- No "independent" verifier that imports project implementation code.
- No generated binary in Git unless explicitly designated archival source material.
- No moving tags attached to releases.
- No unpinned action, installer, container, or formal toolchain in a release workflow.
- No novelty or attribution claim based solely on secondary summaries.
- No external-review label without a named human reviewer or formal venue process.
- No silent correction.
- No continuation of a mathematical branch while its claim ledger is stale.
- No paper release while code, formal statement, and manuscript statement disagree.

## Framework maturity levels

- **CW-0 — Exploration**: no reliability claim.
- **CW-1 — Registered**: charter, attribution, and ledger exist.
- **CW-2 — Internally verified**: proofs audited and computations reproduced.
- **CW-3 — Reproducible package**: clean-room build and evidence package pass.
- **CW-4 — Preprint candidate**: manuscript and release audit pass.
- **CW-5 — Externally reviewed**: named human mathematical review completed.
- **CW-6 — Published**: accepted by a venue or released with an immutable scholarly record.

A project cannot skip levels merely because a proof assistant or a large computation is available.
