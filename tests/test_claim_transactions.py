from __future__ import annotations

import builtins
import json
from pathlib import Path

import pytest
import yaml

from cruthunas.cli import main
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
    _write(
        tmp_path / "claims/claims.yaml",
        "# ledger header\n\nschema_version: 1\nclaims: []\n",
    )
    _write(tmp_path / "docs/proofs/T001.md", "# T001\n")
    return tmp_path


def _register(root: Path) -> None:
    apply_plan(
        plan_claim_proposal(
            root,
            claim_id="T001",
            kind="THEOREM",
            title="Fixture theorem",
            statement="For every n in {1}, n = 1.",
            scope="n in {1}",
            dependencies=[],
            source_document="docs/proofs/T001.md",
            limitations=["Fixture only"],
            proposed_by="github:tester",
            timestamp="2026-07-30T19:00:00Z",
        )
    )
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



def test_propose_and_register_create_valid_complete_transaction(tmp_path: Path) -> None:
    root = _project(tmp_path)
    _register(root)
    result = run_checks(root)
    assert result.ok, result.to_dict()
    ledger_text = (root / "claims/claims.yaml").read_text(encoding="utf-8")
    assert ledger_text.startswith("# ledger header")
    ledger = read_yaml(root / "claims/claims.yaml")
    claim = ledger["claims"][0]
    assert claim["id"] == "T001"
    assert claim["gate"] == 4
    assert claim["evidence"] == ["E-T001-0001"]
    evidence = read_yaml(root / "audit/evidence/T001/E-T001-0001.yaml")
    assert evidence["class"] == "CLAIM_REGISTRATION"
    transitions = list((root / "audit/transitions/T001").glob("*.yaml"))
    assert len(transitions) == 1
    transition = read_yaml(transitions[0])
    assert transition["from"] == 3
    assert transition["to"] == 4


def test_evidence_add_links_claim_and_computational_support(tmp_path: Path) -> None:
    root = _project(tmp_path)
    _register(root)
    apply_plan(
        plan_evidence_add(
            root,
            claim_id="T001",
            evidence_class="COMPUTATION",
            created_by_type="agent",
            created_by_id="test-agent",
            establishes=["Fixture checked for n = 1"],
            does_not_establish=["Any universal statement"],
            source_revision="b" * 40,
            commands=["python check.py"],
            timestamp="2026-07-30T19:02:00Z",
        )
    )
    result = run_checks(root)
    assert result.ok, result.to_dict()
    claim = read_yaml(root / "claims/claims.yaml")["claims"][0]
    assert claim["evidence"] == ["E-T001-0001", "E-T001-0002"]
    assert claim["computational_support"] == ["E-T001-0002"]


def test_transition_can_create_evidence_and_change_multiple_axes(tmp_path: Path) -> None:
    root = _project(tmp_path)
    _register(root)
    apply_plan(
        plan_claim_transition(
            root,
            claim_id="T001",
            epistemic="COMPUTATIONAL",
            verification_add=["INDEPENDENT_REPRODUCTION"],
            reason="Independent finite fixture reproduced",
            requested_by="github:tester",
            approved_by_type="policy",
            approved_by_id="cruthunas/transition-v1",
            new_evidence_class="REPRODUCTION",
            created_by_type="human",
            created_by_id="github:independent-tester",
            establishes=["Independent fixture reproduction succeeded"],
            does_not_establish=["Anything outside n = 1"],
            source_revision="c" * 40,
            timestamp="2026-07-30T19:03:00Z",
        )
    )
    result = run_checks(root)
    assert result.ok, result.to_dict()
    claim = read_yaml(root / "claims/claims.yaml")["claims"][0]
    assert claim["epistemic_status"] == "COMPUTATIONAL"
    assert claim["verification_statuses"] == ["INDEPENDENT_REPRODUCTION"]
    assert len(list((root / "audit/transitions/T001").glob("*.yaml"))) == 3


def test_invalid_transition_leaves_repository_unchanged(tmp_path: Path) -> None:
    root = _project(tmp_path)
    _register(root)
    ledger_before = (root / "claims/claims.yaml").read_bytes()
    paths_before = sorted(str(path.relative_to(root)) for path in root.rglob("*") if path.is_file())
    with pytest.raises(TransactionError):
        plan_claim_transition(
            root,
            claim_id="T001",
            epistemic="PROVED",
            reason="Unsupported promotion",
            requested_by="github:tester",
            approved_by_type="policy",
            approved_by_id="cruthunas/transition-v1",
            new_evidence_class="REVIEW_INTERNAL",
            created_by_type="agent",
            created_by_id="review-agent",
            establishes=["Internal review completed"],
            does_not_establish=["A complete proof"],
            source_revision="d" * 40,
            timestamp="2026-07-30T19:04:00Z",
        )
    assert (root / "claims/claims.yaml").read_bytes() == ledger_before
    paths_after = sorted(str(path.relative_to(root)) for path in root.rglob("*") if path.is_file())
    assert paths_after == paths_before


def test_external_review_evidence_requires_named_reviewer(tmp_path: Path) -> None:
    root = _project(tmp_path)
    _register(root)
    with pytest.raises(TransactionError, match="requires --reviewer-type"):
        plan_evidence_add(
            root,
            claim_id="T001",
            evidence_class="REVIEW_EXTERNAL",
            created_by_type="human",
            created_by_id="github:tester",
            establishes=["Review occurred"],
            does_not_establish=["Automatic correctness"],
            source_revision="e" * 40,
            timestamp="2026-07-30T19:05:00Z",
        )


def test_duplicate_registration_is_rejected_without_changes(tmp_path: Path) -> None:
    root = _project(tmp_path)
    _register(root)
    before = (root / "claims/claims.yaml").read_bytes()
    with pytest.raises(TransactionError, match="already registered"):
        plan_claim_registration(
            root,
            proposal_path="audit/proposals/T001.yaml",
            created_by_type="human",
            created_by_id="github:tester",
            requested_by="github:tester",
            approved_by_type="policy",
            approved_by_id="cruthunas/claim-registration-v1",
            source_revision="f" * 40,
            timestamp="2026-07-30T19:06:00Z",
        )
    assert (root / "claims/claims.yaml").read_bytes() == before


