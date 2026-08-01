# Project Governance

Cruthúnas is currently maintained by Kodaxadev and remains at **CR-0 — Exploration**. The maintainer controls merges, releases, conformance language, and normative specification changes until a broader governance model is adopted.

## Decision principles

Changes are judged by whether they improve auditability, preserve explicit evidence boundaries, prevent invalid state transitions, remain deterministic where enforcement is claimed, and can be tested against concrete failure modes.

## Normative authority

`CRUTHUNAS_SPEC.md` is the primary normative document. Schemas, policy code, CLI behavior, hooks, adapters, CI, and templates must remain consistent with it. When implementation and specification disagree, the conflict must be resolved explicitly; neither silently overrides the other.

## Conformance

No project may claim Cruthúnas conformance against an unreleased framework commit. Experimental adoption and gap reports must identify their framework commit and remain labeled non-conformant until a release defines the applicable contract.

## Status changes and releases

Framework maturity changes require evidence recorded in the repository. Releases must identify the specification version, policy implementation, migration impact, known limitations, and reproducible checks. Corrections are made through new commits or releases rather than rewriting a frozen record.
