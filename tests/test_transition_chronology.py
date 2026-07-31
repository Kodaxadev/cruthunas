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


def _register(root: Path) -> None:
    apply_plan(
        plan_claim_proposal(
            root,
            claim_id="T001",
            kind="THEOREM",
            statement="For every n in {1}, n = 1.",
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


def _add_review(root: Path, timestamp: str) -> str:
    details_path = root / "audit/fixtures/gate-five-review.json"
    _write(
        details_path,
        json.dumps(
            {
                "review_roles": {
                    "prover": "Reviewed the proof argument for completeness.",
                    "falsifier": "Searched for counterexamples and failure modes.",
                    "dependency_auditor": "Checked dependency existence and support.",
                    "statement_auditor": "Checked the registered statement and quantifiers.",
                }
            },
            sort_keys=True,
        ),
    )
    result = apply_plan(
        plan_evidence_add(
            root,
            claim_id="T001",
            evidence_class="REVIEW_INTERNAL",
            created_by_type="agent",
            created_by_id="fixture-reviewer",
            establishes=["Internal review completed"],
            does_not_establish=["External review"],
            source_revision="a" * 40,
            details_json="audit/fixtures/gate-five-review.json",
            timestamp=timestamp,
        )
    )
    return result["evidence_ids"][0]


def _write_linked_review_without_advancing_ledger(root: Path, timestamp: str) -> str:
    evidence_id = "E-T001-0002"
    record = {
        "schema_version": 1,
        "id": evidence_id,
        "claim_id": "T001",
        "class": "REVIEW_INTERNAL",
        "created_at": timestamp,
        "created_by": {"type": "agent", "id": "fixture-reviewer"},
        "establishes": ["Internal review completed"],
        "does_not_establish": ["External review"],
        "artifacts": [],
        "commands": [],
        "environment": None,
        "details": None,
        "source_revision": "a" * 40,
        "notes": None,
    }
    _write(
        root / f"audit/evidence/T001/{evidence_id}.yaml",
        yaml.safe_dump(record, sort_keys=False),
    )
    ledger = read_yaml(root / "claims/claims.yaml")
    ledger["claims"][0]["evidence"].append(evidence_id)
    _write(root / "claims/claims.yaml", yaml.safe_dump(ledger, sort_keys=False))
    return evidence_id


def _promote_ledger(root: Path, updated_at: str) -> None:
    ledger = read_yaml(root / "claims/claims.yaml")
    ledger["claims"][0]["gate"] = 5
    ledger["claims"][0]["updated_at"] = updated_at
    _write(root / "claims/claims.yaml", yaml.safe_dump(ledger, sort_keys=False))


def _write_gate_transition(
    root: Path,
    *,
    evidence_id: str,
    created_at: str,
    filename: str,
) -> None:
    transition = {
        "schema_version": 1,
        "claim_id": "T001",
        "axis": "gate",
        "from": 4,
        "to": 5,
        "requested_by": "github:tester",
        "approved_by": {"type": "policy", "id": "fixture-policy"},
        "evidence": [evidence_id],
        "reason": "Adversarial review recorded",
        "created_at": created_at,
    }
    _write(
        root / f"audit/transitions/T001/{filename}",
        yaml.safe_dump(transition, sort_keys=False),
    )


def test_transition_offsets_are_sorted_by_absolute_time(tmp_path: Path) -> None:
    root = _project(tmp_path)
    _register(root)
    review_id = _add_review(root, "2026-07-30T19:02:00Z")
    _promote_ledger(root, "2026-07-30T19:30:00Z")
    _write_gate_transition(
        root,
        evidence_id=review_id,
        created_at="2026-07-30T18:30:00-01:00",
        filename="20260730T183000-0100-gate-4-to-5.yaml",
    )

    assert run_checks(root).ok


def test_duplicate_axis_transition_timestamps_are_rejected(tmp_path: Path) -> None:
    root = _project(tmp_path)
    _register(root)
    review_id = _add_review(root, "2026-07-30T19:02:00Z")
    _promote_ledger(root, "2026-07-30T19:03:00Z")
    _write_gate_transition(
        root,
        evidence_id=review_id,
        created_at="2026-07-30T19:03:00Z",
        filename="20260730T190300000000Z-gate-4-to-5-a.yaml",
    )
    _write_gate_transition(
        root,
        evidence_id=review_id,
        created_at="2026-07-30T19:03:00Z",
        filename="20260730T190300000000Z-gate-4-to-5-b.yaml",
    )

    result = run_checks(root)
    assert "transition.non_increasing_timestamp" in {
        finding.code for finding in result.findings
    }


def test_transition_cannot_cite_future_evidence(tmp_path: Path) -> None:
    root = _project(tmp_path)
    _register(root)
    review_id = _write_linked_review_without_advancing_ledger(
        root,
        "2026-07-30T19:04:00Z",
    )

    with pytest.raises(TransactionError, match="created after the transition"):
        plan_claim_transition(
            root,
            claim_id="T001",
            gate=5,
            reason="Attempt to cite future-dated evidence",
            requested_by="github:tester",
            approved_by_type="policy",
            approved_by_id="cruthunas/transition-v1",
            evidence_ids=[review_id],
            timestamp="2026-07-30T19:03:00Z",
        )
