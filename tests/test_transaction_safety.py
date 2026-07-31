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



def test_transition_timestamp_collision_does_not_overwrite_history(tmp_path: Path) -> None:
    root = _project(tmp_path)
    _register(root)
    apply_plan(
        plan_evidence_add(
            root,
            claim_id="T001",
            evidence_class="REVIEW_INTERNAL",
            created_by_type="agent",
            created_by_id="audit-agent",
            establishes=["Internal audit completed"],
            does_not_establish=["External review"],
            source_revision="a" * 40,
            timestamp="2026-07-30T19:02:00Z",
        )
    )
    apply_plan(
        plan_claim_transition(
            root,
            claim_id="T001",
            verification_add=["INTERNAL_AUDIT"],
            reason="Internal audit recorded",
            requested_by="github:tester",
            approved_by_type="policy",
            approved_by_id="cruthunas/transition-v1",
            evidence_ids=["E-T001-0002"],
            timestamp="2026-07-30T19:03:00Z",
        )
    )
    before = {
        path.name: path.read_bytes()
        for path in (root / "audit/transitions/T001").glob("*.yaml")
    }
    with pytest.raises(TransactionError, match="must be later"):
        plan_claim_transition(
            root,
            claim_id="T001",
            verification_remove=["INTERNAL_AUDIT"],
            reason="Audit mark withdrawn",
            requested_by="github:tester",
            approved_by_type="policy",
            approved_by_id="cruthunas/transition-v1",
            evidence_ids=["E-T001-0002"],
            timestamp="2026-07-30T19:03:00Z",
        )
    after = {
        path.name: path.read_bytes()
        for path in (root / "audit/transitions/T001").glob("*.yaml")
    }
    assert after == before
    assert run_checks(root).ok


def test_guard_recognizes_command_managed_records() -> None:
    from hooks.claude_guard import protected_record

    assert protected_record("claims/claims.yaml")
    assert protected_record(r"C:\repo\audit\proposals\T001.yaml")
    assert protected_record("audit/evidence/T001/E-T001-0001.yaml")
    assert protected_record("audit/transitions/T001/x.yaml")
    assert not protected_record("docs/proofs/T001.md")


def test_apply_rolls_back_when_post_write_validation_fails(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from cruthunas import transaction_plan
    from cruthunas.models import CheckResult, Finding

    root = _project(tmp_path)
    plan = plan_claim_proposal(
        root,
        claim_id="T001",
        kind="THEOREM",
        statement="For every n in {1}, n = 1.",
        source_document="docs/proofs/T001.md",
        limitations=["Fixture only"],
        proposed_by="github:tester",
        timestamp="2026-07-30T19:00:00Z",
    )
    failure = CheckResult(
        root=str(root),
        findings=(Finding("fixture.failure", "forced", "claims/claims.yaml"),),
        claim_count=0,
        evidence_count=0,
        transition_count=0,
    )
    monkeypatch.setattr(transaction_plan, "run_checks", lambda _root: failure)
    with pytest.raises(TransactionError, match="post-write validation"):
        apply_plan(plan)
    assert not (root / "audit/proposals/T001.yaml").exists()


def test_concurrent_modification_is_not_overwritten(tmp_path: Path) -> None:
    root = _project(tmp_path)
    plan = plan_claim_proposal(
        root,
        claim_id="T001",
        kind="THEOREM",
        statement="For every n in {1}, n = 1.",
        source_document="docs/proofs/T001.md",
        limitations=["Fixture only"],
        proposed_by="github:tester",
        timestamp="2026-07-30T19:00:00Z",
    )
    competing = root / "audit/proposals/T001.yaml"
    _write(competing, "user-created content\n")
    with pytest.raises(TransactionError, match="Concurrent modification"):
        apply_plan(plan)
    assert competing.read_text(encoding="utf-8") == "user-created content\n"


def test_evidence_add_records_artifact_hash_and_environment(tmp_path: Path) -> None:
    root = _project(tmp_path)
    _register(root)
    artifact = root / "certificates/T001/result.json"
    artifact.parent.mkdir(parents=True, exist_ok=True)
    artifact.write_text('{"ok": true}\n', encoding="utf-8")
    environment = root / "experiments/T001/environment.json"
    environment.parent.mkdir(parents=True, exist_ok=True)
    environment.write_text('{"python": "3.13"}\n', encoding="utf-8")

    result = apply_plan(
        plan_evidence_add(
            root,
            claim_id="T001",
            evidence_class="COMPUTATION",
            created_by_type="human",
            created_by_id="github:tester",
            establishes=["Fixture computation completed"],
            does_not_establish=["Anything outside the fixture"],
            source_revision="a" * 40,
            artifacts=["certificates/T001/result.json"],
            commands=["python verify.py"],
            environment_json="experiments/T001/environment.json",
            timestamp="2026-07-30T19:02:00Z",
        )
    )
    evidence_id = result["evidence_ids"][0]
    record = yaml.safe_load(
        (root / f"audit/evidence/T001/{evidence_id}.yaml").read_text(encoding="utf-8")
    )
    assert record["artifacts"][0]["path"] == "certificates/T001/result.json"
    assert len(record["artifacts"][0]["sha256"]) == 64
    assert record["environment"] == {"python": "3.13"}
    assert record["commands"] == ["python verify.py"]
