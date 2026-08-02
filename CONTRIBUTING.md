# Contributing to Cruthúnas

Cruthúnas is a research-governance and verification framework. Contributions are welcome across policy design, schemas, CLI behavior, adapters, documentation, tests, release engineering, and governed-project adoption.

## Start here

Read `README.md`, `CRUTHUNAS_SPEC.md`, `RESEARCH_CHARTER.md`, `docs/POLICY_KERNEL.md`, and `docs/ADOPTION.md` before changing normative behavior.

## Contribution types

- policy or lifecycle clarification;
- schema or validator changes;
- CLI and atomic-mutation improvements;
- hook, CI, or adapter work;
- adoption reports from real projects;
- documentation and reproducibility fixes;
- regression tests for a discovered governance failure.

## Normative changes

A change that alters claim states, verification marks, publication states, lifecycle gates, required evidence, transition rules, or conformance must identify:

- the governing invariant;
- the failure mode being prevented;
- affected schemas, commands, docs, tests, and adapters;
- migration or compatibility impact;
- an example that should pass and one that should fail.

## Development

```bash
python -m pip install --requirement requirements/policy.txt --editable .
python -m pytest
cruthunas adapters check
cruthunas check --all
```

Use `--dry-run --json` when testing mutating commands. Do not use `--yes` in examples unless the task explicitly authorizes mutation.

## Pull requests

Keep changes focused and include tests. Passing CI establishes policy consistency only; it does not establish mathematical truth, external review, or project conformance.
