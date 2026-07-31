# Policy Kernel and Atomic Command Layer

This document describes the deterministic policy and mutation surface currently implemented in the framework repository. It is subordinate to `CRUTHUNAS_SPEC.md` and `RESEARCH_CHARTER.md`.

## Validation commands

```text
cruthunas check --all [--json]
cruthunas check --changed [--json]
cruthunas status [--json|--porcelain]
cruthunas adapters sync
cruthunas adapters check
```

`--changed` currently runs the complete cross-file policy graph. Diff-aware enforcement will be added without weakening these whole-repository checks.

## Atomic mutation commands

```text
cruthunas claim propose ...
cruthunas claim register <audit/proposals/ID.yaml> ...
cruthunas evidence add <CLASS> --claim <ID> ...
cruthunas claim transition <ID> ...
```

The command layer enforces these transaction boundaries:

- proposals are schema-validated and remain outside the claim ledger;
- registration creates the claim, `CLAIM_REGISTRATION` evidence, and the mandatory Gate 3 → 4 transition together;
- evidence creation writes the typed evidence record and links it from the claim in the same transaction;
- a transition may change one or more claim axes, creates one typed transition record per axis, and may create a new evidence record in the same transaction;
- the complete prospective repository is copied to an isolated validation tree and must pass the full policy graph before any canonical file is replaced;
- every changed target is checked for concurrent modification before commit;
- every proposal, evidence record, artifact, and environment file consumed by a plan is content-fingerprinted and rechecked before commit;
- an automatically detected `source_revision` requires a clean Git working tree, pins the current `HEAD`, and rechecks that `HEAD` before commit;
- an explicit `--source-revision` is treated as a caller attestation for external or non-Git source state;
- in-process write or post-write validation failures restore the original files, and incomplete rollback is reported as an internal failure rather than hidden;
- mutating commands preview by default and require confirmation unless `--yes` is explicitly supplied;
- `--dry-run` validates and previews without writing;
- machine-readable output is available with `--json` in `--dry-run` or `--yes` mode.

The filesystem transaction is validated-before-write and rollback-protected within the running process. Read-input fingerprints close the preview-to-apply race for files that determine generated records. The implementation does not claim crash consistency across operating-system failure or sudden power loss.

## Skill scope

The current framework ships one canonical umbrella skill, `cruthunas-govern`, with generated Claude and Codex adapters. It routes governed work across Gates 0–10 and directs canonical record changes through the atomic command layer.

The specialized skills described in the architecture remain a planned decomposition. They will be extracted only when their corresponding CLI workflows and evaluation fixtures exist. Empty skill stubs do not satisfy that design.

## Enforced invariants

- The claim ledger validates against its schema.
- Claim proposals validate against a typed schema and canonical path.
- Claim IDs are unique, dependencies exist, and the dependency graph is acyclic.
- Registered claims are at Gate 4 or later and point to existing source documents.
- Evidence and transition records validate against typed schemas.
- Evidence belongs to the claim directory and all referenced artifacts exist.
- Claim epistemic and verification states have matching evidence classes.
- Every claim has a Gate 3 → Gate 4 transition backed by `CLAIM_REGISTRATION` evidence.
- Transition chains are contiguous and end at the ledger's current state.
- Gate promotions cannot skip a gate.
- New transitions must be later than the existing history on the affected axis.
- External-review evidence names a human reviewer or venue.
- Adoption manifests reject moving framework references and require a full commit SHA.
- GitHub Actions and container references are pinned.
- Generated manuscript/build binaries are rejected from Git history.
- Python clean-room verifiers under `independent/` cannot import packages under `src/`.
- Generated Claude and Codex skill adapters must match their canonical skill source.

## Authority boundary

The kernel and command layer establish repository-policy consistency only. They do not establish mathematical truth, novelty, external review, publication acceptance, or universal validity outside the exact scope recorded by evidence.

## Exit codes

- `0` — compliant, applied, dry-run complete, or user-cancelled before mutation.
- `1` — policy or state violation.
- `2` — invalid invocation or no Cruthúnas project root.
- `3` — required toolchain or source revision unavailable.
- `5` — internal validator or post-write transaction failure.

## Local enforcement

`pre-commit` runs policy and adapter checks before commit and push. The commit-message hook requires structured messages when canonical claim, audit, correction, or manuscript paths change.

Claude Code uses:

- `PreToolUse` to deny bulk staging, destructive reset, force-push, and moving tags, and to require confirmation before freehand edits to command-managed records;
- `PostToolUse` to validate governed edits;
- `Stop` to prevent completion while deterministic violations remain.

Local hooks are advisory boundaries. Required GitHub Actions CI independently reruns policy tests, adapter checks, and repository validation.
