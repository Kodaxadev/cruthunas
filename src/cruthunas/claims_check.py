from __future__ import annotations

from pathlib import Path
from typing import Any

from .models import Finding, load_and_validate, path_exists


def _cycle(claims: dict[str, dict[str, Any]]) -> list[str] | None:
    state: dict[str, int] = {}
    stack: list[str] = []

    def visit(claim_id: str) -> list[str] | None:
        marker = state.get(claim_id, 0)
        if marker == 1:
            start = stack.index(claim_id)
            return stack[start:] + [claim_id]
        if marker == 2:
            return None
        state[claim_id] = 1
        stack.append(claim_id)
        for dependency in claims[claim_id].get("dependencies", []):
            if dependency in claims:
                found = visit(dependency)
                if found:
                    return found
        stack.pop()
        state[claim_id] = 2
        return None

    for claim_id in claims:
        found = visit(claim_id)
        if found:
            return found
    return None


def check_claims(
    root: Path,
) -> tuple[dict[str, dict[str, Any]], list[Finding]]:
    ledger, findings = load_and_validate(
        root / "claims/claims.yaml",
        root / "claims/schema.json",
        root,
        missing_code="ledger.missing",
    )
    claims: dict[str, dict[str, Any]] = {}
    if not isinstance(ledger, dict) or not isinstance(ledger.get("claims"), list):
        return claims, findings

    known_ids = {
        item.get("id")
        for item in ledger["claims"]
        if isinstance(item, dict) and isinstance(item.get("id"), str)
    }
    for claim in ledger["claims"]:
        if not isinstance(claim, dict) or not isinstance(claim.get("id"), str):
            continue
        claim_id = claim["id"]
        if claim_id in claims:
            findings.append(
                Finding(
                    "claim.duplicate_id",
                    f"Duplicate claim ID {claim_id}",
                    "claims/claims.yaml",
                )
            )
        else:
            claims[claim_id] = claim
        if claim.get("gate", 0) < 4:
            findings.append(
                Finding(
                    "claim.invalid_gate",
                    f"Registered claim {claim_id} must be at Gate 4 or later",
                    "claims/claims.yaml",
                )
            )
        if claim_id in claim.get("dependencies", []):
            findings.append(
                Finding(
                    "claim.self_dependency",
                    f"Claim {claim_id} depends on itself",
                    "claims/claims.yaml",
                )
            )
        for dependency in claim.get("dependencies", []):
            if dependency not in known_ids:
                findings.append(
                    Finding(
                        "claim.dangling_dependency",
                        f"Claim {claim_id} depends on unknown claim {dependency}",
                        "claims/claims.yaml",
                    )
                )
        source = claim.get("source_document")
        if isinstance(source, str) and not path_exists(root, source):
            findings.append(
                Finding(
                    "claim.missing_source",
                    f"Claim {claim_id} source_document does not exist: {source}",
                    "claims/claims.yaml",
                )
            )

    found_cycle = _cycle(claims)
    if found_cycle:
        findings.append(
            Finding(
                "claim.dependency_cycle",
                "Dependency cycle: " + " -> ".join(found_cycle),
                "claims/claims.yaml",
            )
        )
    return claims, findings
