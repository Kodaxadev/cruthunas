from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from .models import read_yaml, yaml_files
from .transaction_evidence import (
    _build_evidence,
    _evidence_records,
    _link_evidence,
    _next_evidence_id,
    _unique_record_path,
)
from .transaction_plan import _plan
from .transaction_types import (
    EPISTEMIC_STATUSES,
    EVIDENCE_ID,
    PUBLICATION_STATUSES,
    VERIFICATION_STATUSES,
    TransactionError,
    TransactionPlan,
    _actor,
    _claim_map,
    _filename_timestamp,
    _latest_transition_timestamp,
    _ledger_bytes,
    _load_ledger,
    _parsed_timestamp,
    _source_revision,
    _timestamp,
    _yaml_bytes,
)

def _evidence_input_paths(root: Path, evidence_ids: list[str]) -> list[str]:
    wanted = set(evidence_ids)
    paths: dict[str, str] = {}
    for path in yaml_files(root, "audit/evidence"):
        try:
            record = read_yaml(path)
        except Exception:
            continue
        if isinstance(record, dict) and record.get("id") in wanted:
            paths[record["id"]] = str(path.relative_to(root)).replace("\\", "/")
    return [paths[evidence_id] for evidence_id in evidence_ids if evidence_id in paths]


def plan_evidence_add(
    root: Path,
    *,
    claim_id: str,
    evidence_class: str,
    created_by_type: str,
    created_by_id: str,
    establishes: list[str],
    does_not_establish: list[str],
    source_revision: str | None,
    evidence_id: str | None = None,
    artifacts: list[str] | None = None,
    commands: list[str] | None = None,
    environment_json: str | None = None,
    notes: str | None = None,
    reviewer_type: str | None = None,
    reviewer_id: str | None = None,
    timestamp: str | None = None,
) -> TransactionPlan:
    ledger = _load_ledger(root)
    claims = _claim_map(ledger)
    if claim_id not in claims:
        raise TransactionError(f"Unknown claim: {claim_id}")
    records = _evidence_records(root)
    selected_id = evidence_id or _next_evidence_id(root, claim_id)
    match = EVIDENCE_ID.fullmatch(selected_id)
    if not match or match.group(1) != claim_id:
        raise TransactionError(f"Evidence ID must belong to {claim_id}: {selected_id}", exit_code=2)
    if selected_id in records or (root / f"audit/evidence/{claim_id}/{selected_id}.yaml").exists():
        raise TransactionError(f"Evidence ID already exists: {selected_id}")
    created_at = _timestamp(timestamp)
    revision = _source_revision(root, source_revision)
    expected_git_head = revision if source_revision is None else None
    evidence = _build_evidence(
        root,
        claim_id=claim_id,
        evidence_id=selected_id,
        evidence_class=evidence_class,
        created_at=created_at,
        created_by_type=created_by_type,
        created_by_id=created_by_id,
        establishes=establishes,
        does_not_establish=does_not_establish,
        source_revision=revision,
        artifacts=artifacts or [],
        commands=commands or [],
        environment_json=environment_json,
        notes=notes,
        reviewer_type=reviewer_type,
        reviewer_id=reviewer_id,
    )
    claim = claims[claim_id]
    _link_evidence(claim, evidence)
    claim["updated_at"] = created_at
    path = f"audit/evidence/{claim_id}/{selected_id}.yaml"
    return _plan(
        root,
        "evidence.add",
        [
            ("claims/claims.yaml", _ledger_bytes(root, ledger)),
            (path, _yaml_bytes(evidence)),
        ],
        {"claim_id": claim_id, "evidence_ids": [selected_id], "evidence_paths": [path]},
        reads=[*(artifacts or []), *([environment_json] if environment_json else [])],
        expected_git_head=expected_git_head,
    )


def _verification_target(
    current: list[str],
    additions: list[str],
    removals: list[str],
) -> list[str]:
    active = {item for item in current if item != "UNCHECKED"}
    for item in additions:
        if item not in VERIFICATION_STATUSES:
            raise TransactionError(f"Unknown verification status: {item}", exit_code=2)
        active.add(item)
    for item in removals:
        if item not in VERIFICATION_STATUSES:
            raise TransactionError(f"Unknown verification status: {item}", exit_code=2)
        active.discard(item)
    return [item for item in VERIFICATION_STATUSES if item in active] or ["UNCHECKED"]


