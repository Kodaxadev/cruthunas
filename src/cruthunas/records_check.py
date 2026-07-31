from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any

from .models import Finding, load_and_validate, path_exists, yaml_files
from .transition_check import check_transition_semantics

EVIDENCE_FOR = {
    "INTERNAL_AUDIT": {"REVIEW_INTERNAL"},
    "INDEPENDENT_REPRODUCTION": {"REPRODUCTION"},
    "FORMALIZED": {"FORMALIZATION"},
    "EXTERNAL_REVIEW": {"REVIEW_EXTERNAL"},
}


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
        if record.get("class") == "REVIEW_EXTERNAL":
            reviewer = record.get("reviewer")
            if not isinstance(reviewer, dict) or reviewer.get("type") not in {
                "human",
                "venue",
            }:
                findings.append(
                    Finding(
                        "review.external_identity_required",
                        f"External-review evidence {evidence_id} requires a human or venue reviewer",
                        relative,
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


def check_records(
    root: Path,
    claims: dict[str, dict[str, Any]],
) -> tuple[dict[str, dict[str, Any]], list[dict[str, Any]], list[Finding]]:
    evidence, findings = _evidence(root, claims)
    transitions, transition_findings = _transitions(root, claims, evidence)
    findings.extend(transition_findings)
    findings.extend(check_transition_semantics(root, claims, evidence))
    findings.extend(_claim_support(claims, evidence))
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
