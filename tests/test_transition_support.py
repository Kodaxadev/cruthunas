from __future__ import annotations

import json
from pathlib import Path

import pytest
import yaml

from cruthunas.models import read_yaml
from cruthunas.policy import run_checks
from cruthunas.transactions import (
    TransactionError,
    apply_plan,
    plan_claim_proposal,
    plan_claim_registration,
    plan_claim_transition,
    plan_evidence_add,
)

REPO_ROOT = Path(__file__).parents[1]


def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def _project(tmp_path: Path) -> Path:
    (tmp_path / "schemas").mkdir(parents=True)
    for source in (REPO_ROOT / "schemas").glob("*.json"):
        (tmp_path / "schemas" / source.name).write_text(
            source.read_text(encoding="utf-8"),
            encoding="utf-8",
        )
    (tmp_path / "claims").mkdir()
    (tmp_path / "claims/schema.json").write_text(
        (REPO_ROOT / "claims/schema.json").read_text(encoding="utf-8"),
        encoding="utf-8",
    )
    _write(tmp_path / "claims/claims.yaml", "schema_version: 1\nclaims: []\n")
    _write(tmp_path / "docs/proofs/T001.md", "# T001\n")
    return tmp_path


def _proposal(root: Path, *, proposed_by: str = "github:tester") -> None:
    apply_plan(
        plan_claim_proposal(
            root,
            claim_id="T001",
            kind="THEOREM",
            statement="For every n in {1}, n = 1.",
            source_document="docs/proofs/T001.md",
            limitations=["Fixture only"],
            proposed_by=proposed_by,
            timestamp="2026-07-30T19:00:00Z",
        )
    )


def _register(root: Path) -> None:
    _proposal(root)
    apply_plan(
        plan_claim_registration(
            root,
            proposal_path="audit/proposals/T001.yaml",
            created_by_type="human",
            created_by_id="github:tester",
            requested_by="github:tester",
            approved_by_type="policy",
            approved_by_id="cruthunas/claim-registration-v1",
            source_revision="a" * 40,
            timestamp="2026-07-30T19:01:00Z",
        )
    )


def _details(root: Path, name: str, value: dict) -> str:
    relative = f"audit/fixtures/{name}.json"
    _write(root / relative, json.dumps(value))
    return relative


def _gate_five_details(root: Path, *, complete: bool = True) -> str:
    roles = {
        "prover": "Reviewed the proof argument for completeness.",
    }
    if complete:
        roles.update(
            {
                "falsifier": "Searched for counterexamples and failure modes.",
                "dependency_auditor": "Checked dependency existence and support.",
                "statement_auditor": "Checked the registered statement and quantifiers.",
            }
        )
    return _details(root, "gate-five-review", {"review_roles": roles})


def _add_evidence(
    root: Path,
    evidence_class: str,
    timestamp: str,
    *,
    details_json: str | None = None,
) -> str:
    result = apply_plan(
        plan_evidence_add(
            root,
            claim_id="T001",
            evidence_class=evidence_class,
            created_by_type="agent",
            created_by_id="fixture-agent",
            establishes=[f"Fixture {evidence_class} evidence"],
            does_not_establish=["Anything beyond this fixture"],
            source_revision="a" * 40,
            details_json=details_json,
            timestamp=timestamp,
        )
    )
    return result["evidence_ids"][0]


def test_gate_promotion_requires_transition_evidence_class(tmp_path: Path) -> None:
    root = _project(tmp_path)
    _register(root)

    with pytest.raises(TransactionError, match="gate transition"):
        plan_claim_transition(
            root,
            claim_id="T001",
            gate=5,
            reason="Attempt unsupported Gate 5 promotion",
            requested_by="github:tester",
            approved_by_type="policy",
            approved_by_id="cruthunas/transition-v1",
            evidence_ids=["E-T001-0001"],
            timestamp="2026-07-30T19:02:00Z",
        )

    details = _gate_five_details(root)
    review_id = _add_evidence(
        root,
        "REVIEW_INTERNAL",
        "2026-07-30T19:02:00Z",
        details_json=details,
    )
    apply_plan(
        plan_claim_transition(
            root,
            claim_id="T001",
            gate=5,
            reason="Adversarial review recorded",
            requested_by="github:tester",
            approved_by_type="policy",
            approved_by_id="cruthunas/transition-v1",
            evidence_ids=[review_id],
            timestamp="2026-07-30T19:03:00Z",
        )
    )
    assert run_checks(root).ok


