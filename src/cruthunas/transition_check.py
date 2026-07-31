from __future__ import annotations

from collections import defaultdict
from pathlib import Path
from typing import Any

from .models import Finding, read_yaml, yaml_files


AXIS_FIELD = {
    "gate": "gate",
    "epistemic": "epistemic_status",
    "verification": "verification_statuses",
    "publication": "publication_status",
}
DEFAULT_STATE: dict[str, Any] = {
    "epistemic": "OPEN",
    "verification": ["UNCHECKED"],
    "publication": "WORKING",
}


def _normalized(axis: str, value: Any) -> Any:
    if axis == "verification" and isinstance(value, list):
        return sorted(value)
    return value


def check_transition_semantics(
    root: Path,
    claims: dict[str, dict[str, Any]],
    evidence: dict[str, dict[str, Any]],
) -> list[Finding]:
    findings: list[Finding] = []
    grouped: dict[tuple[str, str], list[tuple[Path, dict[str, Any]]]] = defaultdict(list)

    for path in yaml_files(root, "audit/transitions"):
        try:
            record = read_yaml(path)
        except Exception:
            continue
        if not isinstance(record, dict):
            continue
        claim_id = record.get("claim_id")
        axis = record.get("axis")
        if not isinstance(claim_id, str) or axis not in AXIS_FIELD:
            continue
        grouped[(claim_id, axis)].append((path, record))
        claim = claims.get(claim_id)
        if claim is None:
            continue
        linked_evidence = set(claim.get("evidence", []))
        for evidence_id in record.get("evidence", []):
            evidence_record = evidence.get(evidence_id)
            if evidence_record and evidence_record.get("claim_id") != claim_id:
                findings.append(
                    Finding(
                        "transition.foreign_evidence",
                        f"Transition for {claim_id} uses evidence owned by {evidence_record.get('claim_id')}: {evidence_id}",
                        str(path.relative_to(root)),
                    )
                )
            if evidence_id not in linked_evidence:
                findings.append(
                    Finding(
                        "transition.unlinked_evidence",
                        f"Transition evidence {evidence_id} is not linked from claim {claim_id}",
                        str(path.relative_to(root)),
                    )
                )

    for (claim_id, axis), items in grouped.items():
        items.sort(key=lambda item: str(item[1].get("created_at", "")))
        previous_to: Any = None
        for index, (path, record) in enumerate(items):
            before = _normalized(axis, record.get("from"))
            after = _normalized(axis, record.get("to"))
            if before == after:
                findings.append(
                    Finding(
                        "transition.noop",
                        f"Transition does not change the {axis} axis",
                        str(path.relative_to(root)),
                    )
                )
            if index and before != previous_to:
                findings.append(
                    Finding(
                        "transition.broken_chain",
                        f"Transition chain for {claim_id}/{axis} expects from={previous_to!r}, found {before!r}",
                        str(path.relative_to(root)),
                    )
                )
            if axis == "gate" and isinstance(before, int) and isinstance(after, int):
                if after > before + 1:
                    findings.append(
                        Finding(
                            "transition.gate_skip",
                            f"Gate transition skips from {before} to {after}",
                            str(path.relative_to(root)),
                        )
                    )
            previous_to = after

        claim = claims.get(claim_id)
        if claim is None:
            continue
        expected = _normalized(axis, claim.get(AXIS_FIELD[axis]))
        if previous_to != expected:
            last_path = items[-1][0]
            findings.append(
                Finding(
                    "transition.ledger_mismatch",
                    f"Last {axis} transition ends at {previous_to!r}, but ledger records {expected!r}",
                    str(last_path.relative_to(root)),
                )
            )

    for claim_id, claim in claims.items():
        gate_items = grouped.get((claim_id, "gate"), [])
        if not gate_items:
            findings.append(
                Finding(
                    "transition.registration_missing",
                    f"Claim {claim_id} has no Gate 3 -> Gate 4 registration transition",
                    "claims/claims.yaml",
                )
            )
        else:
            gate_items.sort(key=lambda item: str(item[1].get("created_at", "")))
            first_path, first = gate_items[0]
            if first.get("from") != 3 or first.get("to") != 4:
                findings.append(
                    Finding(
                        "transition.registration_invalid",
                        f"First gate transition for {claim_id} must be 3 -> 4",
                        str(first_path.relative_to(root)),
                    )
                )
            registration_classes = {
                evidence[item].get("class")
                for item in first.get("evidence", [])
                if item in evidence
            }
            if "CLAIM_REGISTRATION" not in registration_classes:
                findings.append(
                    Finding(
                        "transition.registration_evidence_missing",
                        f"Gate 3 -> 4 transition for {claim_id} requires CLAIM_REGISTRATION evidence",
                        str(first_path.relative_to(root)),
                    )
                )

        for axis, default in DEFAULT_STATE.items():
            current = _normalized(axis, claim.get(AXIS_FIELD[axis]))
            if current != _normalized(axis, default) and (claim_id, axis) not in grouped:
                findings.append(
                    Finding(
                        "transition.status_history_missing",
                        f"Claim {claim_id} has non-default {axis} state without a transition record",
                        "claims/claims.yaml",
                    )
                )

    return findings
