# Cruthúnas Execution Architecture

**Status:** DRAFT implementation contract  
**Normative parent:** `CRUTHUNAS_SPEC.md`

This document defines how the written protocol becomes an enforceable system. It separates four concerns that must not be conflated:

1. **Knowledge** — specifications, charters, schemas, and evidence.
2. **Agent workflow** — portable skills and short repository instructions.
3. **Local enforcement** — deterministic hooks that catch errors early.
4. **Repository enforcement** — CI and branch rules that decide whether a change may merge or release.

Agent compliance is useful but never trusted as the enforcement boundary.

## 1. System topology

Cruthúnas has two repository roles.

### 1.1 Framework repository

`Kodaxadev/cruthunas` publishes:

- normative specifications;
- JSON Schemas and policy profiles;
- the `cruthunas` validation CLI;
- portable Agent Skills;
- local-hook installers;
- reusable GitHub Actions workflows;
- project templates and migration guides;
- versioned releases and checksums.

### 1.2 Governed research repository

A research repository adopts a pinned framework release and contains its own:

- `.cruthunas/project.yaml` adoption manifest;
- `RESEARCH_CHARTER.md`;
- attribution and literature records;
- `claims/claims.yaml`;
- proofs, experiments, independent reproductions, and formalizations;
- audit records and release evidence;
- a small caller workflow pinned to a Cruthúnas tag or commit.

The framework repository does not become the source of mathematical truth for every project. Each project owns its claim ledger and evidence. Cruthúnas owns the contract and validators.

## 2. Authority model

The execution layers have strict precedence:

```text
specification → schema/policy → CI → local hooks → agent skills → agent output
```

- A skill MAY suggest a workflow.
- A hook MAY reject an unsafe local action.
- CI MUST independently rerun every merge-critical rule.
- Only protected-branch CI and required human decisions authorize merge or release.
- No agent message, hook success, or local test result can override a failing required check.

## 3. Adoption manifest

Every governed project MUST provide `.cruthunas/project.yaml`:

```yaml
schema_version: 1
framework:
  repository: Kodaxadev/cruthunas
  version: v1.0.0
  commit: <full-40-character-sha>
profile: mathematics
project:
  id: cloitre-recurrence
  title: "Cloitre recurrence research"
  maintainers:
    - github: Kodaxadev
canonical:
  claim_ledger: claims/claims.yaml
  research_charter: RESEARCH_CHARTER.md
  evidence_root: audit/evidence
  transition_root: audit/transitions
  release_manifest: audit/evidence-manifest.yaml
toolchains:
  python: "3.13.5"
  lean: null
policies:
  require_external_review_for_publication: false
  require_external_review_label_for_external_review_status: true
  forbid_generated_binaries_in_git: true
  require_independent_computation_for_computational_claims: true
```

Rules:

- `version` and `commit` MUST agree.
- `main`, `latest`, or another moving reference MUST NOT be used.
- A profile MAY tighten the base specification but MUST NOT weaken a MUST rule.
- Project-specific exemptions live in `audit/exemptions/`, never inline as unstructured comments.

## 4. Portable Agent Skills

### 4.1 Canonical storage

Canonical skills live in:

```text
skills/<skill-name>/SKILL.md
skills/<skill-name>/scripts/
skills/<skill-name>/references/
skills/<skill-name>/assets/
```

The skill format follows the portable Agent Skills convention: a folder centered on `SKILL.md` with narrowly scoped instructions and optional executable resources.

The canonical copy is vendor-neutral. Tool-specific discovery directories are generated adapters, not independent authored copies:

```text
.claude/skills/<skill-name>/
.codex/skills/<skill-name>/
```

`cruthunas adapters sync` copies canonical skills into supported tool directories and records a source hash. `cruthunas adapters check` fails if an adapter drifts from its canonical source. Symlinks are not required because Windows checkout behavior is inconsistent across developer environments.

