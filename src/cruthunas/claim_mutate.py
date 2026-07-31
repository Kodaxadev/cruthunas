from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from .evidence_policy import normalized_identity
from .transaction_evidence import (
    _build_evidence,
    _evidence_records_with_snapshots,
    _link_evidence,
    _next_evidence_id,
    _unique_record_snapshot,
)
from .transaction_plan import _plan
from .transaction_types import (
    EPISTEMIC_STATUSES,
    EVIDENCE_ID,
    PUBLICATION_STATUSES,
    VERIFICATION_STATUSES,
    FileSnapshot,
    TransactionError,
    TransactionPlan,
    _actor,
    _capture_file,
    _claim_map,
    _filename_timestamp,
    _identity,
    _identity_key,
    _ledger_bytes,
    _load_ledger_snapshot,
    _nonempty_text,
    _parsed_timestamp,
    _require_later,
    _source_revision,
    _timestamp,
    _transition_history,
    _yaml_bytes,
)


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
    details_json: str | None = None,
    notes: str | None = None,
    reviewer_type: str | None = None,
    reviewer_id: str | None = None,
    timestamp: str | None = None,
) -> TransactionPlan:
    ledger, ledger_snapshot = _load_ledger_snapshot(root)
    claims = _claim_map(ledger)
    if claim_id not in claims:
        raise TransactionError(f"Unknown claim: {claim_id}")
    records, _record_snapshots = _evidence_records_with_snapshots(root)
    selected_id = evidence_id or _next_evidence_id(root, claim_id)
    match = EVIDENCE_ID.fullmatch(selected_id)
    if not match or match.group(1) != claim_id:
        raise TransactionError(
            f"Evidence ID must belong to {claim_id}: {selected_id}",
            exit_code=2,
        )
    path = f"audit/evidence/{claim_id}/{selected_id}.yaml"
    evidence_target = _capture_file(root, path)
    if selected_id in records or evidence_target.content is not None:
        raise TransactionError(f"Evidence ID already exists: {selected_id}")
    claim = claims[claim_id]
    created_at = _timestamp(timestamp)
    _require_later(created_at, claim.get("updated_at"), f"Evidence {selected_id}")
    revision = _source_revision(root, source_revision)
    expected_git_head = revision if source_revision is None else None
    evidence, evidence_inputs = _build_evidence(
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
        details_json=details_json,
        notes=notes,
        reviewer_type=reviewer_type,
        reviewer_id=reviewer_id,
    )
    _link_evidence(claim, evidence)
    claim["updated_at"] = created_at
    return _plan(
        root,
        "evidence.add",
        [
            ("claims/claims.yaml", _ledger_bytes(root, ledger, ledger_snapshot)),
            (path, _yaml_bytes(evidence)),
        ],
        {"claim_id": claim_id, "evidence_ids": [selected_id], "evidence_paths": [path]},
        read_snapshots=list(evidence_inputs),
        write_snapshots={
            "claims/claims.yaml": ledger_snapshot,
            path: evidence_target,
        },
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
    details_json: str | None = None,
    notes: str | None = None,
    reviewer_type: str | None = None,
    reviewer_id: str | None = None,
    timestamp: str | None = None,
) -> TransactionPlan:
    ledger, ledger_snapshot = _load_ledger_snapshot(root)
    claims = _claim_map(ledger)
    if claim_id not in claims:
        raise TransactionError(f"Unknown claim: {claim_id}")
    requester = _identity(requested_by, "Transition requester")
    reason_text = _nonempty_text(reason, "Transition reason")
    approver = _actor(approved_by_type, approved_by_id, approver=True)
    if approved_by_type == "human" and _identity_key(approver["id"]) == _identity_key(requester):
        raise TransactionError(
            "A human requester cannot be the sole human approver of the same transition"
        )
    claim = claims[claim_id]
    created_at = _timestamp(timestamp)
    _require_later(created_at, claim.get("updated_at"), f"Transition for {claim_id}")
    evidence_records, evidence_snapshots = _evidence_records_with_snapshots(root)
    selected_evidence = list(dict.fromkeys(evidence_ids or []))
    selected_evidence_snapshots: list[FileSnapshot] = []
    selected_records: list[dict[str, Any]] = []
    for evidence_id in selected_evidence:
        record = evidence_records.get(evidence_id)
        if record is None:
            raise TransactionError(f"Transition evidence does not exist: {evidence_id}")
        if record.get("claim_id") != claim_id:
            raise TransactionError(
                f"Transition evidence belongs to another claim: {evidence_id}"
            )
        selected_records.append(record)
        selected_evidence_snapshots.append(evidence_snapshots[evidence_id])

    new_evidence: dict[str, Any] | None = None
    new_evidence_path: str | None = None
    new_evidence_target: FileSnapshot | None = None
    new_evidence_inputs: tuple[FileSnapshot, ...] = ()
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
        new_evidence, new_evidence_inputs = _build_evidence(
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
            details_json=details_json,
            notes=notes,
            reviewer_type=reviewer_type,
            reviewer_id=reviewer_id,
        )
        selected_evidence.append(new_id)
        selected_records.append(new_evidence)
        new_evidence_path = f"audit/evidence/{claim_id}/{new_id}.yaml"
        new_evidence_target = _capture_file(root, new_evidence_path)
        if new_evidence_target.content is not None:
            raise TransactionError(f"Evidence ID already exists: {new_id}")
        _link_evidence(claim, new_evidence)
    if not selected_evidence:
        raise TransactionError("A transition requires at least one evidence record", exit_code=2)
    for evidence_id in selected_evidence:
        record = (
            new_evidence
            if new_evidence and new_evidence["id"] == evidence_id
            else evidence_records[evidence_id]
        )
        _link_evidence(claim, record)

    if approved_by_type == "human":
        approver_key = _identity_key(approver["id"])
        contributor_keys = {
            normalized_identity(record.get("created_by", {}).get("id"))
            for record in selected_records
            if isinstance(record.get("created_by"), dict)
            and record.get("created_by", {}).get("type") == "human"
        }
        if approver_key in contributor_keys:
            raise TransactionError(
                "A human evidence creator cannot be the sole human approver of a transition relying on that evidence"
            )

    changes: list[tuple[str, Any, Any]] = []
    if gate is not None:
        if gate < 4 or gate > 10:
            raise TransactionError(
                "Registered claim gate must remain between 4 and 10",
                exit_code=2,
            )
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
            raise TransactionError(
                f"Unknown publication status: {publication}",
                exit_code=2,
            )
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

    transition_history_snapshots: list[FileSnapshot] = []
    for axis, _before, _after in changes:
        latest, history_snapshots = _transition_history(root, claim_id, axis)
        transition_history_snapshots.extend(history_snapshots)
        if latest is not None and _parsed_timestamp(created_at) <= _parsed_timestamp(latest):
            raise TransactionError(
                f"Transition timestamp for {claim_id}/{axis} must be later than {latest}",
                exit_code=2,
            )
    claim["updated_at"] = created_at
    transition_paths: list[str] = []
    writes: list[tuple[str, bytes]] = [
        ("claims/claims.yaml", _ledger_bytes(root, ledger, ledger_snapshot))
    ]
    write_snapshots: dict[str, FileSnapshot] = {
        "claims/claims.yaml": ledger_snapshot,
    }
    if (
        new_evidence is not None
        and new_evidence_path is not None
        and new_evidence_target is not None
    ):
        writes.append((new_evidence_path, _yaml_bytes(new_evidence)))
        write_snapshots[new_evidence_path] = new_evidence_target
    stamp = _filename_timestamp(created_at)
    for axis, before, after in changes:
        transition = {
            "schema_version": 1,
            "claim_id": claim_id,
            "axis": axis,
            "from": before,
            "to": after,
            "requested_by": requester,
            "approved_by": approver,
            "evidence": selected_evidence,
            "reason": reason_text,
            "created_at": created_at,
        }
        suffix = f"{axis}-{str(before).lower()}-to-{str(after).lower()}"
        suffix = re.sub(r"[^a-z0-9-]+", "-", suffix).strip("-")
        target = _unique_record_snapshot(
            root,
            f"audit/transitions/{claim_id}/{stamp}-{suffix}.yaml",
        )
        transition_paths.append(target.path)
        writes.append((target.path, _yaml_bytes(transition)))
        write_snapshots[target.path] = target
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
        read_snapshots=[
            *selected_evidence_snapshots,
            *new_evidence_inputs,
            *transition_history_snapshots,
        ],
        write_snapshots=write_snapshots,
        expected_git_head=expected_git_head,
    )
