from __future__ import annotations

import json
from pathlib import Path

import pytest

from cruthunas.policy import run_checks
from cruthunas.transactions import (
    TransactionError,
    apply_plan,
    plan_claim_proposal,
    plan_claim_registration,
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


def _register(root: Path) -> None:
    apply_plan(
        plan_claim_proposal(
            root,
            claim_id="T001",
            kind="THEOREM",
            statement="For every n in {1}, n = 1.",
            source_document="docs/proofs/T001.md",
            limitations=["Fixture only"],
            proposed_by="github:originator",
            timestamp="2026-07-30T19:00:00Z",
        )
    )
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


def _json(root: Path, name: str, value: dict) -> str:
    relative = f"audit/fixtures/{name}.json"
    _write(root / relative, json.dumps(value))
    return relative


def _artifact(root: Path, name: str) -> str:
    relative = f"certificates/T001/{name}.json"
    _write(root / relative, '{"ok": true}\n')
    return relative


def _independence_details(root: Path, name: str) -> str:
    return _json(
        root,
        name,
        {
            "independent": True,
            "relationship_to_originator": "No shared originating context",
            "inputs_received": ["registered statement"],
            "saw_original_work": False,
            "implementation_boundary": "Fresh implementation or review context",
            "dependency_boundary": "No project implementation imports",
            "result": "No blocking disagreement",
            "disagreements": "None",
        },
    )


@pytest.mark.parametrize(
    ("evidence_class", "reviewer_type", "reviewer_id"),
    [
        ("COMPUTATION", None, None),
        ("REPRODUCTION", None, None),
        ("FORMALIZATION", None, None),
        ("REVIEW_EXTERNAL", "human", "github:independent-reviewer"),
        ("RELEASE", None, None),
    ],
)
def test_strict_evidence_classes_require_complete_contracts(
    tmp_path: Path,
    evidence_class: str,
    reviewer_type: str | None,
    reviewer_id: str | None,
) -> None:
    root = _project(tmp_path)
    _register(root)
    with pytest.raises(TransactionError, match=evidence_class):
        plan_evidence_add(
            root,
            claim_id="T001",
            evidence_class=evidence_class,
            created_by_type="agent",
            created_by_id="fixture-agent",
            establishes=["Fixture evidence recorded"],
            does_not_establish=["Anything beyond this fixture"],
            source_revision="b" * 40,
            reviewer_type=reviewer_type,
            reviewer_id=reviewer_id,
            timestamp="2026-07-30T19:02:00Z",
        )


def test_external_review_rejects_originator_as_reviewer_after_normalization(
    tmp_path: Path,
) -> None:
    root = _project(tmp_path)
    _register(root)
    details = _independence_details(root, "external-review")
    with pytest.raises(TransactionError, match="independent of the claim originator"):
        plan_evidence_add(
            root,
            claim_id="T001",
            evidence_class="REVIEW_EXTERNAL",
            created_by_type="agent",
            created_by_id="review-recorder",
            establishes=["External review completed"],
            does_not_establish=["Automatic mathematical correctness"],
            source_revision="b" * 40,
            details_json=details,
            reviewer_type="human",
            reviewer_id=" GITHUB:ORIGINATOR ",
            timestamp="2026-07-30T19:02:00Z",
        )


def test_reproduction_rejects_originator_as_reproducer(tmp_path: Path) -> None:
    root = _project(tmp_path)
    _register(root)
    artifact = _artifact(root, "reproduction")
    environment = _json(root, "reproduction-environment", {"interpreter": "Python 3.13", "dependencies": ["none"], "operating_system": "fixture", "locale": "C", "timezone": "UTC", "environment_variables": "none", "random_seeds": "not applicable"})
    details = _independence_details(root, "reproduction-details")
    with pytest.raises(TransactionError, match="creator must be independent"):
        plan_evidence_add(
            root,
            claim_id="T001",
            evidence_class="REPRODUCTION",
            created_by_type="human",
            created_by_id="github:originator",
            establishes=["Fixture reproduced"],
            does_not_establish=["Anything outside the fixture"],
            source_revision="b" * 40,
            artifacts=[artifact],
            commands=["python reproduce.py"],
            environment_json=environment,
            details_json=details,
            timestamp="2026-07-30T19:02:00Z",
        )


def test_valid_independent_external_review_passes_policy(tmp_path: Path) -> None:
    root = _project(tmp_path)
    _register(root)
    details = _independence_details(root, "valid-external-review")
    apply_plan(
        plan_evidence_add(
            root,
            claim_id="T001",
            evidence_class="REVIEW_EXTERNAL",
            created_by_type="agent",
            created_by_id="review-recorder",
            establishes=["Named independent review completed"],
            does_not_establish=["Venue acceptance or publication"],
            source_revision="b" * 40,
            details_json=details,
            reviewer_type="human",
            reviewer_id="github:independent-reviewer",
            timestamp="2026-07-30T19:02:00Z",
        )
    )
    result = run_checks(root)
    assert result.ok, result.to_dict()
