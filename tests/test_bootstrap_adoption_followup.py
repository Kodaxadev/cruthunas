from __future__ import annotations

from pathlib import Path

import pytest

from cruthunas.adoption import adoption_gap_report
from cruthunas.bootstrap import plan_project_init
from cruthunas.transaction_types import TransactionError

FRAMEWORK_COMMIT = "3dd07da5534410b285a337110106bb65f9ab628e"


def _plan(root: Path, **updates):
    values = {
        "mode": "experimental",
        "framework_repository": "Kodaxadev/cruthunas",
        "framework_commit": FRAMEWORK_COMMIT,
        "framework_version": None,
        "framework_release_manifest": None,
        "profile": "mathematics",
        "project_id": "fixture",
        "project_title": "Fixture Project",
        "maintainer_github": ["tester"],
    }
    values.update(updates)
    return plan_project_init(root, **values)


def test_adoption_report_finds_unstructured_independence_claim_in_status_document(
    tmp_path: Path,
) -> None:
    status = tmp_path / "docs/theorem-status.md"
    status.parent.mkdir(parents=True)
    status.write_text(
        "K4 was checked by 3 independent implementations.\n",
        encoding="utf-8",
    )
    report = adoption_gap_report(tmp_path)
    matches = [
        gap
        for gap in report.gaps
        if gap.code == "identity.unstructured_assertion"
        and gap.path == "docs/theorem-status.md"
    ]
    assert len(matches) == 1
    assert matches[0].automatic is False


def test_experimental_mode_rejects_moving_commit_reference(tmp_path: Path) -> None:
    with pytest.raises(TransactionError, match="exact 40-character"):
        _plan(tmp_path, framework_commit="main")


def test_released_mode_rejects_ref_namespace_version(tmp_path: Path) -> None:
    release = tmp_path / "framework-release.json"
    release.write_text("{}", encoding="utf-8")
    with pytest.raises(TransactionError, match="Moving framework version"):
        _plan(
            tmp_path,
            mode="released",
            framework_version="refs/heads/v1.0.0",
            framework_release_manifest="framework-release.json",
        )


def test_adoption_report_handles_malformed_project_manifest_deterministically(
    tmp_path: Path,
) -> None:
    project = tmp_path / ".cruthunas/project.yaml"
    project.parent.mkdir(parents=True)
    schema = tmp_path / "schemas/project-v1.json"
    schema.parent.mkdir(parents=True)
    schema.write_text(
        (Path(__file__).parents[1] / "schemas/project-v1.json").read_text(encoding="utf-8"),
        encoding="utf-8",
    )
    project.write_text("framework: []\nmode: released\n", encoding="utf-8")
    report = adoption_gap_report(tmp_path)
    codes = {gap.code for gap in report.gaps}
    assert "schema.invalid" in codes
    assert report.to_dict() == adoption_gap_report(tmp_path).to_dict()
