# Claude Code adapter

Read and follow `AGENTS.md` before acting. Treat `CRUTHUNAS_SPEC.md` as the canonical policy source and `RESEARCH_CHARTER.md` as the canonical Gate 0–10 procedure.

Use the portable skill under `skills/cruthunas-govern/` when a task changes a mathematical claim, evidence, review record, reproducibility package, manuscript, release, or correction.

Claude-specific hooks are an early-warning layer only. They do not replace the repository policy CLI or required CI.

Do not:

- mutate the repository without explicit authorization;
- use bulk staging;
- self-approve a claim produced in the same context;
- label AI review external review;
- change claim statuses freehand;
- tag, publish, submit, archive, or release without explicit authorization.

Before stopping, inspect the diff, run available policy checks, and report checks not run and unresolved uncertainty.
