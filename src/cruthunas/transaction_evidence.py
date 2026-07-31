from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Iterable

from .models import read_yaml, yaml_files
from .transaction_types import (
    ACTOR_TYPES,
    EVIDENCE_CLASSES,
    EVIDENCE_ID,
    TransactionError,
    _actor,
    _relative_text,
    _resolve_relative,
    _validate_instance,
)

def _evidence_records(root: Path) -> dict[str, dict[str, Any]]:
    records: dict[str, dict[str, Any]] = {}
    for path in yaml_files(root, "audit/evidence"):
        try:
            record = read_yaml(path)
        except Exception:
            continue
        if isinstance(record, dict) and isinstance(record.get("id"), str):
            records[record["id"]] = record
    return records


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


def _unique_record_path(root: Path, relative: str) -> str:
    candidate = relative
    counter = 2
    path = Path(relative)
    while (root / candidate).exists():
        candidate = str(path.with_name(f"{path.stem}-{counter}{path.suffix}")).replace("\\", "/")
        counter += 1
    return candidate


def _artifact_records(root: Path, artifacts: Iterable[str]) -> list[dict[str, str]]:
    records: list[dict[str, str]] = []
    for value in artifacts:
        relative = _relative_text(root, value)
        path = root / relative
        if not path.is_file():
            raise TransactionError(f"Evidence artifact does not exist: {relative}")
        records.append({"path": relative, "sha256": hashlib.sha256(path.read_bytes()).hexdigest()})
    return records


def _environment(root: Path, environment_json: str | None) -> dict[str, Any] | None:
    if environment_json is None:
        return None
    path = _resolve_relative(root, environment_json)
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise TransactionError(f"Could not read environment JSON: {exc}") from exc
    if not isinstance(value, dict):
        raise TransactionError("Environment JSON must contain an object")
    return value


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
    notes: str | None,
    reviewer_type: str | None,
    reviewer_id: str | None,
) -> dict[str, Any]:
    if evidence_class not in EVIDENCE_CLASSES:
        raise TransactionError(f"Unknown evidence class: {evidence_class}", exit_code=2)
    if not establishes or not all(item.strip() for item in establishes):
        raise TransactionError("Evidence requires at least one non-empty establishes statement", exit_code=2)
    if not does_not_establish or not all(item.strip() for item in does_not_establish):
        raise TransactionError("Evidence requires at least one non-empty does-not-establish statement", exit_code=2)
    record: dict[str, Any] = {
        "schema_version": 1,
        "id": evidence_id,
        "claim_id": claim_id,
        "class": evidence_class,
        "created_at": created_at,
        "created_by": _actor(created_by_type, created_by_id),
        "establishes": [item.strip() for item in establishes],
        "does_not_establish": [item.strip() for item in does_not_establish],
        "artifacts": _artifact_records(root, artifacts),
        "commands": [item.strip() for item in commands],
        "environment": _environment(root, environment_json),
        "source_revision": source_revision,
        "notes": notes,
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
    _validate_instance(record, root / "schemas/evidence-v1.json", "evidence record")
    return record


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
        if not any(item.get("record") == evidence_id for item in reviews if isinstance(item, dict)):
            reviews.append(record)
