---
name: cruthunas-govern
description: Apply the Cruthúnas protocol when a task changes a mathematical claim, its evidence, review status, reproducibility package, manuscript, release, or correction record. Use for governed research work; do not use for casual mathematical explanation that will not modify a governed project.
---

# Cruthúnas Governance

Apply the repository's canonical protocol without inventing a weaker shortcut.

## Start

1. Read `AGENTS.md`.
2. Read `CRUTHUNAS_SPEC.md` and the relevant gate in `RESEARCH_CHARTER.md`.
3. Inspect `.cruthunas/project.yaml` when working in an adopted project.
4. Identify:
   - affected claim IDs;
   - affected gate;
   - canonical files;
   - requested mutation;
   - whether explicit authorization exists;
   - whether the current context originated the claim or evidence.

Do not mutate the repository when authorization is absent or ambiguous. Produce a proposal instead.

## Route the task

- Candidate selection or prior-work triage → Gate 0.
- Definitions, scope, notation, or solution criteria → Gate 1.
- Reproducing published examples independently → Gate 2.
- Searching, experimenting, or recording failed approaches → Gate 3.
- Promoting an exact statement into the ledger → Gate 4.
- Falsification, dependency audit, or proof/statement comparison → Gate 5.
- Finite search, exhaustive computation, certificates, or benchmarks → Gate 6.
- Lean, Coq, Isabelle, or another proof assistant → Gate 7.
- Paper consistency, citations, attribution, limitations, or disclosures → Gate 8.
- Tagging, archival artifacts, DOI, checksums, or publication → Gate 9.
- Error report, correction, demotion, refutation, or withdrawal → Gate 10.

## Required distinctions

Never conflate:

- exploration with a registered claim;
- computational evidence with a universal proof;
- formalization with peer review;
- CI success with mathematical review;
- fresh AI context with external review;
- publication with correctness;
- a restricted theorem with the unresolved broader conjecture.

## Claim work

For a new or changed claim:

1. preserve the exact quantifiers, domain, indexing conventions, and edge cases;
2. list all registered dependencies;
3. state limitations in the claim record, not only in prose;
4. link evidence that establishes the requested status;
5. state what each evidence item does not establish;
6. create a transition record for any status change;
7. do not self-approve the originating work;
8. keep `UNCHECKED` alone or replace it with the applicable cumulative verification marks.

Use the transaction commands instead of editing governed records freehand:

- `cruthunas claim propose` creates a reviewable proposal without entering the ledger;
- `cruthunas claim register` creates the claim, registration evidence, and Gate 3 → 4 transition together;
- `cruthunas evidence add` creates and links an evidence record;
- `cruthunas claim transition` changes claim axes with linked evidence and transition history.

Mutating commands preview and validate the complete prospective state. Use `--yes` only when the current task explicitly authorizes the mutation.

## Computational work

Record all of:

- exact inclusive/exclusive bounds;
- exhaustive versus sampled method;
- algorithm and source revision;
- integer representation and overflow behavior;
- random seeds and locale/environment where relevant;
- exact command;
- toolchain and dependency versions;
- raw output or content-addressed artifact;
- output hash and row/count summary;
- runtime/resource notes;
- independent implementation boundary;
- explicit non-implications.

The independent verifier must not import the project implementation under test.

## Review work

Use separate roles:

- prover;
- falsifier;
- dependency auditor;
- statement auditor;
- formalizer where applicable.

A clean model context may perform an internal role, but its review remains `INTERNAL_AUDIT`. Add `EXTERNAL_REVIEW` only for a named independent human or documented venue process.

## Release work

Do not tag, publish, submit, archive, create a DOI, or upload release assets without explicit authorization.

Before proposing release, verify:

- Gate 8 audit complete;
- exact source revision frozen;
- all required CI at that revision;
- deterministic source and manuscript builds;
- evidence manifest complete;
- artifact hashes recorded;
- review status accurately described;
- correction and withdrawal channels present;
- no existing tag will move.

## Finish

Report:

- files changed;
- claim IDs and gates affected;
- status changes proposed or completed;
- evidence added or invalidated;
- checks and commands run;
- checks not run and why;
- unresolved mathematical or procedural uncertainty.

Never claim a gate passed merely because this skill was followed. Gate completion is established by required evidence and repository policy.