def test_gate_five_requires_all_adversarial_review_roles(tmp_path: Path) -> None:
    root = _project(tmp_path)
    _register(root)
    details = _gate_five_details(root, complete=False)
    review_id = _add_evidence(
        root,
        "REVIEW_INTERNAL",
        "2026-07-30T19:02:00Z",
        details_json=details,
    )

    with pytest.raises(TransactionError, match="details.review_roles"):
        plan_claim_transition(
            root,
            claim_id="T001",
            gate=5,
            reason="Incomplete adversarial review",
            requested_by="github:tester",
            approved_by_type="policy",
            approved_by_id="cruthunas/transition-v1",
            evidence_ids=[review_id],
            timestamp="2026-07-30T19:03:00Z",
        )


def test_policy_rejects_manual_gate_five_review_without_roles(tmp_path: Path) -> None:
    root = _project(tmp_path)
    _register(root)
    review_id = _add_evidence(root, "REVIEW_INTERNAL", "2026-07-30T19:02:00Z")
    ledger = read_yaml(root / "claims/claims.yaml")
    ledger["claims"][0]["gate"] = 5
    ledger["claims"][0]["updated_at"] = "2026-07-30T19:03:00Z"
    _write(root / "claims/claims.yaml", yaml.safe_dump(ledger, sort_keys=False))
    transition = {
        "schema_version": 1,
        "claim_id": "T001",
        "axis": "gate",
        "from": 4,
        "to": 5,
        "requested_by": "github:tester",
        "approved_by": {"type": "policy", "id": "fixture-policy"},
        "evidence": [review_id],
        "reason": "Generic review label without required role records",
        "created_at": "2026-07-30T19:03:00Z",
    }
    _write(
        root / "audit/transitions/T001/20260730T190300Z-gate-4-to-5.yaml",
        yaml.safe_dump(transition, sort_keys=False),
    )

    result = run_checks(root)
    assert any(
        finding.code == "transition.unsupported_evidence"
        and "details.review_roles" in finding.message
        for finding in result.findings
    )


def test_gate_disposition_can_close_permitted_gate(tmp_path: Path) -> None:
    root = _project(tmp_path)
    _register(root)
    disposition_id = _add_evidence(root, "GATE_DISPOSITION", "2026-07-30T19:02:00Z")
    apply_plan(
        plan_claim_transition(
            root,
            claim_id="T001",
            gate=5,
            reason="Gate 5 is not applicable to this definition fixture",
            requested_by="github:tester",
            approved_by_type="policy",
            approved_by_id="cruthunas/transition-v1",
            evidence_ids=[disposition_id],
            timestamp="2026-07-30T19:03:00Z",
        )
    )
    assert run_checks(root).ok


def test_unrelated_linked_evidence_cannot_support_verification_transition(
    tmp_path: Path,
) -> None:
    root = _project(tmp_path)
    _register(root)
    _add_evidence(root, "REVIEW_INTERNAL", "2026-07-30T19:02:00Z")

    with pytest.raises(TransactionError, match="verification transition"):
        plan_claim_transition(
            root,
            claim_id="T001",
            verification_add=["INTERNAL_AUDIT"],
            reason="Cites registration instead of review",
            requested_by="github:tester",
            approved_by_type="policy",
            approved_by_id="cruthunas/transition-v1",
            evidence_ids=["E-T001-0001"],
            timestamp="2026-07-30T19:03:00Z",
        )


