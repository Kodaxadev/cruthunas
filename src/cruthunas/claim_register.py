from __future__ import annotations

from pathlib import Path
from typing import Any

from .models import read_yaml
from .transaction_evidence import _build_evidence, _next_evidence_id, _unique_record_path
from .transaction_plan import _plan
from .transaction_types import (
    CLAIM_ID,
    CLAIM_KINDS,
    TransactionError,
    TransactionPlan,
    _actor,
    _claim_map,
    _filename_timestamp,
    _ledger_bytes,
    _load_ledger,
    _relative_text,
    _source_revision,
    _timestamp,
    _validate_instance,
    _yaml_bytes,
)

def plan_claim_proposal(
    root: Path,
    *,
    claim_id: str,
    kind: str,
    statement: str,
    source_document: str,
    limitations: list[str],
    proposed_by: str,
    title: str | None = None,
    scope: str | None = None,
    dependencies: list[str] | None = None,
    proof_location: str | None = None,
    formal_declarations: list[str] | None = None,
    timestamp: str | None = None,
) -> TransactionPlan:
    if not CLAIM_ID.fullmatch(claim_id):
        raise TransactionError("Claim ID must match ^[A-Z][0-9]{3,}$", exit_code=2)
    if kind not in CLAIM_KINDS:
        raise TransactionError(f"Unknown claim kind: {kind}", exit_code=2)
    ledger = _load_ledger(root)
    claims = _claim_map(ledger)
    if claim_id in claims:
        raise TransactionError(f"Claim {claim_id} is already registered")
    dependency_list = list(dict.fromkeys(dependencies or []))
    for dependency in dependency_list:
        if dependency not in claims:
            raise TransactionError(f"Proposal dependency is not registered: {dependency}")
    source_relative = _relative_text(root, source_document)
    if not (root / source_relative).is_file():
        raise TransactionError(f"Claim source document does not exist: {source_relative}")
    relative = f"audit/proposals/{claim_id}.yaml"
    if (root / relative).exists():
        raise TransactionError(f"Proposal already exists: {relative}")
    proposed_at = _timestamp(timestamp)
    proposal: dict[str, Any] = {
        "schema_version": 1,
        "id": claim_id,
        "kind": kind,
    }
    if title:
        proposal["title"] = title
    proposal.update(
        {
            "statement": statement,
            "scope": scope,
            "dependencies": dependency_list,
            "source_document": source_relative,
            "proof_location": proof_location,
            "formal_declarations": list(dict.fromkeys(formal_declarations or [])),
            "limitations": limitations,
            "proposed_at": proposed_at,
            "proposed_by": proposed_by,
        }
    )
    _validate_instance(proposal, root / "schemas/claim-proposal-v1.json", "claim proposal")
    return _plan(
        root,
        "claim.propose",
        [(relative, _yaml_bytes(proposal))],
        {"claim_id": claim_id, "proposal": relative},
    )


def plan_claim_registration(
    root: Path,
    *,
    proposal_path: str,
    created_by_type: str,
    created_by_id: str,
    requested_by: str | None,
    approved_by_type: str,
    approved_by_id: str,
    source_revision: str | None,
    timestamp: str | None = None,
    establishes: list[str] | None = None,
    does_not_establish: list[str] | None = None,
) -> TransactionPlan:
    proposal_relative = _relative_text(root, proposal_path)
    proposal_file = root / proposal_relative
    if not proposal_file.is_file():
        raise TransactionError(f"Proposal does not exist: {proposal_relative}")
    if proposal_file.parent.resolve() != (root / "audit/proposals").resolve():
        raise TransactionError("Registered proposals must come from audit/proposals/", exit_code=2)
    proposal = read_yaml(proposal_file)
    _validate_instance(proposal, root / "schemas/claim-proposal-v1.json", "claim proposal")
    assert isinstance(proposal, dict)
    claim_id = proposal["id"]
    ledger = _load_ledger(root)
    claims = _claim_map(ledger)
    if claim_id in claims:
        raise TransactionError(f"Claim {claim_id} is already registered")
    for dependency in proposal.get("dependencies", []):
        if dependency not in claims:
            raise TransactionError(f"Proposal dependency is not registered: {dependency}")
    effective_requester = requested_by or created_by_id
    if approved_by_type == "human" and approved_by_id == effective_requester:
        raise TransactionError("A human requester cannot be the sole human approver of claim registration")
    created_at = _timestamp(timestamp)
    revision = _source_revision(root, source_revision)
    evidence_id = _next_evidence_id(root, claim_id)
    evidence = _build_evidence(
        root,
        claim_id=claim_id,
        evidence_id=evidence_id,
        evidence_class="CLAIM_REGISTRATION",
        created_at=created_at,
        created_by_type=created_by_type,
        created_by_id=created_by_id,
        establishes=establishes or [f"Registers the exact statement of claim {claim_id} at Gate 4."],
        does_not_establish=does_not_establish or [
            "Claim registration does not establish mathematical correctness, proof, novelty, or external review."
        ],
        source_revision=revision,
        artifacts=[],
        commands=[],
        environment_json=None,
        notes=f"Created from {proposal_relative}",
        reviewer_type=None,
        reviewer_id=None,
    )
    claim: dict[str, Any] = {
        "id": claim_id,
        "kind": proposal["kind"],
    }
    if proposal.get("title"):
        claim["title"] = proposal["title"]
    claim.update(
        {
            "statement": proposal["statement"],
            "scope": proposal.get("scope"),
            "epistemic_status": "OPEN",
            "verification_statuses": ["UNCHECKED"],
            "publication_status": "WORKING",
            "gate": 4,
            "dependencies": list(proposal.get("dependencies", [])),
            "evidence": [evidence_id],
            "source_document": proposal["source_document"],
            "proof_location": proposal.get("proof_location"),
            "computational_support": [],
            "formal_declarations": list(proposal.get("formal_declarations", [])),
            "external_reviews": [],
            "limitations": list(proposal["limitations"]),
            "introduced_at": created_at,
            "updated_at": created_at,
        }
    )
    ledger["claims"].append(claim)
    transition = {
        "schema_version": 1,
        "claim_id": claim_id,
        "axis": "gate",
        "from": 3,
        "to": 4,
        "requested_by": effective_requester,
        "approved_by": _actor(approved_by_type, approved_by_id, approver=True),
        "evidence": [evidence_id],
        "reason": "Exact claim registered from an approved proposal.",
        "created_at": created_at,
    }
    evidence_path = f"audit/evidence/{claim_id}/{evidence_id}.yaml"
    transition_path = _unique_record_path(
        root,
        f"audit/transitions/{claim_id}/{_filename_timestamp(created_at)}-gate-3-to-4.yaml",
    )
    return _plan(
        root,
        "claim.register",
        [
            ("claims/claims.yaml", _ledger_bytes(root, ledger)),
            (evidence_path, _yaml_bytes(evidence)),
            (transition_path, _yaml_bytes(transition)),
        ],
        {
            "claim_id": claim_id,
            "proposal": proposal_relative,
            "evidence_ids": [evidence_id],
            "transition_paths": [transition_path],
        },
    )
