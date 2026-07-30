# Corrections Log

This framework assumes errors will eventually be found after release. Corrections are recorded publicly here, never silently applied to published artifacts.

## Policy

- No silent rewriting of published artifacts. A correction is a new, versioned entry, not an edit to history.
- Every correction records: severity, affected claim IDs, whether downstream dependencies remain valid, corrected release reference, and new DOI version where applicable (see Zenodo versioning model).
- Central failures (a claim central to the paper's thesis is refuted) trigger the withdrawal procedure below rather than a routine correction entry.

## Severity classes

- **COSMETIC** — typos, formatting, non-substantive wording.
- **MINOR** — a lemma statement is imprecise but the result and proof survive with clarification.
- **MODERATE** — a proof gap is found and closed; conclusion unchanged but the original argument was incomplete.
- **MAJOR** — a claim's status must be downgraded (e.g. PROVED → HEURISTIC) pending new work.
- **CRITICAL** — a central claim is refuted; withdrawal procedure applies.

## Correction entry template

```
date: 
severity: 
affected_claim_ids: []
description: 
dependency_impact: 
corrected_release: 
new_doi_version: 
reported_by: 
```

## Withdrawal procedure (CRITICAL severity)

1. Freeze further releases on the affected branch.
2. Publish a withdrawal notice referencing the specific claim ID(s) and dependency chain.
3. Mark the affected claim(s) `REFUTED` in `claims/claims.yaml`; do not delete the record.
4. Determine which downstream claims lose support and mark them accordingly.
5. Issue a corrected release or a formal withdrawal, consistent with the venue's own policy if published.

## Log

| Date | Severity | Claim IDs | Description | Status |
|---|---|---|---|---|
| — | — | — | — | — |