def test_proved_requires_proof_and_review_in_same_transition(tmp_path: Path) -> None:
    root = _project(tmp_path)
    _register(root)
    proof_id = _add_evidence(root, "PROOF", "2026-07-30T19:02:00Z")
    review_id = _add_evidence(root, "REVIEW_INTERNAL", "2026-07-30T19:03:00Z")

    with pytest.raises(TransactionError, match="REVIEW_EXTERNAL or REVIEW_INTERNAL"):
        plan_claim_transition(
            root,
            claim_id="T001",
            epistemic="PROVED",
            reason="Proof without cited review",
            requested_by="github:tester",
            approved_by_type="policy",
            approved_by_id="cruthunas/transition-v1",
            evidence_ids=[proof_id],
            timestamp="2026-07-30T19:04:00Z",
        )

    apply_plan(
        plan_claim_transition(
            root,
            claim_id="T001",
            epistemic="PROVED",
            reason="Exact proof and internal adversarial review recorded",
            requested_by="github:tester",
            approved_by_type="policy",
            approved_by_id="cruthunas/transition-v1",
            evidence_ids=[proof_id, review_id],
            timestamp="2026-07-30T19:04:00Z",
        )
    )
    assert run_checks(root).ok


def test_heuristic_transition_accepts_derivation(tmp_path: Path) -> None:
    root = _project(tmp_path)
    _register(root)
    derivation_id = _add_evidence(root, "DERIVATION", "2026-07-30T19:02:00Z")
    apply_plan(
        plan_claim_transition(
            root,
            claim_id="T001",
            epistemic="HEURISTIC",
            reason="Structured heuristic derivation recorded",
            requested_by="github:tester",
            approved_by_type="policy",
            approved_by_id="cruthunas/transition-v1",
            evidence_ids=[derivation_id],
            timestamp="2026-07-30T19:03:00Z",
        )
    )
    assert run_checks(root).ok


def test_policy_rejects_manual_unsupported_transition(tmp_path: Path) -> None:
    root = _project(tmp_path)
    _register(root)
    ledger = read_yaml(root / "claims/claims.yaml")
    ledger["claims"][0]["gate"] = 5
    ledger["claims"][0]["updated_at"] = "2026-07-30T19:02:00Z"
    _write(root / "claims/claims.yaml", yaml.safe_dump(ledger, sort_keys=False))
    transition = {
        "schema_version": 1,
        "claim_id": "T001",
        "axis": "gate",
        "from": 4,
        "to": 5,
        "requested_by": "github:tester",
        "approved_by": {"type": "policy", "id": "fixture-policy"},
        "evidence": ["E-T001-0001"],
        "reason": "Unsupported manual promotion",
        "created_at": "2026-07-30T19:02:00Z",
    }
    _write(
        root / "audit/transitions/T001/20260730T190200Z-gate-4-to-5.yaml",
        yaml.safe_dump(transition, sort_keys=False),
    )
    result = run_checks(root)
    assert "transition.unsupported_evidence" in {
        finding.code for finding in result.findings
    }


def test_registration_rejects_human_proposal_originator_as_approver(
    tmp_path: Path,
) -> None:
    root = _project(tmp_path)
    _proposal(root, proposed_by="github:originator")
    with pytest.raises(TransactionError, match="originator or requester"):
        plan_claim_registration(
            root,
            proposal_path="audit/proposals/T001.yaml",
            created_by_type="agent",
            created_by_id="registry-agent",
            requested_by="github:requester",
            approved_by_type="human",
            approved_by_id="github:originator",
            source_revision="a" * 40,
            timestamp="2026-07-30T19:01:00Z",
        )


def test_policy_rejects_manual_registration_originator_self_approval(
    tmp_path: Path,
) -> None:
    root = _project(tmp_path)
    _proposal(root, proposed_by="github:originator")
    apply_plan(
        plan_claim_registration(
            root,
            proposal_path="audit/proposals/T001.yaml",
            created_by_type="agent",
            created_by_id="registry-agent",
            requested_by="github:requester",
            approved_by_type="policy",
            approved_by_id="cruthunas/claim-registration-v1",
            source_revision="a" * 40,
            timestamp="2026-07-30T19:01:00Z",
        )
    )
    transition_path = next((root / "audit/transitions/T001").glob("*.yaml"))
    transition = read_yaml(transition_path)
    transition["approved_by"] = {"type": "human", "id": "github:originator"}
    _write(transition_path, yaml.safe_dump(transition, sort_keys=False))
    result = run_checks(root)
    assert "transition.registration_self_approval" in {
        finding.code for finding in result.findings
    }