### 4.2 Skill boundaries

A skill encodes a repeatable process. It MUST NOT:

- claim that its own output passed a gate;
- mutate a status without invoking the transition workflow;
- label AI review as external review;
- bypass hooks or CI;
- silently edit canonical evidence;
- combine originating and approving roles in one context.

### 4.3 Initial skill set

#### `candidate-intake`

Use for Gate 0. Produces a candidate dossier containing exact statement, attribution trail, prior results, current activity, application/importance hypothesis, tractability, tool requirements, and GO/PARK/REJECT recommendation. It does not register a claim.

#### `charter-freeze`

Use for Gate 1. Converts a selected candidate into frozen definitions, notation, scope, edge cases, solution criteria, assumptions, stop conditions, and amendment rules.

#### `baseline-reproduction`

Use for Gate 2. Builds or audits an implementation that does not import the project implementation, reproduces published fixtures, and records disagreements.

#### `claim-register`

Use for Gate 4. Creates a proposed exact claim record and dependency list. It invokes `cruthunas claim propose`; it never edits status fields freehand.

#### `proof-falsification`

Use for Gate 5 in a clean context. Searches for hidden assumptions, quantifier changes, dependency failures, counterexamples, and mismatches between the proof and registered statement. Its result is an internal review record unless a named independent human performed it.

#### `computation-package`

Use for Gate 6. Captures bounds, inclusivity, integer semantics, algorithm, commands, versions, seeds, outputs, hashes, runtime, independent implementation, and non-implications.

#### `formalization-audit`

Use for Gate 7. Maps human claims to formal declarations, checks toolchain and axioms, rejects placeholders, and states whether the formal theorem is weaker, equivalent, or stronger.

#### `manuscript-audit`

Use for Gate 8. Maps every theorem and computational statement to the ledger and verifies attribution, citations, notation, limitations, disclosures, and stale text.

#### `release-audit`

Use for Gate 9. Runs the release checklist and produces a proposed evidence manifest. It cannot publish or tag without explicit authorization.

#### `correction-assessment`

Use for Gate 10. Classifies severity, traces dependency impact, proposes demotions/refutations, and drafts correction or withdrawal records.

### 4.4 Skill evaluation

Every skill MUST have evaluation fixtures:

```text
skills/<name>/evals/cases.yaml
skills/<name>/evals/expected/
```

Cases include:

- positive triggers;
- near-miss prompts where the skill should not activate;
- malformed project states;
- attempts to bypass required evidence;
- attempts to overstate verification or review.

A skill is not considered stable because it worked once. CI MUST test its file structure, frontmatter, links, adapter hashes, and deterministic helper scripts. Model-behavior benchmarking is informative and MUST NOT be the only enforcement mechanism.

## 5. Repository instruction files

### 5.1 `AGENTS.md`

`AGENTS.md` is a short map, not a duplicate specification. It tells any coding/research agent:

- where the canonical rules live;
- what commands to run;
- which files are canonical or generated;
- which actions require explicit authorization;
- which claims must never be made from AI-only review.

It SHOULD remain under roughly 150 lines. Deep instructions belong in the specification, charter, or skills.

### 5.2 Tool adapters

- `CLAUDE.md` points Claude Code to `AGENTS.md`, the relevant skills, and project-specific commands.
- Codex consumes `AGENTS.md` and generated `.codex/skills/` adapters.
- Other agents receive the same short map or portable skills where supported.

Tool adapters MUST NOT redefine statuses, gates, or policy. CI compares policy-bearing statements against the canonical spec to detect drift.

## 6. Deterministic local hooks

Local hooks reduce feedback time. They are not trusted because developers and agents can bypass them.

Cruthúnas uses the `pre-commit` framework for cross-platform installation and invokes the same CLI used by CI.

### 6.1 Install

