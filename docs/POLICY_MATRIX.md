# Cruthúnas Policy Matrix

This matrix connects each lifecycle gate to its canonical evidence, agent workflow, local checks, CI authority, and permitted status effect. It is explanatory; `CRUTHUNAS_SPEC.md` remains normative.

| Gate | Canonical evidence | Primary skill | Local hook focus | Required CI | Permitted effect |
|---|---|---|---|---|---|
| 0 Candidate intake | candidate dossier, attribution lead, GO/PARK/REJECT record | `candidate-intake` | required dossier fields; no premature claim ID | `policy-static` | none; candidate only |
| 1 Research charter | frozen charter and amendment policy | `charter-freeze` | charter headings, version, unresolved placeholders | `policy-static`, `policy-diff` | project may begin baseline work |
| 2 Baseline reproduction | fixtures, independent implementation, comparison report | `baseline-reproduction` | independent import boundary; commands and hashes | `reproduce` | verification may add `INDEPENDENT_REPRODUCTION` for the reproduced baseline only |
| 3 Exploration | dated logs, failed approaches, observations | none required | keep exploration outside ledger; no status language in generated notes | `policy-static` | none |
| 4 Claim registration | exact ledger entry, dependencies, limitations, source links | `claim-register` | schema, unique ID, exact statement, dependency closure | `policy-static`, `policy-diff` | new claim begins `OPEN`, `UNCHECKED`, `WORKING` |
| 5 Adversarial proof review | prover/falsifier/dependency/statement review records | `proof-falsification` | originating-context separation; unresolved gap detection | `policy-static`, `policy-tests` | may add `INTERNAL_AUDIT`; cannot add `EXTERNAL_REVIEW` from AI-only work |
| 6 Computational evidence | experiment manifest, exact commands/ranges, outputs, hashes, independent verifier | `computation-package` | exact bounds; arithmetic/overflow; output links | `reproduce`, `policy-diff` | may set `COMPUTATIONAL` only for the exact bounded statement |
| 7 Formal verification | declaration map, toolchain lock, axioms/placeholders report | `formalization-audit` | declaration exists; no forbidden placeholders; statement relation recorded | `formal` | may add `FORMALIZED`; does not imply external review or publication |
| 8 Manuscript audit | theorem map, citation/attribution audit, build record, disclosure | `manuscript-audit` | no stale claims/ranges/TODOs; ledger alignment | `manuscript`, `policy-diff` | may set publication `FROZEN`; no truth-status promotion by publication |
| 9 Release | release manifest, source/artifact hashes, attestations, archival ID | `release-audit` | tag/version consistency; explicit authorization | full workflow set plus `release` | may set `PREPRINT`, `SUBMITTED`, or `PUBLISHED` according to actual event |
| 10 Correction | correction/withdrawal record and dependency-impact report | `correction-assessment` | correction precedes status change; no deleted history | `policy-diff`, affected reproduction/formal/manuscript jobs | may demote/refute claims and set `CORRECTED` or `WITHDRAWN` |

## Promotion rules

| Requested change | Minimum evidence | Additional rule |
|---|---|---|
| `OPEN → HEURISTIC` | derivation or exploratory evidence | limitations explicit |
| `OPEN/HEURISTIC → COMPUTATIONAL` | Gate 6 computation package | claim statement itself must be bounded to computed scope |
| `OPEN/HEURISTIC/COMPUTATIONAL → PROVED` | complete derivation mapped to exact statement plus Gate 5 internal audit | originator cannot be sole approving reviewer; external review is reported separately, not inferred |
| any non-refuted state → `REFUTED` | counterexample or disproof evidence | downstream dependency impact required |
| add `INDEPENDENT_REPRODUCTION` | clean independent implementation and comparison record | verifier must not import project implementation code |
| add `FORMALIZED` | successful pinned proof-assistant build and declaration map | placeholders and additional axioms disclosed |
| add `EXTERNAL_REVIEW` | named independent human or documented venue process | AI-only review prohibited |
| `WORKING → FROZEN` | Gate 8 audit complete | source revision fixed |
| `FROZEN → PREPRINT/SUBMITTED/PUBLISHED` | Gate 9 release package | value must match actual dissemination event |
| published state → `CORRECTED` | public correction record | affected claims and versions identified |
| any publication state → `WITHDRAWN` | withdrawal record | published history remains available where venue permits |

## Enforcement ownership

| Layer | Can advise | Can block locally | Can block merge | Can confer mathematical review |
|---|---:|---:|---:|---:|
| Agent skill | yes | no | no | no |
| Claude/Codex tool hook | yes | yes | no | no |
| Git/pre-commit hook | yes | yes | no | no |
| CI policy check | no | n/a | yes | no |
| Formal proof assistant | no | n/a | yes for configured formal checks | formal verification only |
| Named independent human/venue | yes | n/a | by repository policy | yes, for `EXTERNAL_REVIEW` |
| Maintainer release approval | no | n/a | yes | no |
