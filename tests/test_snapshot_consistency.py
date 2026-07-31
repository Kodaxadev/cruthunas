from __future__ import annotations

import subprocess
from pathlib import Path

import pytest
import yaml

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
        (tmp_path / "schemas" / source.name).write_text(source.read_text(encoding="utf-8"), encoding="utf-8")
    (tmp_path / "claims").mkdir()
    (tmp_path / "claims/schema.json").write_text((REPO_ROOT / "claims/schema.json").read_text(encoding="utf-8"), encoding="utf-8")
    _write(tmp_path / "claims/claims.yaml", "# ledger header\n\nschema_version: 1\nclaims: []\n")
    _write(tmp_path / "docs/proofs/T001.md", "# T001\n")
    return tmp_path


def _register(root: Path) -> None:
    apply_plan(plan_claim_proposal(root, claim_id="T001", kind="THEOREM", title="Fixture theorem", statement="For every n in {1}, n = 1.", scope="n in {1}", dependencies=[], source_document="docs/proofs/T001.md", limitations=["Fixture only"], proposed_by="github:tester", timestamp="2026-07-30T19:00:00Z"))
    apply_plan(plan_claim_registration(root, proposal_path="audit/proposals/T001.yaml", created_by_type="human", created_by_id="github:tester", requested_by="github:tester", approved_by_type="policy", approved_by_id="cruthunas/claim-registration-v1", source_revision="a" * 40, timestamp="2026-07-30T19:01:00Z"))


def _git(root: Path, *arguments: str) -> str:
    completed = subprocess.run(["git", "-C", str(root), *arguments], check=True, capture_output=True, text=True)
    return completed.stdout.strip()


def _commit_fixture(root: Path, message: str = "fixture") -> str:
    if not (root / ".git").exists():
        _git(root, "init")
        _git(root, "config", "user.name", "Fixture")
        _git(root, "config", "user.email", "fixture@example.invalid")
    files = [str(path.relative_to(root)) for path in sorted(root.rglob("*")) if path.is_file() and ".git" not in path.parts]
    _git(root, "add", "--", *files)
    _git(root, "commit", "-m", message)
    return _git(root, "rev-parse", "HEAD")

def test_proposal_uses_exact_ledger_snapshot_during_planning(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from cruthunas import claim_register

    root = _project(tmp_path)
    ledger_path = root / "claims/claims.yaml"
    original_timestamp = claim_register._timestamp

    def mutate_ledger(value: str | None) -> str:
        ledger_path.write_text(
            "# changed while planning\n\nschema_version: 1\nclaims: []\n",
            encoding="utf-8",
        )
        return original_timestamp(value)

    monkeypatch.setattr(claim_register, "_timestamp", mutate_ledger)
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

    with pytest.raises(TransactionError, match="Transaction input changed"):
        apply_plan(plan)

    assert not (root / "audit/proposals/T001.yaml").exists()


def test_registration_uses_exact_proposal_snapshot_during_planning(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from cruthunas import claim_register

    root = _project(tmp_path)
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
    proposal_path = root / "audit/proposals/T001.yaml"
    original_source_revision = claim_register._source_revision

    def mutate_proposal(current_root: Path, override: str | None) -> str:
        proposal = yaml.safe_load(proposal_path.read_text(encoding="utf-8"))
        proposal["statement"] = "Changed while registration was being planned."
        proposal_path.write_text(yaml.safe_dump(proposal, sort_keys=False), encoding="utf-8")
        return original_source_revision(current_root, override)

    monkeypatch.setattr(claim_register, "_source_revision", mutate_proposal)
    plan = plan_claim_registration(
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

    with pytest.raises(TransactionError, match="Transaction input changed"):
        apply_plan(plan)

    assert read_yaml(root / "claims/claims.yaml")["claims"] == []


def test_transition_uses_exact_evidence_snapshot_during_planning(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from cruthunas import claim_mutate

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
    evidence_path = root / "audit/evidence/T001/E-T001-0002.yaml"
    original_history = claim_mutate._transition_history

    def mutate_evidence(
        current_root: Path,
        claim_id: str,
        axis: str,
    ):
        evidence = yaml.safe_load(evidence_path.read_text(encoding="utf-8"))
        evidence["notes"] = "Changed while transition was being planned"
        evidence_path.write_text(yaml.safe_dump(evidence, sort_keys=False), encoding="utf-8")
        return original_history(current_root, claim_id, axis)

    monkeypatch.setattr(claim_mutate, "_transition_history", mutate_evidence)
    plan = plan_claim_transition(
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

    with pytest.raises(TransactionError, match="Transaction input changed"):
        apply_plan(plan)

    claim = read_yaml(root / "claims/claims.yaml")["claims"][0]
    assert claim["verification_statuses"] == ["UNCHECKED"]


def test_artifact_change_during_planning_invalidates_prospective_transaction(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from cruthunas import claim_mutate

    root = _project(tmp_path)
    _register(root)
    artifact = root / "certificates/T001/result.json"
    artifact.parent.mkdir(parents=True, exist_ok=True)
    artifact.write_text('{"value": 1}\n', encoding="utf-8")
    original_link = claim_mutate._link_evidence

    def mutate_artifact(claim: dict, evidence: dict) -> None:
        original_link(claim, evidence)
        artifact.write_text('{"value": 2}\n', encoding="utf-8")

    monkeypatch.setattr(claim_mutate, "_link_evidence", mutate_artifact)
    with pytest.raises(TransactionError, match="Prospective transaction violates"):
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
            timestamp="2026-07-30T19:02:00Z",
        )

    assert not (root / "audit/evidence/T001/E-T001-0002.yaml").exists()


def test_default_source_revision_rechecks_clean_worktree_before_apply(tmp_path: Path) -> None:
    root = _project(tmp_path)
    _register(root)
    _commit_fixture(root)
    plan = plan_evidence_add(
        root,
        claim_id="T001",
        evidence_class="REVIEW_INTERNAL",
        created_by_type="human",
        created_by_id="github:tester",
        establishes=["Internal review completed"],
        does_not_establish=["External review"],
        source_revision=None,
        timestamp="2026-07-30T19:02:00Z",
    )
    (root / "untracked-after-preview.txt").write_text("changed\n", encoding="utf-8")

    with pytest.raises(TransactionError, match="Working tree changed"):
        apply_plan(plan)

    assert not (root / "audit/evidence/T001/E-T001-0002.yaml").exists()