def plan_claim_transition(
    root: Path,
    *,
    claim_id: str,
    reason: str,
    requested_by: str,
    approved_by_type: str,
    approved_by_id: str,
    evidence_ids: list[str] | None = None,
    gate: int | None = None,
    epistemic: str | None = None,
    publication: str | None = None,
    verification_add: list[str] | None = None,
    verification_remove: list[str] | None = None,
    new_evidence_class: str | None = None,
    created_by_type: str | None = None,
    created_by_id: str | None = None,
    establishes: list[str] | None = None,
    does_not_establish: list[str] | None = None,
    source_revision: str | None = None,
    artifacts: list[str] | None = None,
    commands: list[str] | None = None,
    environment_json: str | None = None,
    notes: str | None = None,
    reviewer_type: str | None = None,
    reviewer_id: str | None = None,
    timestamp: str | None = None,
) -> TransactionPlan:
    ledger = _load_ledger(root)
    claims = _claim_map(ledger)
    if claim_id not in claims:
        raise TransactionError(f"Unknown claim: {claim_id}")
    if approved_by_type == "human" and approved_by_id == requested_by:
        raise TransactionError("A human requester cannot be the sole human approver of the same transition")
    claim = claims[claim_id]
    created_at = _timestamp(timestamp)
    evidence_records = _evidence_records(root)
    selected_evidence = list(dict.fromkeys(evidence_ids or []))
    for evidence_id in selected_evidence:
        record = evidence_records.get(evidence_id)
        if record is None:
            raise TransactionError(f"Transition evidence does not exist: {evidence_id}")
        if record.get("claim_id") != claim_id:
            raise TransactionError(f"Transition evidence belongs to another claim: {evidence_id}")
    new_evidence: dict[str, Any] | None = None
    new_evidence_path: str | None = None
    expected_git_head: str | None = None
    if new_evidence_class is not None:
        if created_by_type is None or created_by_id is None:
            raise TransactionError(
                "New transition evidence requires --created-by-type and --created-by-id",
                exit_code=2,
            )
        new_id = _next_evidence_id(root, claim_id)
        while new_id in selected_evidence:
            number = int(new_id.rsplit("-", 1)[1]) + 1
            new_id = f"E-{claim_id}-{number:04d}"
        revision = _source_revision(root, source_revision)
        expected_git_head = revision if source_revision is None else None
        new_evidence = _build_evidence(
            root,
            claim_id=claim_id,
            evidence_id=new_id,
            evidence_class=new_evidence_class,
            created_at=created_at,
            created_by_type=created_by_type,
            created_by_id=created_by_id,
            establishes=establishes or [],
            does_not_establish=does_not_establish or [],
            source_revision=revision,
            artifacts=artifacts or [],
            commands=commands or [],
            environment_json=environment_json,
            notes=notes,
            reviewer_type=reviewer_type,
            reviewer_id=reviewer_id,
        )
        selected_evidence.append(new_id)
        new_evidence_path = f"audit/evidence/{claim_id}/{new_id}.yaml"
        _link_evidence(claim, new_evidence)
    if not selected_evidence:
        raise TransactionError("A transition requires at least one evidence record", exit_code=2)
    for evidence_id in selected_evidence:
        record = new_evidence if new_evidence and new_evidence["id"] == evidence_id else evidence_records[evidence_id]
        _link_evidence(claim, record)

    changes: list[tuple[str, Any, Any]] = []
    if gate is not None:
        if gate < 4 or gate > 10:
            raise TransactionError("Registered claim gate must remain between 4 and 10", exit_code=2)
        before = claim["gate"]
        if gate > before + 1:
            raise TransactionError(f"Gate promotion cannot skip from {before} to {gate}")
        if gate != before:
            changes.append(("gate", before, gate))
            claim["gate"] = gate
    if epistemic is not None:
        if epistemic not in EPISTEMIC_STATUSES:
            raise TransactionError(f"Unknown epistemic status: {epistemic}", exit_code=2)
        before = claim["epistemic_status"]
        if epistemic != before:
            changes.append(("epistemic", before, epistemic))
            claim["epistemic_status"] = epistemic
    if publication is not None:
        if publication not in PUBLICATION_STATUSES:
            raise TransactionError(f"Unknown publication status: {publication}", exit_code=2)
        before = claim["publication_status"]
        if publication != before:
            changes.append(("publication", before, publication))
            claim["publication_status"] = publication
    additions = verification_add or []
    removals = verification_remove or []
    if additions or removals:
        before = list(claim["verification_statuses"])
        after = _verification_target(before, additions, removals)
        if after != before:
            changes.append(("verification", before, after))
            claim["verification_statuses"] = after
    if not changes:
        raise TransactionError("Transition does not change any claim axis", exit_code=2)
    for axis, _before, _after in changes:
        latest = _latest_transition_timestamp(root, claim_id, axis)
        if latest is not None and _parsed_timestamp(created_at) <= _parsed_timestamp(latest):
            raise TransactionError(
                f"Transition timestamp for {claim_id}/{axis} must be later than {latest}",
                exit_code=2,
            )
    claim["updated_at"] = created_at
    approver = _actor(approved_by_type, approved_by_id, approver=True)
    transition_paths: list[str] = []
    writes: list[tuple[str, bytes]] = [("claims/claims.yaml", _ledger_bytes(root, ledger))]
    if new_evidence is not None and new_evidence_path is not None:
        writes.append((new_evidence_path, _yaml_bytes(new_evidence)))
    stamp = _filename_timestamp(created_at)
    for axis, before, after in changes:
        transition = {
            "schema_version": 1,
            "claim_id": claim_id,
            "axis": axis,
            "from": before,
            "to": after,
            "requested_by": requested_by,
            "approved_by": approver,
            "evidence": selected_evidence,
            "reason": reason,
            "created_at": created_at,
        }
        suffix = f"{axis}-{str(before).lower()}-to-{str(after).lower()}"
        suffix = re.sub(r"[^a-z0-9-]+", "-", suffix).strip("-")
        path = _unique_record_path(
            root,
            f"audit/transitions/{claim_id}/{stamp}-{suffix}.yaml",
        )
        transition_paths.append(path)
        writes.append((path, _yaml_bytes(transition)))
    return _plan(
        root,
        "claim.transition",
        writes,
        {
            "claim_id": claim_id,
            "evidence_ids": selected_evidence,
            "transition_paths": transition_paths,
            "changes": [
                {"axis": axis, "from": before, "to": after}
                for axis, before, after in changes
            ],
        },
        reads=[
            *_evidence_input_paths(root, selected_evidence),
            *(artifacts or []),
            *([environment_json] if environment_json else []),
        ],
        expected_git_head=expected_git_head,
    )