```bash
python -m pip install --requirement requirements/policy.txt
pre-commit install --hook-type pre-commit --hook-type commit-msg --hook-type pre-push
cruthunas adapters sync
cruthunas check --all
```

The dependency file MUST pin exact versions and hashes before CR-3.

### 6.2 `pre-commit`

Runs fast, staged-file checks:

- YAML/JSON syntax;
- claim-ledger schema validation;
- duplicate IDs and dangling dependencies;
- canonical-path and generated-file rules;
- forbidden binary/build artifacts;
- transition record required when status fields change;
- evidence links exist;
- no `UNCHECKED` mixed with other verification marks;
- no `EXTERNAL_REVIEW` without named human/venue evidence;
- no independent verifier importing project implementation code;
- no stale generated reports when their source changed;
- skill/adaptor drift;
- Markdown links and required frontmatter for changed governance files.

### 6.3 `commit-msg`

When a commit changes a claim, transition, correction, or release record, the message MUST use one of:

```text
claim(<ID>): <summary>
transition(<ID>): <FROM> -> <TO>
review(<ID>): <scope>
release(<version>): <summary>
correction(<ID>): <severity> <summary>
policy: <summary>
```

Ordinary documentation and implementation commits are not forced to contain a claim ID unless they alter claim evidence.

### 6.4 `pre-push`

Runs:

```bash
cruthunas check --all
cruthunas test --policy
```

It SHOULD avoid expensive mathematical reproduction by default. Full clean-room computation belongs in CI or an explicit local command.

## 7. Claude Code hooks

Claude Code hooks provide agent-specific early blocking. They complement portable skills but are not portable policy.

### 7.1 `PreToolUse`

Block or require confirmation for:

- `git add -A`, `git add .`, or equivalent bulk staging;
- force-push, destructive reset, branch deletion, and tag movement;
- direct edits to generated reports;
- direct status mutation outside `cruthunas claim transition`;
- release/tag/publish commands without an explicit release task;
- edits to protected publication artifacts;
- commands that make an independent verifier import project code;
- unpinned installer or container references in release workflows.

The hook inspects intended commands; the repository policy CLI validates resulting state.

### 7.2 `PostToolUse`

After edits to governed paths, run targeted checks:

```bash
cruthunas check --changed
```

Failures return a deterministic explanation and exact remediation command. Hooks MUST avoid rewriting mathematical content automatically.

### 7.3 `Stop`

Before Claude declares completion:

```bash
cruthunas check --changed
cruthunas status --porcelain
```

The hook blocks completion only for actionable repository violations. It MUST avoid infinite loops and MUST not demand optional gates unrelated to the current task.

### 7.4 Hook configuration source

Canonical hook logic lives in `hooks/` and `src/cruthunas/`. `.claude/settings.json` contains only event wiring and narrow matchers. CI tests hook scripts directly without requiring Claude Code.

## 8. Cruthúnas CLI

The CLI is the single deterministic policy entry point for humans, hooks, skills, and CI.

### 8.1 Commands

```text
cruthunas init
cruthunas check [--all|--changed|--profile <name>]
cruthunas status [--json|--porcelain]
cruthunas claim propose
cruthunas claim register <proposal>
cruthunas claim transition <ID> --epistemic ... --verification-add ... --publication ...
cruthunas gate check <0..10>
cruthunas evidence add <class>
cruthunas report claims
cruthunas report dependency-graph
cruthunas adapters sync
cruthunas adapters check
cruthunas reproduce <experiment-id>
cruthunas release verify <version>
cruthunas migrate <from> <to>
```

### 8.2 Safety properties

- Mutating commands produce a preview and require explicit confirmation unless `--yes` is supplied in a trusted automation context.
- The CLI never publishes, tags, or merges by default.
- Claim transition commands generate evidence/transition stubs and validate the complete transaction before writing.
- Failed transactions leave the repository unchanged.
- Machine-readable output is available for hooks and CI.

### 8.3 Exit codes

