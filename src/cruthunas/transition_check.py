from __future__ import annotations

from collections import defaultdict
from pathlib import Path
from typing import Any

from .models import Finding, read_yaml, yaml_files
from .transition_policy import transition_support_errors

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


def _human_approver(record: dict[str, Any]) -> str | None:
    approved = record.get("approved_by")
    if isinstance(approved, dict) and approved.get("type") == "human":
        value = approved.get("id")
        return value if isinstance(value, str) else None
    return None


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
        relative = str(path.relative_to(root))
        grouped[(claim_id, axis)].append((path, record))
        claim = claims.get(claim_id)
        if claim is None:
            continue

        approver = _human_approver(record)
        if approver is not None and approver == record.get("requested_by"):
            findings.append(
                Finding(
                    "transition.self_approval",
                    f"Human requester {approver} cannot be the sole human approver",
                    relative,
                )
            )

        linked_evidence = set(claim.get("evidence", []))
        selected_ids = record.get("evidence", [])
        selected_records: list[dict[str, Any]] = []
        all_present = isinstance(selected_ids, list)
        for evidence_id in selected_ids if isinstance(selected_ids, list) else []:
            evidence_record = evidence.get(evidence_id)
            if evidence_record is None:
                all_present = False
            else:
                selected_records.append(evidence_record)
                if evidence_record.get("claim_id") != claim_id:
                    findings.append(
                        Finding(
                            "transition.foreign_evidence",
                            f"Transition for {claim_id} uses evidence owned by {evidence_record.get('claim_id')}: {evidence_id}",
                            relative,
                        )
                    )
            if evidence_id not in linked_evidence:
                findings.append(
                    Finding(
                        "transition.unlinked_evidence",
                        f"Transition evidence {evidence_id} is not linked from claim {claim_id}",
                        relative,
                    )
                )
        if all_present and selected_records:
            before = _normalized(axis, record.get("from"))
            after = _normalized(axis, record.get("to"))
            for message in transition_support_errors(axis, before, after, selected_records):
                findings.append(
                    Finding(
                        "transition.unsupported_evidence",
                        message,
                        relative,
                    )
                )

    for (claim_id, axis), items in grouped.items():
        items.sort(key=lambda item: str(item[1].get("created_at", "")))
        previous_to: Any = None
        for index, (path, record) in enumerate(items):
            relative = str(path.relative_to(root))
            before = _normalized(axis, record.get("from"))
            after = _normalized(axis, record.get("to"))
            if before == after:
                findings.append(
                    Finding(
                        "transition.noop",
                        f"Transition does not change the {axis} axis",
                        relative,
                    )
                )
            if index and before != previous_to:
                findings.append(
                    Finding(
                        "transition.broken_chain",
                        f"Transition chain for {claim_id}/{axis} expects from={previous_to!r}, found {before!r}",
                        relative,
                    )
                )
            if (
                axis == "gate"
                and isinstance(before, int)
                and isinstance(after, int)
                and after > before + 1
            ):
                findings.append(
                    Finding(
                        "transition.gate_skip",
                        f"Gate transition skips from {before} to {after}",
                        relative,
                    )
                )
            previous_to = after

        claim = claims.get(claim_id)
        if claim is None:
            continue
        expected = _normalized(axis, claim.get(AXIS_FIELD[axis]))
        if previous_to != expected:
            findings.append(
                Finding(
                    "transition.ledger_mismatch",
                    f"Last {axis} transition ends at {previous_to!r}, but ledger records {expected!r}",
                    str(items[-1][0].relative_to(root)),
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
            relative = str(first_path.relative_to(root))
            if first.get("from") != 3 or first.get("to") != 4:
                findings.append(
                    Finding(
                        "transition.registration_invalid",
                        f"First gate transition for {claim_id} must be 3 -> 4",
                        relative,
                    )
                )
            registration_ids = first.get("evidence", [])
            registration_records = [
                evidence[item]
                for item in registration_ids
                if item in evidence and evidence[item].get("class") == "CLAIM_REGISTRATION"
            ]
            if not registration_records:
                findings.append(
                    Finding(
                        "transition.registration_evidence_missing",
                        f"Gate 3 -> 4 transition for {claim_id} requires CLAIM_REGISTRATION evidence",
                        relative,
                    )
                )

            approver = _human_approver(first)
            if approver is not None:
                originators = {
                    record.get("created_by", {}).get("id")
                    for record in registration_records
                    if isinstance(record.get("created_by"), dict)
                }
                proposal_path = root / "audit/proposals" / f"{claim_id}.yaml"
                if proposal_path.is_file():
                    try:
                        proposal = read_yaml(proposal_path)
                    except Exception:
                        proposal = None
                    if isinstance(proposal, dict):
                        originators.add(proposal.get("proposed_by"))
                if approver in originators:
                    findings.append(
                        Finding(
                            "transition.registration_self_approval",
                            f"Human claim originator or requester {approver} cannot be the sole human registration approver",
                            relative,
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
