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


def test_cli_dry_run_writes_nothing(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    root = _project(tmp_path)
    code = main(
        [
            "claim",
            "propose",
            "--root",
            str(root),
            "--id",
            "T001",
            "--kind",
            "THEOREM",
            "--statement",
            "For every n in {1}, n = 1.",
            "--source-document",
            "docs/proofs/T001.md",
            "--limitation",
            "Fixture only",
            "--proposed-by",
            "github:tester",
            "--timestamp",
            "2026-07-30T19:00:00Z",
            "--dry-run",
            "--json",
        ]
    )
    assert code == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["applied"] is False
    assert not (root / "audit/proposals/T001.yaml").exists()


def test_cli_declined_confirmation_writes_nothing(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root = _project(tmp_path)
    monkeypatch.setattr(builtins, "input", lambda _prompt: "no")
    code = main(
        [
            "claim",
            "propose",
            "--root",
            str(root),
            "--id",
            "T001",
            "--kind",
            "THEOREM",
            "--statement",
            "For every n in {1}, n = 1.",
            "--source-document",
            "docs/proofs/T001.md",
            "--limitation",
            "Fixture only",
            "--proposed-by",
            "github:tester",
            "--timestamp",
            "2026-07-30T19:00:00Z",
        ]
    )
    assert code == 0
    assert not (root / "audit/proposals/T001.yaml").exists()


def test_registration_rejects_same_human_requester_and_approver(tmp_path: Path) -> None:
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
    with pytest.raises(TransactionError, match="sole human registration approver"):
        plan_claim_registration(
            root,
            proposal_path="audit/proposals/T001.yaml",
            created_by_type="human",
            created_by_id="github:tester",
            requested_by="github:tester",
            approved_by_type="human",
            approved_by_id="github:tester",
            source_revision="a" * 40,
            timestamp="2026-07-30T19:01:00Z",
        )
