from __future__ import annotations

from pathlib import Path
from typing import Any, Iterable, Mapping

from .models import read_yaml

ORIGINATING_EVIDENCE_CLASSES = frozenset({"CLAIM_REGISTRATION", "DERIVATION", "PROOF", "COMPUTATION", "FORMALIZATION"})
INDEPENDENCE_KEYS = ("independent", "relationship_to_originator", "inputs_received", "saw_original_work", "implementation_boundary", "dependency_boundary", "result", "disagreements")
CLASS_DETAIL_KEYS: dict[str, tuple[str, ...]] = {
    "COMPUTATION": ("algorithm", "bounds", "arithmetic", "inputs", "input_hashes", "outputs", "output_hashes", "runtime", "resources"),
    "REPRODUCTION": INDEPENDENCE_KEYS,
    "FORMALIZATION": ("proof_assistant", "toolchain", "statement_mapping", "dependencies", "axioms", "placeholders", "out_of_assistant_computations", "build_result"),
    "REVIEW_EXTERNAL": INDEPENDENCE_KEYS,
    "RELEASE": ("tag", "build", "evidence_manifest", "archive", "immutable_assets", "review_status"),
}
COMPUTATIONAL_ENVIRONMENT_KEYS = ("interpreter", "dependencies", "operating_system", "locale", "timezone", "environment_variables", "random_seeds")
CLASSES_REQUIRING_COMMANDS = frozenset({"COMPUTATION", "REPRODUCTION", "FORMALIZATION", "RELEASE"})
CLASSES_REQUIRING_ARTIFACTS = frozenset({"COMPUTATION", "REPRODUCTION", "FORMALIZATION", "RELEASE"})
CLASSES_REQUIRING_ENVIRONMENT = frozenset({"COMPUTATION", "REPRODUCTION", "FORMALIZATION", "RELEASE"})


def normalized_identity(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    normalized = value.strip()
    return normalized.casefold() if normalized else None


def _actor(record: Mapping[str, Any], field: str) -> Mapping[str, Any] | None:
    actor = record.get(field)
    return actor if isinstance(actor, Mapping) else None


def _actor_identity(record: Mapping[str, Any], field: str) -> str | None:
    actor = _actor(record, field)
    return normalized_identity(actor.get("id")) if actor is not None else None


def _has_value(value: Any) -> bool:
    if isinstance(value, str):
        return bool(value.strip())
    if isinstance(value, (list, tuple, set, dict)):
        return bool(value)
    return value is not None


def evidence_contract_errors(record: Mapping[str, Any], *, originator_ids: Iterable[str] = ()) -> list[str]:
    evidence_class = record.get("class")
    if not isinstance(evidence_class, str):
        return []
    errors: list[str] = []
    commands = record.get("commands")
    artifacts = record.get("artifacts")
    environment = record.get("environment")
    details = record.get("details")
    if evidence_class in CLASSES_REQUIRING_COMMANDS and (not isinstance(commands, list) or not commands or not all(isinstance(item, str) and item.strip() for item in commands)):
        errors.append(f"{evidence_class} evidence requires at least one exact command")
    if evidence_class in CLASSES_REQUIRING_ARTIFACTS and (not isinstance(artifacts, list) or not artifacts):
        errors.append(f"{evidence_class} evidence requires at least one hashed artifact")
    if evidence_class in CLASSES_REQUIRING_ENVIRONMENT:
        if not isinstance(environment, Mapping) or not environment:
            errors.append(f"{evidence_class} evidence requires a non-empty environment record")
        elif evidence_class in {"COMPUTATION", "REPRODUCTION"}:
            for key in COMPUTATIONAL_ENVIRONMENT_KEYS:
                if key not in environment or not _has_value(environment.get(key)):
                    errors.append(f"{evidence_class} environment requires non-empty {key}")
    required_keys = CLASS_DETAIL_KEYS.get(evidence_class, ())
    if required_keys:
        if not isinstance(details, Mapping):
            errors.append(f"{evidence_class} evidence requires structured class-specific details")
        else:
            for key in required_keys:
                if key not in details or not _has_value(details.get(key)):
                    errors.append(f"{evidence_class} evidence details require non-empty {key}")
    creator_record = _actor(record, "created_by")
    creator_type = creator_record.get("type") if creator_record is not None else None
    creator = _actor_identity(record, "created_by")
    originators = {key for value in originator_ids if (key := normalized_identity(value)) is not None}
    if evidence_class in {"REPRODUCTION", "REVIEW_EXTERNAL"}:
        if creator_type == "agent":
            authority = "independent reproduction" if evidence_class == "REPRODUCTION" else "external review"
            errors.append(f"Agent-created {evidence_class} evidence is provenance only and cannot establish {authority}")
        if not isinstance(details, Mapping) or details.get("independent") is not True:
            errors.append(f"{evidence_class} evidence must explicitly record independent=true")
        if isinstance(details, Mapping) and not isinstance(details.get("saw_original_work"), bool):
            errors.append(f"{evidence_class} evidence details require boolean saw_original_work")
    if evidence_class == "REPRODUCTION" and creator is not None and creator in originators:
        errors.append("REPRODUCTION evidence creator must be independent of the claim originator")
    if evidence_class == "REVIEW_EXTERNAL":
        reviewer = record.get("reviewer")
        reviewer_type = reviewer.get("type") if isinstance(reviewer, Mapping) else None
        reviewer_identity = _actor_identity(record, "reviewer")
        if reviewer_type not in {"human", "venue"} or reviewer_identity is None:
            errors.append("REVIEW_EXTERNAL evidence requires a named human reviewer or documented venue")
        elif reviewer_type == "human":
            if creator is not None and reviewer_identity == creator:
                errors.append("REVIEW_EXTERNAL reviewer must differ from the evidence creator")
            if reviewer_identity in originators:
                errors.append("REVIEW_EXTERNAL reviewer must be independent of the claim originator")
    return errors


def claim_originator_identities(root: Path, claim_id: str, records: Mapping[str, Mapping[str, Any]]) -> frozenset[str]:
    identities: set[str] = set()
    proposal_path = root / "audit" / "proposals" / f"{claim_id}.yaml"
    if proposal_path.is_file():
        try:
            proposal = read_yaml(proposal_path)
        except Exception:
            proposal = None
        if isinstance(proposal, Mapping):
            identity = normalized_identity(proposal.get("proposed_by"))
            if identity is not None:
                identities.add(identity)
    for record in records.values():
        if record.get("claim_id") == claim_id and record.get("class") in ORIGINATING_EVIDENCE_CLASSES:
            identity = _actor_identity(record, "created_by")
            if identity is not None:
                identities.add(identity)
    return frozenset(identities)
