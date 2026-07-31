from __future__ import annotations

from pathlib import Path
from typing import Any

from .transaction_evidence import (
    _build_evidence,
    _next_evidence_id,
    _unique_record_snapshot,
)
from .transaction_plan import _plan
from .transaction_types import (
    CLAIM_ID,
    CLAIM_KINDS,
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
    _relative_text,
    _require_later,
    _source_revision,
    _timestamp,
    _validate_instance,
    _yaml_bytes,
    _yaml_from_snapshot,
)


def _optional_text(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = value.strip()
    return normalized or None


def _text_list(values: list[str], label: str) -> list[str]:
    normalized = [_nonempty_text(item, label) for item in values]
    return list(dict.fromkeys(normalized))


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
    ledger, ledger_snapshot = _load_ledger_snapshot(root)
    claims = _claim_map(ledger)
    if claim_id in claims:
        raise TransactionError(f"Claim {claim_id} is already registered")
    dependency_list = list(dict.fromkeys(dependencies or []))
    for dependency in dependency_list:
        if dependency not in claims:
            raise TransactionError(f"Proposal dependency is not registered: {dependency}")
    source_relative = _relative_text(root, source_document)
    source_snapshot = _capture_file(root, source_relative, required=True)
    relative = f"audit/proposals/{claim_id}.yaml"
    proposal_target = _capture_file(root, relative)
    if proposal_target.content is not None:
        raise TransactionError(f"Proposal already exists: {relative}")
    proposed_at = _timestamp(timestamp)
    proposal: dict[str, Any] = {
        "schema_version": 1,
        "id": claim_id,
        "kind": kind,
    }
    normalized_title = _optional_text(title)
    if normalized_title:
        proposal["title"] = normalized_title
    proposal.update(
        {
            "statement": _nonempty_text(statement, "Claim statement"),
            "scope": _optional_text(scope),
            "dependencies": dependency_list,
            "source_document": source_relative,
            "proof_location": _optional_text(proof_location),
            "formal_declarations": _text_list(
                formal_declarations or [], "Formal declaration"
            ),
            "limitations": _text_list(limitations, "Claim limitation"),
            "proposed_at": proposed_at,
            "proposed_by": _identity(proposed_by, "Proposal originator"),
        }
    )
    _validate_instance(proposal, root / "schemas/claim-proposal-v1.json", "claim proposal")
    return _plan(
        root,
        "claim.propose",
        [(relative, _yaml_bytes(proposal))],
        {"claim_id": claim_id, "proposal": relative},
        read_snapshots=[ledger_snapshot, source_snapshot],
        write_snapshots={relative: proposal_target},
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
    proposal_snapshot = _capture_file(root, proposal_relative, required=True)
    proposal_file = root / proposal_relative
    if proposal_file.parent.resolve() != (root / "audit/proposals").resolve():
        raise TransactionError("Registered proposals must come from audit/proposals/", exit_code=2)
    proposal = _yaml_from_snapshot(proposal_snapshot)
    _validate_instance(proposal, root / "schemas/claim-proposal-v1.json", "claim proposal")
    assert isinstance(proposal, dict)
    claim_id = proposal["id"]
    ledger, ledger_snapshot = _load_ledger_snapshot(root)
    claims = _claim_map(ledger)
    if claim_id in claims:
        raise TransactionError(f"Claim {claim_id} is already registered")
    for dependency in proposal.get("dependencies", []):
        if dependency not in claims:
            raise TransactionError(f"Proposal dependency is not registered: {dependency}")
    source_snapshot = _capture_file(root, proposal["source_document"], required=True)
    creator = _actor(created_by_type, created_by_id)
    effective_requester = _identity(
        requested_by or creator["id"], "Registration requester"
    )
    approver = _actor(approved_by_type, approved_by_id, approver=True)
    if approved_by_type == "human":
        approver_key = _identity_key(approver["id"])
        originator_keys = {
            _identity_key(effective_requester),
            _identity_key(proposal.get("proposed_by")),
        }
        if creator["type"] == "human":
            originator_keys.add(_identity_key(creator["id"]))
        if approver_key in originator_keys:
            raise TransactionError(
                "A human claim originator or requester cannot be the sole human registration approver"
            )
    created_at = _timestamp(timestamp)
    _require_later(created_at, proposal.get("proposed_at"), "Claim registration")
    revision = _source_revision(root, source_revision)
    expected_git_head = revision if source_revision is None else None
    evidence_id = _next_evidence_id(root, claim_id)
    evidence, evidence_inputs = _build_evidence(
        root,
        claim_id=claim_id,
        evidence_id=evidence_id,
        evidence_class="CLAIM_REGISTRATION",
        created_at=created_at,
        created_by_type=creator["type"],
        created_by_id=creator["id"],
        establishes=establishes or [
            f"Registers the exact statement of claim {claim_id} at Gate 4."
        ],
        does_not_establish=does_not_establish or [
            "Claim registration does not establish mathematical correctness, proof, novelty, or external review."
        ],
        source_revision=revision,
        artifacts=[],
        commands=[],
        environment_json=None,
        details_json=None,
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
        "approved_by": approver,
        "evidence": [evidence_id],
        "reason": "Exact claim registered from an approved proposal.",
        "created_at": created_at,
    }
    evidence_path = f"audit/evidence/{claim_id}/{evidence_id}.yaml"
    evidence_target = _capture_file(root, evidence_path)
    if evidence_target.content is not None:
        raise TransactionError(f"Evidence ID already exists: {evidence_id}")
    transition_target = _unique_record_snapshot(
        root,
        f"audit/transitions/{claim_id}/{_filename_timestamp(created_at)}-gate-3-to-4.yaml",
    )
    transition_path = transition_target.path
    write_snapshots: dict[str, FileSnapshot] = {
        "claims/claims.yaml": ledger_snapshot,
        evidence_path: evidence_target,
        transition_path: transition_target,
    }
    return _plan(
        root,
        "claim.register",
        [
            ("claims/claims.yaml", _ledger_bytes(root, ledger, ledger_snapshot)),
            (evidence_path, _yaml_bytes(evidence)),
            (transition_path, _yaml_bytes(transition)),
        ],
        {
            "claim_id": claim_id,
            "proposal": proposal_relative,
            "evidence_ids": [evidence_id],
            "transition_paths": [transition_path],
        },
        read_snapshots=[
            proposal_snapshot,
            source_snapshot,
            *evidence_inputs,
        ],
        write_snapshots=write_snapshots,
        expected_git_head=expected_git_head,
    )
