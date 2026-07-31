from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .evidence_policy import claim_originator_identities, evidence_contract_errors
from .models import Finding, load_and_validate, path_exists, yaml_files
from .transition_check import check_transition_semantics

EVIDENCE_FOR = {
    "INTERNAL_AUDIT": {"REVIEW_INTERNAL"},
    "INDEPENDENT_REPRODUCTION": {"REPRODUCTION"},
    "FORMALIZED": {"FORMALIZATION"},
    "EXTERNAL_REVIEW": {"REVIEW_EXTERNAL"},
}


def _timestamp(value: Any) -> datetime | None:
    if not isinstance(value, str):
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return None
    return parsed.astimezone(timezone.utc)


def _local_artifact(root: Path, value: str) -> Path | None:
    if value.startswith(("https://", "http://", "doi:")):
        return None
    candidate = (root / value).resolve()
    try:
        candidate.relative_to(root.resolve())
    except ValueError:
        return None
    return candidate


def _evidence(
    root: Path,
    claims: dict[str, dict[str, Any]],
) -> tuple[dict[str, dict[str, Any]], list[Finding]]:
    findings: list[Finding] = []
    records: dict[str, dict[str, Any]] = {}
    record_paths: dict[str, str] = {}
    schema = root / "schemas/evidence-v1.json"
    for path in yaml_files(root, "audit/evidence"):
        record, current = load_and_validate(
            path,
            schema,
            root,
            missing_code="evidence.missing",
        )
        findings.extend(current)
        if not isinstance(record, dict) or not isinstance(record.get("id"), str):
            continue
        evidence_id = record["id"]
        relative = str(path.relative_to(root))
        if evidence_id in records:
            findings.append(
                Finding(
                    "evidence.duplicate_id",
                    f"Duplicate evidence ID {evidence_id}",
                    relative,
                )
            )
        records[evidence_id] = record
        record_paths[evidence_id] = relative
        claim_id = record.get("claim_id")
        if claim_id not in claims:
            findings.append(
                Finding(
                    "evidence.unknown_claim",
                    f"Evidence {evidence_id} refers to unknown claim {claim_id}",
                    relative,
                )
            )
        if path.parent.resolve() != (root / "audit/evidence" / str(claim_id)).resolve():
            findings.append(
                Finding(
                    "evidence.path_mismatch",
                    f"Evidence for {claim_id} must live under audit/evidence/{claim_id}/",
                    relative,
                )
            )
        for artifact in record.get("artifacts", []):
            artifact_path = artifact.get("path") if isinstance(artifact, dict) else None
            if not isinstance(artifact_path, str):
                continue
            if not path_exists(root, artifact_path):
                findings.append(
                    Finding(
                        "evidence.missing_artifact",
                        f"Evidence {evidence_id} artifact does not exist: {artifact_path}",
                        relative,
                    )
                )
                continue
            local = _local_artifact(root, artifact_path)
            if local is None:
                continue
            if not local.is_file():
                findings.append(
                    Finding(
                        "evidence.missing_artifact",
                        f"Evidence {evidence_id} artifact is not a file: {artifact_path}",
                        relative,
                    )
                )
                continue
            expected = artifact.get("sha256") if isinstance(artifact, dict) else None
            actual = hashlib.sha256(local.read_bytes()).hexdigest()
            if isinstance(expected, str) and actual != expected:
                findings.append(
                    Finding(
                        "evidence.artifact_hash_mismatch",
                        f"Evidence {evidence_id} artifact hash does not match: {artifact_path}",
                        relative,
                    )
                )

    for evidence_id, record in records.items():
        claim_id = record.get("claim_id")
        originators = (
            claim_originator_identities(root, claim_id, records)
            if isinstance(claim_id, str)
            else frozenset()
        )
        for message in evidence_contract_errors(record, originator_ids=originators):
            findings.append(
                Finding(
                    "evidence.contract_incomplete",
                    message,
                    record_paths[evidence_id],
                )
            )
    return records, findings


def _transitions(
    root: Path,
    claims: dict[str, dict[str, Any]],
    evidence: dict[str, dict[str, Any]],
) -> tuple[list[dict[str, Any]], list[Finding]]:
    findings: list[Finding] = []
    records: list[dict[str, Any]] = []
    schema = root / "schemas/transition-v1.json"
    for path in yaml_files(root, "audit/transitions"):
        record, current = load_and_validate(
            path,
            schema,
            root,
            missing_code="transition.missing",
        )
        findings.extend(current)
        if not isinstance(record, dict):
            continue
        records.append(record)
        relative = str(path.relative_to(root))
        if record.get("claim_id") not in claims:
            findings.append(
                Finding(
                    "transition.unknown_claim",
                    f"Transition refers to unknown claim {record.get('claim_id')}",
                    relative,
                )
            )
        for evidence_id in record.get("evidence", []):
            if evidence_id not in evidence:
                findings.append(
                    Finding(
                        "transition.missing_evidence",
                        f"Transition references missing evidence {evidence_id}",
                        relative,
                    )
                )
    return records, findings


