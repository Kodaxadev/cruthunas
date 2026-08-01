# Experimental initialization and adoption gaps

Cruthúnas remains **CR-0**. The commands in this document create and inspect project governance structure; they do not release the framework, claim conformance, raise maturity, or establish mathematical correctness.

## Initialize a project

`cruthunas init` uses the same preview, snapshot, confirmation, atomic replacement, post-write validation, and rollback boundary as the claim transaction commands.

```text
cruthunas init \
  --root PATH \
  --mode experimental \
  --framework-commit FULL_40_CHARACTER_SHA \
  --project-id project-id \
  --project-title "Project title" \
  --maintainer-github github-user \
  --dry-run --json
```

Initialization refuses to overwrite an existing governed destination. It creates only the project manifest, empty claim ledger, unfrozen charter template, and the schemas needed by the deterministic policy kernel. Empty audit directories are created later by transactions when records exist.

`--json` on a mutating command requires either `--dry-run` or `--yes`. Without `--yes`, the command previews the exact destinations and asks for confirmation.

## Project modes

### Experimental

An experimental project:

- pins an exact 40-character framework commit;
- may use a commit for which no framework release exists;
- records `conformance: non-conformant`;
- contains no framework version or release assertion;
- cannot claim Cruthúnas conformance merely because its local records pass policy validation.

This is the mode for disposable pilots and pre-release integration work.

### Released

A released project requires all of the following:

- an immutable framework version that is not a branch or moving reference;
- an exact framework commit;
- a local immutable framework-release attestation matching the repository, version, and commit;
- the SHA-256 of that attestation in `.cruthunas/project.yaml`.

`cruthunas init` does not discover or manufacture release evidence. A caller must supply the release attestation explicitly. The initialized project begins with `conformance: not-claimed`; a framework release and a valid project state are necessary but not by themselves sufficient to claim conformance.

## Historical claim aliases

Canonical claim IDs still match:

```text
^[A-Z][0-9]{3,}$
```

A claim or proposal may additionally contain normalized historical aliases. For example:

```yaml
id: K004
aliases:
  - K4
```

Aliases are provenance metadata. They are trimmed, uppercased, preserved through proposal and registration, and checked globally for collisions. An alias cannot:

- duplicate its canonical ID;
- equal any canonical ID;
- be assigned to more than one claim;
- become a later canonical ID.

Commands that require a claim reference—including dependencies, evidence creation, and transitions—continue to require the canonical ID. Cruthúnas does not silently resolve aliases in those positions. This avoids changing a command's meaning when historical identifiers are ambiguous.

## Adoption-gap reporting

```text
cruthunas adoption gaps --root PATH --json
```

The report is deterministic and read-only. It identifies:

- missing governed project structure;
- historical IDs that fail the canonical pattern, preserving dotted forms such as `C2.1` as exact manual findings rather than truncating them to a pad-compatible prefix;
- unpinned GitHub Actions, workflow containers, and Dockerfile base images;
- missing evidence-creator identities and reproduction or review independence metadata, including affirmative prose variants such as “independently regenerated”;
- canonical skills without an adapter manifest, or drift after adapters have been adopted;
- project-mode, framework-commit, version, release-attestation, and conformance incompatibilities;
- legacy or untyped records requiring a manual migration decision.

A gap marked `automatic` means the mechanical correction is deterministic. It does not authorize mutation. A `manual` gap requires a human decision or evidence that cannot be inferred from repository text.

Punctuated historical IDs remain manual while the alias contract cannot represent them losslessly. Independence-language detection evaluates each match in its containing sentence and clause. Agent or artifact nouns require an active completed action or result attributable to that noun; process nouns require completion or success of the process itself. Action phrases must use completed-action morphology outside modal, progressive, planned, interrogative, or uncertain scope, and modal scope is traced through a bounded local chain of modifiers and auxiliaries. The detector also excludes explicit negation, evidence absence, failed or unsuccessful attempts, abandoned, cancelled, or refused work, and ordinary mathematical uses such as “independently of `q`”; unrelated requirement wording and a neighboring question do not suppress a completed assertion. Structured evidence checks and unstructured prose checks run together during partial migration. A prose finding requests provenance review and does not establish independence itself.

## Actor roles

Actor fields describe distinct roles:

- `proposed_by` identifies the proposal originator;
- `created_by` identifies who created a record or evidence artifact;
- `requested_by` identifies who requested a transition or registration;
- `approved_by` identifies the policy, venue, or human approval authority;
- `reviewer` identifies the named human or venue responsible for review.

An agent may create `COMPUTATION` evidence. That is valid provenance for the computation and may support a bounded `COMPUTATIONAL` epistemic status. Agent creation does not establish an independent reproduction or an external review. `REPRODUCTION` and `REVIEW_EXTERNAL` require the applicable independent human or venue identities and structured independence boundaries.

## Explicit nonclaims

Initialization and adoption-gap reporting do not:

- synchronize adapters;
- pin a project's workflows;
- migrate records;
- execute computations;
- export or import transaction plans;
- release or tag Cruthúnas;
- establish CR-1 maturity;
- establish project conformance, truth, novelty, review, publication, or release.
