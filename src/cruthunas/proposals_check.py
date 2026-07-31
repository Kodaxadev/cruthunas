from __future__ import annotations

from pathlib import Path
from typing import Any

from .models import Finding, load_and_validate, path_exists, yaml_files


def check_proposals(
    root: Path,
    claims: dict[str, dict[str, Any]],
) -> list[Finding]:
    findings: list[Finding] = []
    seen: set[str] = set()
    schema = root / "schemas/claim-proposal-v1.json"
    proposal_root = (root / "audit/proposals").resolve()

    for path in yaml_files(root, "audit/proposals"):
        proposal, current = load_and_validate(
            path,
            schema,
            root,
            missing_code="proposal.missing",
        )
        findings.extend(current)
        if not isinstance(proposal, dict) or not isinstance(proposal.get("id"), str):
            continue
        claim_id = proposal["id"]
        relative = str(path.relative_to(root))
        if claim_id in seen:
            findings.append(
                Finding(
                    "proposal.duplicate_id",
                    f"Duplicate proposal ID {claim_id}",
                    relative,
                )
            )
        seen.add(claim_id)
        if path.parent.resolve() != proposal_root or path.name != f"{claim_id}.yaml":
            findings.append(
                Finding(
                    "proposal.path_mismatch",
                    f"Proposal {claim_id} must live at audit/proposals/{claim_id}.yaml",
                    relative,
                )
            )
        source = proposal.get("source_document")
        if isinstance(source, str) and not path_exists(root, source):
            findings.append(
                Finding(
                    "proposal.missing_source",
                    f"Proposal {claim_id} source_document does not exist: {source}",
                    relative,
                )
            )
        for dependency in proposal.get("dependencies", []):
            if dependency not in claims:
                findings.append(
                    Finding(
                        "proposal.dangling_dependency",
                        f"Proposal {claim_id} depends on unknown registered claim {dependency}",
                        relative,
                    )
                )
    return findings
