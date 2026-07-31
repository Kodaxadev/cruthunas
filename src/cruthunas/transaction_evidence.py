from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Iterable

from .evidence_policy import evidence_contract_errors
from .models import yaml_files
from .transaction_types import (
    EVIDENCE_CLASSES,
    EVIDENCE_ID,
    FileSnapshot,
    TransactionError,
    _actor,
    _capture_file,
    _relative_text,
    _validate_instance,
    _yaml_from_snapshot,
)


def _evidence_records_with_snapshots(
    root: Path,
) -> tuple[dict[str, dict[str, Any]], dict[str, FileSnapshot]]:
    records: dict[str, dict[str, Any]] = {}
    snapshots: dict[str, FileSnapshot] = {}
    for path in yaml_files(root, "audit/evidence"):
        try:
            snapshot = _capture_file(root, path, required=True)
            record = _yaml_from_snapshot(snapshot)
        except TransactionError:
            continue
        if isinstance(record, dict) and isinstance(record.get("id"), str):
            records[record["id"]] = record
            snapshots[record["id"]] = snapshot
    return records, snapshots


def _evidence_records(root: Path) -> dict[str, dict[str, Any]]:
    return _evidence_records_with_snapshots(root)[0]


def _next_evidence_id(root: Path, claim_id: str) -> str:
    maximum = 0
    candidates = set(_evidence_records(root))
    evidence_root = root / "audit/evidence" / claim_id
    if evidence_root.is_dir():
        candidates.update(path.stem for path in evidence_root.glob("*.yaml"))
        candidates.update(path.stem for path in evidence_root.glob("*.yml"))
    for evidence_id in candidates:
        match = EVIDENCE_ID.fullmatch(evidence_id)
        if match and match.group(1) == claim_id:
            maximum = max(maximum, int(match.group(2)))
    return f"E-{claim_id}-{maximum + 1:04d}"


def _unique_record_snapshot(root: Path, relative: str) -> FileSnapshot:
    candidate = relative
    counter = 2
    path = Path(relative)
    while True:
        snapshot = _capture_file(root, candidate)
        if snapshot.content is None:
            return snapshot
        candidate = str(path.with_name(f"{path.stem}-{counter}{path.suffix}")).replace("\\", "/")
        counter += 1


def _unique_record_path(root: Path, relative: str) -> str:
    return _unique_record_snapshot(root, relative).path


def _artifact_records(
    root: Path,
    artifacts: Iterable[str],
) -> tuple[list[dict[str, str]], list[FileSnapshot]]:
    records: list[dict[str, str]] = []
    snapshots: list[FileSnapshot] = []
    for value in artifacts:
        relative = _relative_text(root, value)
        snapshot = _capture_file(root, relative, required=True)
        assert snapshot.sha256 is not None
        records.append({"path": relative, "sha256": snapshot.sha256})
        snapshots.append(snapshot)
    return records, snapshots


def _json_object(
    root: Path,
    json_path: str | None,
    label: str,
) -> tuple[dict[str, Any] | None, list[FileSnapshot]]:
    if json_path is None:
        return None, []
    snapshot = _capture_file(root, json_path, required=True)
    assert snapshot.content is not None
    try:
        value = json.loads(snapshot.content.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise TransactionError(f"Could not read {label} JSON: {exc}") from exc
    if not isinstance(value, dict):
        raise TransactionError(f"{label} JSON must contain an object")
    return value, [snapshot]


def _build_evidence(
    root: Path,
    *,
    claim_id: str,
    evidence_id: str,
    evidence_class: str,
    created_at: str,
    created_by_type: str,
    created_by_id: str,
    establishes: list[str],
    does_not_establish: list[str],
    source_revision: str,
    artifacts: list[str],
    commands: list[str],
    environment_json: str | None,
    details_json: str | None,
    notes: str | None,
    reviewer_type: str | None,
    reviewer_id: str | None,
) -> tuple[dict[str, Any], tuple[FileSnapshot, ...]]:
    if evidence_class not in EVIDENCE_CLASSES:
        raise TransactionError(f"Unknown evidence class: {evidence_class}", exit_code=2)
    if not establishes or not all(isinstance(item, str) and item.strip() for item in establishes):
        raise TransactionError(
            "Evidence requires at least one non-empty establishes statement",
            exit_code=2,
        )
    if not does_not_establish or not all(
        isinstance(item, str) and item.strip() for item in does_not_establish
    ):
        raise TransactionError(
            "Evidence requires at least one non-empty does-not-establish statement",
            exit_code=2,
        )
    if any(not isinstance(item, str) or not item.strip() for item in commands):
        raise TransactionError("Evidence commands must not be empty", exit_code=2)
    artifact_records, artifact_snapshots = _artifact_records(root, artifacts)
    environment, environment_snapshots = _json_object(root, environment_json, "Environment")
    details, details_snapshots = _json_object(root, details_json, "Details")
    record: dict[str, Any] = {
        "schema_version": 1,
        "id": evidence_id,
        "claim_id": claim_id,
        "class": evidence_class,
        "created_at": created_at,
        "created_by": _actor(created_by_type, created_by_id),
        "establishes": [item.strip() for item in establishes],
        "does_not_establish": [item.strip() for item in does_not_establish],
        "artifacts": artifact_records,
        "commands": [item.strip() for item in commands],
        "environment": environment,
        "details": details,
        "source_revision": source_revision,
        "notes": notes.strip() if isinstance(notes, str) and notes.strip() else None,
    }
    if evidence_class == "REVIEW_EXTERNAL":
        if reviewer_type not in {"human", "venue"} or not reviewer_id:
            raise TransactionError(
                "REVIEW_EXTERNAL evidence requires --reviewer-type human|venue and --reviewer-id",
                exit_code=2,
            )
        record["reviewer"] = _actor(reviewer_type, reviewer_id)
    elif reviewer_type is not None or reviewer_id is not None:
        if reviewer_type is None or reviewer_id is None:
            raise TransactionError("Reviewer type and ID must be supplied together", exit_code=2)
        record["reviewer"] = _actor(reviewer_type, reviewer_id)
    contract_errors = evidence_contract_errors(record)
    if contract_errors:
        raise TransactionError("; ".join(contract_errors), exit_code=2)
    _validate_instance(record, root / "schemas/evidence-v1.json", "evidence record")
    return record, tuple(
        [*artifact_snapshots, *environment_snapshots, *details_snapshots]
    )


def _link_evidence(claim: dict[str, Any], evidence: dict[str, Any]) -> None:
    evidence_id = evidence["id"]
    linked = claim.setdefault("evidence", [])
    if evidence_id not in linked:
        linked.append(evidence_id)
    if evidence["class"] in {"COMPUTATION", "REPRODUCTION"}:
        support = claim.setdefault("computational_support", [])
        if evidence_id not in support:
            support.append(evidence_id)
    if evidence["class"] == "REVIEW_EXTERNAL":
        reviewer = evidence.get("reviewer", {})
        reviews = claim.setdefault("external_reviews", [])
        record = {
            "reviewer": reviewer.get("id", "unknown"),
            "record": evidence_id,
            "venue": reviewer.get("id") if reviewer.get("type") == "venue" else None,
        }
        if not any(
            item.get("record") == evidence_id
            for item in reviews
            if isinstance(item, dict)
        ):
            reviews.append(record)