- `0` — compliant.
- `1` — policy violation.
- `2` — invalid invocation or configuration.
- `3` — missing dependency/toolchain.
- `4` — reproduction mismatch.
- `5` — internal validator failure.

## 9. Evidence and transition records

### 9.1 Evidence

```text
audit/evidence/<claim-id>/<evidence-id>.yaml
```

Minimum fields:

```yaml
schema_version: 1
id: E-T018-0001
claim_id: T018
class: COMPUTATION
created_at: 2026-07-30T19:00:00Z
created_by:
  type: human
  id: github:Kodaxadev
establishes:
  - "Claim holds for starts 1 through 259 inclusive"
does_not_establish:
  - "Universal stabilization"
artifacts:
  - path: certificates/t018/start-1-259.json
    sha256: <digest>
commands:
  - "python -m verifier --start 1 --stop 259"
environment:
  manifest: experiments/t018/environment.lock
source_revision: <full-sha>
```

### 9.2 Transitions

```text
audit/transitions/<claim-id>/<timestamp>-<transition>.yaml
```

Minimum fields:

```yaml
schema_version: 1
claim_id: T018
axis: epistemic
from: HEURISTIC
to: COMPUTATIONAL
requested_by: github:Kodaxadev
approved_by:
  type: policy
  id: cruthunas/promotion-computational-v1
evidence:
  - E-T018-0001
reason: "Exhaustive finite range certified"
created_at: 2026-07-30T19:00:00Z
```

Git history supplies the containing commit. A record MUST NOT attempt to include its own not-yet-existing commit SHA.

## 10. CI architecture

### 10.1 Required workflow: `policy.yml`

Triggers on every pull request and push to protected branches.

Jobs:

1. **policy-static** — pinned environment; schema, ledger, dependency graph, evidence links, transitions, adapters, docs, forbidden files, workflow pinning.
2. **policy-diff** — evaluates changes against the merge base; requires transition/correction/release records when protected fields change.
3. **policy-tests** — unit and mutation tests for validators and hooks.
4. **policy-report** — produces a human-readable compliance summary and machine-readable JSON artifact.

This is the minimum required check for all changes.

### 10.2 Conditional workflow: `reproduce.yml`

Runs when claims, experiments, certificates, independent implementations, or reproducibility manifests change; also supports manual dispatch.

Jobs are isolated by evidence package. Each job:

- checks out a frozen revision;
- creates the declared clean environment;
- runs exact recorded commands;
- compares output hashes and semantic summaries;
- verifies the independent implementation boundary;
- uploads logs and result manifests.

A successful run proves only that the declared computation reproduced in that environment.

### 10.3 Conditional workflow: `formal.yml`

Runs when `formal/`, formal evidence, or mapped claims change.

It pins the proof assistant and dependency lock, rejects placeholders/admitted gaps according to project policy, checks declaration mappings, and uploads build logs. It does not set `EXTERNAL_REVIEW`.

### 10.4 Conditional workflow: `manuscript.yml`

Runs when manuscript, claims, citations, attribution, evidence summaries, or build tooling change.

It:

- builds in the canonical environment;
- checks theorem-to-claim mappings;
- checks that numerical ranges and limitations match the ledger;
- scans for stale TODOs/placeholders and prohibited overstatement;
- verifies citations against recorded literature metadata;
- uploads PDF/source as workflow artifacts, not ordinary Git history;
- records hashes in a draft release manifest.

### 10.5 Release workflow: `release.yml`

Runs only by explicit manual dispatch or an immutable version tag created through the approved release command.

Required sequence:

1. verify Gate 8 and Gate 9 evidence;
2. run all policy, reproduction, formal, and manuscript workflows at the exact source SHA;
3. build source archive and release artifacts;
4. generate checksums and an evidence manifest;
5. generate GitHub artifact attestations where available;
6. create a draft release;
7. require explicit human publication approval;
8. archive with DOI provider when configured;
9. write archival identifiers back through a follow-up correction-safe commit or release metadata record.