def _claim_support(
    claims: dict[str, dict[str, Any]],
    evidence: dict[str, dict[str, Any]],
) -> list[Finding]:
    findings: list[Finding] = []
    for claim_id, claim in claims.items():
        linked = claim.get("evidence", [])
        for evidence_id in linked:
            if evidence_id not in evidence:
                findings.append(
                    Finding(
                        "claim.missing_evidence",
                        f"Claim {claim_id} references missing evidence {evidence_id}",
                        "claims/claims.yaml",
                    )
                )
        classes = {evidence[item].get("class") for item in linked if item in evidence}
        for verification in claim.get("verification_statuses", []):
            required = EVIDENCE_FOR.get(verification)
            if required and classes.isdisjoint(required):
                findings.append(
                    Finding(
                        "claim.unsupported_verification",
                        f"Claim {claim_id} has {verification} without matching evidence",
                        "claims/claims.yaml",
                    )
                )
        if claim.get("epistemic_status") == "COMPUTATIONAL" and classes.isdisjoint(
            {"COMPUTATION", "REPRODUCTION"}
        ):
            findings.append(
                Finding(
                    "claim.unsupported_computational_status",
                    f"Claim {claim_id} is COMPUTATIONAL without computation evidence",
                    "claims/claims.yaml",
                )
            )
        if claim.get("epistemic_status") == "PROVED" and classes.isdisjoint(
            {"PROOF", "FORMALIZATION"}
        ):
            findings.append(
                Finding(
                    "claim.unsupported_proof_status",
                    f"Claim {claim_id} is PROVED without proof evidence",
                    "claims/claims.yaml",
                )
            )
        if claim.get("epistemic_status") == "REFUTED" and "REFUTATION" not in classes:
            findings.append(
                Finding(
                    "claim.unsupported_refutation",
                    f"Claim {claim_id} is REFUTED without refutation evidence",
                    "claims/claims.yaml",
                )
            )
    return findings


def _claim_chronology(
    root: Path,
    claims: dict[str, dict[str, Any]],
    evidence: dict[str, dict[str, Any]],
    transitions: list[dict[str, Any]],
) -> list[Finding]:
    findings: list[Finding] = []
    transitions_by_claim: dict[str, list[dict[str, Any]]] = {}
    for record in transitions:
        claim_id = record.get("claim_id")
        if isinstance(claim_id, str):
            transitions_by_claim.setdefault(claim_id, []).append(record)

    for claim_id, claim in claims.items():
        introduced = _timestamp(claim.get("introduced_at"))
        updated = _timestamp(claim.get("updated_at"))
        if introduced is not None and updated is not None and updated < introduced:
            findings.append(
                Finding(
                    "claim.chronology_reversed",
                    f"Claim {claim_id} updated_at precedes introduced_at",
                    "claims/claims.yaml",
                )
            )
        if updated is None:
            continue
        for evidence_id in claim.get("evidence", []):
            record = evidence.get(evidence_id)
            event = _timestamp(record.get("created_at")) if isinstance(record, dict) else None
            if introduced is not None and event is not None and event < introduced:
                findings.append(
                    Finding(
                        "evidence.before_claim_introduction",
                        f"Evidence {evidence_id} predates claim {claim_id} introduction",
                        f"audit/evidence/{claim_id}/{evidence_id}.yaml",
                    )
                )
            if event is not None and event > updated:
                findings.append(
                    Finding(
                        "claim.updated_at_before_evidence",
                        f"Claim {claim_id} updated_at precedes linked evidence {evidence_id}",
                        "claims/claims.yaml",
                    )
                )
        for transition in transitions_by_claim.get(claim_id, []):
            event = _timestamp(transition.get("created_at"))
            if introduced is not None and event is not None and event < introduced:
                findings.append(
                    Finding(
                        "transition.before_claim_introduction",
                        f"Transition for {claim_id} predates claim introduction",
                        "claims/claims.yaml",
                    )
                )
            if event is not None and event > updated:
                findings.append(
                    Finding(
                        "claim.updated_at_before_transition",
                        f"Claim {claim_id} updated_at precedes a transition record",
                        "claims/claims.yaml",
                    )
                )
    return findings


def check_records(
    root: Path,
    claims: dict[str, dict[str, Any]],
) -> tuple[dict[str, dict[str, Any]], list[dict[str, Any]], list[Finding]]:
    evidence, findings = _evidence(root, claims)
    transitions, transition_findings = _transitions(root, claims, evidence)
    findings.extend(transition_findings)
    findings.extend(check_transition_semantics(root, claims, evidence))
    findings.extend(_claim_support(claims, evidence))
    findings.extend(_claim_chronology(root, claims, evidence, transitions))
    schema = root / "schemas/exemption-v1.json"
    for path in yaml_files(root, "audit/exemptions"):
        _, current = load_and_validate(
            path,
            schema,
            root,
            missing_code="exemption.missing",
        )
        findings.extend(current)
    return evidence, transitions, findings
