from __future__ import annotations

from pathlib import Path

import pytest

from cruthunas.models import read_yaml
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
            source.read_text(encoding="utf-8"), encoding="utf-8"
        )
    (tmp_path / "claims").mkdir()
    (tmp_path / "claims/schema.json").write_text(
        (REPO_ROOT / "claims/schema.json").read_text(encoding="utf-8"),
        encoding="utf-8",
    )
    _write(tmp_path / "claims/claims.yaml", "schema_version: 1\nclaims: []\n")
    _write(tmp_path / "docs/proofs/T001.md", "# T001\n")
    return tmp_path


def _proposal(root: Path, proposed_by: str = "github:originator") -> None:
    apply_plan(
        plan_claim_proposal(
            root,
            claim_id="T001",
            kind="THEOREM",
            statement="  For every n in {1}, n = 1.  ",
            source_document="docs/proofs/T001.md",
            limitations=["  Fixture only  "],
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
            created_by_id="github:originator",
            requested_by="github:originator",
            approved_by_type="policy",
            approved_by_id="cruthunas/claim-registration-v1",
            source_revision="a" * 40,
            timestamp="2026-07-30T19:01:00Z",
        )
    )


def test_proposal_text_and_identity_are_normalized(tmp_path: Path) -> None:
    root = _project(tmp_path)
    _proposal(root, "  GitHub:Originator  ")
    proposal = read_yaml(root / "audit/proposals/T001.yaml")
    assert proposal["statement"] == "For every n in {1}, n = 1."
    assert proposal["limitations"] == ["Fixture only"]
    assert proposal["proposed_by"] == "GitHub:Originator"


def test_registration_rejects_case_and_whitespace_identity_bypass(tmp_path: Path) -> None:
    root = _project(tmp_path)
    _proposal(root, " github:originator ")
    with pytest.raises(TransactionError, match="originator or requester"):
        plan_claim_registration(
            root,
            proposal_path="audit/proposals/T001.yaml",
            created_by_type="agent",
            created_by_id="registry-agent",
            requested_by="github:requester",
            approved_by_type="human",
            approved_by_id=" GITHUB:ORIGINATOR ",
            source_revision="a" * 40,
            timestamp="2026-07-30T19:01:00Z",
        )


def test_registration_must_follow_proposal_time(tmp_path: Path) -> None:
    root = _project(tmp_path)
    _proposal(root)
    with pytest.raises(TransactionError, match="must be later"):
        plan_claim_registration(
            root,
            proposal_path="audit/proposals/T001.yaml",
            created_by_type="agent",
            created_by_id="registry-agent",
            requested_by="github:requester",
            approved_by_type="policy",
            approved_by_id="registration-policy",
            source_revision="a" * 40,
            timestamp="2026-07-30T18:59:00Z",
        )


def test_evidence_timestamp_must_advance_claim_updated_at(tmp_path: Path) -> None:
    root = _project(tmp_path)
    _register(root)
    with pytest.raises(TransactionError, match="must be later"):
        plan_evidence_add(
            root,
            claim_id="T001",
            evidence_class="REVIEW_INTERNAL",
            created_by_type="agent",
            created_by_id="audit-agent",
            establishes=["Audit completed"],
            does_not_establish=["External review"],
            source_revision="b" * 40,
            timestamp="2026-07-30T19:01:00Z",
        )


def test_transition_timestamp_must_advance_claim_updated_at(tmp_path: Path) -> None:
    root = _project(tmp_path)
    _register(root)
    apply_plan(
        plan_evidence_add(
            root,
            claim_id="T001",
            evidence_class="REVIEW_INTERNAL",
            created_by_type="agent",
            created_by_id="audit-agent",
            establishes=["Audit completed"],
            does_not_establish=["External review"],
            source_revision="b" * 40,
            timestamp="2026-07-30T19:02:00Z",
        )
    )
    with pytest.raises(TransactionError, match="must be later"):
        plan_claim_transition(
            root,
            claim_id="T001",
            verification_add=["INTERNAL_AUDIT"],
            reason="Audit recorded",
            requested_by="github:originator",
            approved_by_type="policy",
            approved_by_id="transition-policy",
            evidence_ids=["E-T001-0002"],
            timestamp="2026-07-30T19:01:30Z",
        )