No workflow may move an existing release tag.

### 10.6 Scheduled workflow: `drift.yml`

Runs weekly and reports, but does not silently mutate:

- broken external references;
- unpinned or superseded action/toolchain versions;
- adapter drift;
- expired exemptions;
- unreproduced evidence packages;
- framework-version drift in adopted projects.

Security updates open a pull request through a controlled dependency updater; they do not modify releases.

## 11. Reusable workflow distribution

The framework publishes reusable workflows under `.github/workflows/reusable-*.yml`. Governed projects call them using a pinned full commit SHA or immutable release tag.

Caller example:

```yaml
jobs:
  cruthunas:
    uses: Kodaxadev/cruthunas/.github/workflows/reusable-policy.yml@<full-sha>
    with:
      manifest: .cruthunas/project.yaml
```

Before CR-6, a full commit SHA is preferred. A release tag is acceptable only after tag protection and immutable release procedures are operational.

All third-party actions inside Cruthúnas workflows MUST be pinned to full commit SHAs. Dependabot or an equivalent controlled process may propose updates.

## 12. Pull-request contract

Every PR template asks:

- which gates or claims are affected;
- whether any status changes;
- evidence IDs added or invalidated;
- whether an originating context is approving its own work;
- commands run;
- artifacts generated;
- AI tools used;
- remaining limitations;
- whether release or correction rules apply.

Labels are descriptive only. They do not establish status.

## 13. Branch protection

For `main` and release branches:

- pull request required;
- required policy checks enabled;
- stale approvals dismissed when protected evidence changes;
- force pushes and branch deletion disabled;
- release tags protected;
- administrators do not routinely bypass required checks.

A solo maintainer may merge governance and implementation changes after CI, but MUST NOT self-assert `EXTERNAL_REVIEW` for a mathematical claim.

## 14. Generated content

Generated claim tables, dependency graphs, evidence summaries, and PDFs are derived artifacts.

- Human-edited canonical source is committed.
- Generated text MAY be committed only when required for a static publication surface and MUST carry a generated header plus drift check.
- PDFs and large outputs SHOULD be workflow/release artifacts rather than ordinary Git history.
- Release assets MUST have hashes and provenance records.

## 15. Implementation phases

### Phase A — consistency repair

- establish `CRUTHUNAS_SPEC.md` as canonical;
- remove stale Conjecture Warden terminology;
- reconcile gate/status definitions;
- correct the ledger schema root and status representation;
- replace self-referential commit fields with auditable transition records.

### Phase B — policy kernel

- implement manifest, ledger, evidence, transition, and exemption schemas;
- implement `cruthunas check`, `status`, and adapter commands;
- add unit, mutation, and fixture tests.

### Phase C — local workflow

- add portable skills and evaluations;
- add `AGENTS.md` and tool adapters;
- add pre-commit/commit-msg/pre-push hooks;
- add Claude Code hook wiring.

### Phase D — CI enforcement

- add policy and conditional workflows;
- require checks on protected branches;
- add reusable workflow callers and compliance reports.

### Phase E — first governed case

- adopt Cruthúnas in `cloitre-recurrence` without rewriting its history;
- create a gap report against existing evidence;
- backfill only verifiable records;
- process one claim transition end to end.

### Phase F — release

- run external framework review;
- publish v1.0.0 with immutable artifacts, checksums, attestations, migration guide, and correction channel.

## 16. Completion criterion

The execution layer is tied together when the same policy rule:

1. is stated once in the specification;
2. has a machine-readable schema or validator rule;
3. is invoked by local hooks;
4. is invoked independently by CI;
5. has positive and negative tests;
6. appears in the compliance report;
7. can be traced to evidence for a real governed claim.

Until then, Cruthúnas remains below CR-3 regardless of document completeness.
