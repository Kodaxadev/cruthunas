# Policy Kernel v0.1

This document describes the deterministic subset currently implemented on the execution-layer draft branch. It is subordinate to `CRUTHUNAS_SPEC.md` and `RESEARCH_CHARTER.md`.

## Commands

```text
cruthunas check --all [--json]
cruthunas check --changed [--json]
cruthunas status [--json|--porcelain]
cruthunas adapters sync
cruthunas adapters check
```

`--changed` currently runs the complete cross-file policy graph. Diff-aware enforcement will be added without weakening these whole-repository checks.

## Enforced invariants

- The claim ledger validates against its schema.
- Claim IDs are unique, dependencies exist, and the dependency graph is acyclic.
- Registered claims are at Gate 4 or later and point to existing source documents.
- Evidence and transition records validate against typed schemas.
- Evidence belongs to the claim directory and all referenced artifacts exist.
- Claim epistemic and verification states have matching evidence classes.
- Every claim has a Gate 3 → Gate 4 transition backed by `CLAIM_REGISTRATION` evidence.
- Transition chains are contiguous and end at the ledger's current state.
- Gate promotions cannot skip a gate.
- External-review evidence names a human reviewer or venue.
- Adoption manifests reject moving framework references and require a full commit SHA.
- GitHub Actions and container references are pinned.
- Generated manuscript/build binaries are rejected from Git history.
- Python clean-room verifiers under `independent/` cannot import packages under `src/`.
- Generated Claude and Codex skill adapters must match their canonical skill source.

## Authority boundary

The kernel establishes repository-policy compliance only. It does not establish mathematical truth, novelty, external review, publication acceptance, or universal validity outside the exact scope recorded by evidence.

## Exit codes

- `0` — compliant.
- `1` — policy violation.
- `2` — invalid invocation or no Cruthúnas project root.

Additional codes reserved by the architecture are not implemented yet.

## Local enforcement

`pre-commit` runs policy and adapter checks before commit and push. The commit-message hook requires structured messages when canonical claim, audit, correction, or manuscript paths change.

Claude Code uses:

- `PreToolUse` to deny bulk staging, destructive reset, force-push, and moving tags;
- `PostToolUse` to validate governed edits;
- `Stop` to prevent completion while deterministic violations remain.

Local hooks are advisory boundaries. Required GitHub Actions CI independently reruns policy tests, adapter checks, and repository validation.
