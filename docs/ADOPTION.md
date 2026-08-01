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

Punctuated historical IDs remain manual while the alias contract cannot represent them losslessly. Independence-language detection is a conservative supported grammar, not a general English semantic parser. It creates offset-bearing action candidates, evaluates each in its local sentence and contrastive clause, and accepts only a bounded set of completed predicates. Actor nouns require an action performed by that actor; artifact nouns require a check or result attributed to that artifact; process nouns require completion, success, or a direct result predicate of the process itself. Modified direct subjects are supported, while embedded references such as plans, requirements, concepts, and proposals are excluded. Supported actor roles include verifiers, reviewers, auditors, validators, and referees.

The action grammar requires `independently` to attach directly through whitespace or an en/em dash to the supported completed action, or directly after that action. Commas, colons, semicolons, parentheses, and unrelated predicates do not bridge attachment. Bounded `and`, `or`, comma, and `neither`/`nor` coordination can inherit a shared negation, modal, evidential, or hedge scope; a final postposed attribution or hedge governs its contiguous coordinated proposition in both directions. A contrast or explicit new subject resets ordinary shared scope. Active, passive, preposed, parenthetical, postposed, zero-complement, and `as reported by` attribution frames are non-affirmative. Modal chains, progressive or planned work, questions, uncertainty, evidence absence, negation, failed attempts, abandoned, cancelled, refused, and hedged statements are likewise excluded. Unrelated requirement or hedge wording and a neighboring question do not suppress a completed assertion.

For Markdown inputs, the scan supports deterministic block boundaries rather than full CommonMark parsing. Backtick and tilde fences track their marker type and opening length through matching, longer, or unclosed fences; fenced bodies and unambiguous four-space indented code are excluded. Inline code spans are masked, and HTML-comment state is retained across blank lines through a closing marker or end of file. Visible emphasis and inline-link labels remain prose. Blank lines, headings, list items, block quotes, and table rows terminate attribution, while a single newline inside one prose block remains a supported hard wrap. Other text formats retain plain-text scanning. Structured evidence and unstructured prose checks run together during partial migration. A prose finding requests provenance review and is never evidence that independence occurred; absence of a finding does not establish that prose or structured evidence is complete.

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
