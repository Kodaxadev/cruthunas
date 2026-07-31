from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest
import yaml

from cruthunas.adoption import adoption_gap_report
from cruthunas.bootstrap import plan_project_init
from cruthunas.cli import main
from cruthunas.models import CheckResult, Finding, read_yaml
from cruthunas.policy import run_checks
from cruthunas.transaction_plan import apply_plan
from cruthunas.transaction_types import TransactionError

FRAMEWORK_COMMIT = "3dd07da5534410b285a337110106bb65f9ab628e"


def _kwargs(**updates):
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
    return values


def _plan(root: Path, **updates):
    return plan_project_init(root, **_kwargs(**updates))


def test_init_dry_run_json_writes_nothing(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    code = main([
        "init", "--root", str(tmp_path), "--mode", "experimental",
        "--framework-commit", FRAMEWORK_COMMIT, "--project-id", "fixture",
        "--project-title", "Fixture Project", "--maintainer-github", "tester",
        "--dry-run", "--json",
    ])
    assert code == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["operation"] == "project.init"
    assert payload["applied"] is False
    assert payload["mode"] == "experimental"
    assert payload["conformance"] == "non-conformant"
    assert payload["validation_profile"] == "bootstrap"
    assert not (tmp_path / ".cruthunas/project.yaml").exists()


def test_init_applies_minimum_structure_and_full_policy_passes(tmp_path: Path) -> None:
    result = apply_plan(_plan(tmp_path))
    assert result["applied"] is True
    expected = {
        ".cruthunas/project.yaml", "claims/claims.yaml", "claims/schema.json",
        "RESEARCH_CHARTER.md", "schemas/project-v1.json",
        "schemas/claim-proposal-v1.json", "schemas/evidence-v1.json",
        "schemas/transition-v1.json", "schemas/exemption-v1.json",
        "schemas/framework-release-v1.json",
    }
    assert set(result["writes"]) == expected
    manifest = read_yaml(tmp_path / ".cruthunas/project.yaml")
    assert manifest["mode"] == "experimental"
    assert manifest["conformance"] == "non-conformant"
    assert manifest["framework"] == {
        "repository": "Kodaxadev/cruthunas", "commit": FRAMEWORK_COMMIT,
    }
    policy = run_checks(tmp_path)
    assert policy.ok, policy.to_dict()
    assert adoption_gap_report(tmp_path).ok


def test_repeated_initialization_is_refused(tmp_path: Path) -> None:
    apply_plan(_plan(tmp_path))
    with pytest.raises(TransactionError, match="refuses to overwrite"):
        _plan(tmp_path)


def test_partial_existing_structure_is_refused(tmp_path: Path) -> None:
    target = tmp_path / "claims/claims.yaml"
    target.parent.mkdir(parents=True)
    target.write_text("legacy: true\n", encoding="utf-8")
    with pytest.raises(TransactionError, match="refuses to overwrite") as caught:
        _plan(tmp_path)
    assert "claims/claims.yaml" in caught.value.details["conflicts"]
    assert target.read_text(encoding="utf-8") == "legacy: true\n"


def test_conflicting_destination_directory_is_refused(tmp_path: Path) -> None:
    (tmp_path / "schemas/project-v1.json").mkdir(parents=True)
    with pytest.raises(TransactionError, match="refuses to overwrite"):
        _plan(tmp_path)


def test_release_manifest_path_traversal_is_refused(tmp_path: Path) -> None:
    outside = tmp_path.parent / "release.json"
    outside.write_text("{}", encoding="utf-8")
    with pytest.raises(TransactionError, match="escapes"):
        _plan(tmp_path, mode="released", framework_version="v1.0.0", framework_release_manifest="../release.json")


def test_stale_initialization_target_is_rejected(tmp_path: Path) -> None:
    plan = _plan(tmp_path)
    target = tmp_path / "claims/claims.yaml"
    target.parent.mkdir(parents=True)
    target.write_text("concurrent: true\n", encoding="utf-8")
    with pytest.raises(TransactionError, match="Concurrent modification"):
        apply_plan(plan)
    assert target.read_text(encoding="utf-8") == "concurrent: true\n"
    assert not (tmp_path / ".cruthunas/project.yaml").exists()


def test_initialization_rolls_back_after_post_write_failure(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    plan = _plan(tmp_path)
    failure = CheckResult(
        root=str(tmp_path),
        findings=(Finding("project.synthetic_failure", "synthetic", ".cruthunas/project.yaml"),),
        claim_count=0, evidence_count=0, transition_count=0,
    )
    monkeypatch.setattr("cruthunas.transaction_plan.run_checks", lambda _root: failure)
    with pytest.raises(TransactionError, match="post-write validation"):
        apply_plan(plan)
    for item in plan.writes:
        assert not (tmp_path / item.path).exists()


def test_experimental_mode_rejects_release_semantics(tmp_path: Path) -> None:
    with pytest.raises(TransactionError, match="cannot claim"):
        _plan(tmp_path, framework_version="v1.0.0")


def test_released_mode_requires_release_attestation(tmp_path: Path) -> None:
    with pytest.raises(TransactionError, match="release-manifest"):
        _plan(tmp_path, mode="released", framework_version="v1.0.0")


def test_released_mode_rejects_moving_framework_version(tmp_path: Path) -> None:
    (tmp_path / "framework-release.json").write_text("{}", encoding="utf-8")
    with pytest.raises(TransactionError, match="Moving framework version"):
        _plan(tmp_path, mode="released", framework_version="main", framework_release_manifest="framework-release.json")


def test_released_mode_rejects_mismatched_release_attestation(tmp_path: Path) -> None:
    release = {
        "schema_version": 1,
        "framework": {"repository": "Kodaxadev/cruthunas", "version": "v1.0.0", "commit": "a" * 40},
        "released_at": "2026-07-31T18:00:00Z",
    }
    (tmp_path / "framework-release.json").write_text(json.dumps(release), encoding="utf-8")
    with pytest.raises(TransactionError, match="does not match"):
        _plan(tmp_path, mode="released", framework_version="v1.0.0", framework_release_manifest="framework-release.json")


def test_released_mode_requires_and_preserves_exact_release_evidence(tmp_path: Path) -> None:
    release = {
        "schema_version": 1,
        "framework": {"repository": "Kodaxadev/cruthunas", "version": "v1.0.0", "commit": FRAMEWORK_COMMIT},
        "released_at": "2026-07-31T18:00:00Z",
        "release_url": "https://example.invalid/releases/v1.0.0",
    }
    release_path = tmp_path / "framework-release.json"
    release_bytes = json.dumps(release, sort_keys=True).encode("utf-8")
    release_path.write_bytes(release_bytes)
    apply_plan(_plan(tmp_path, mode="released", framework_version="v1.0.0", framework_release_manifest="framework-release.json"))
    manifest = read_yaml(tmp_path / ".cruthunas/project.yaml")
    assert manifest["mode"] == "released"
    assert manifest["conformance"] == "not-claimed"
    assert manifest["framework"]["release"] == {
        "manifest": "framework-release.json", "sha256": hashlib.sha256(release_bytes).hexdigest(),
    }
    assert run_checks(tmp_path).ok


def test_adoption_gap_report_is_deterministic_and_non_mutating(tmp_path: Path) -> None:
    (tmp_path / "docs").mkdir()
    (tmp_path / "docs/ledger.md").write_text("Claims K4 and CJ1.\n", encoding="utf-8")
    (tmp_path / ".github/workflows").mkdir(parents=True)
    (tmp_path / ".github/workflows/test.yml").write_text(
        "steps:\n  - uses: actions/checkout@v4\ncontainer:\n  image: python:3.13\n", encoding="utf-8"
    )
    (tmp_path / "Dockerfile").write_text("FROM python:3.13\n", encoding="utf-8")
    (tmp_path / "skills/example").mkdir(parents=True)
    (tmp_path / "skills/example/SKILL.md").write_text("# Example\n", encoding="utf-8")
    evidence = tmp_path / "audit/evidence/T001/legacy.yaml"
    evidence.parent.mkdir(parents=True)
    evidence.write_text(yaml.safe_dump({"class": "REPRODUCTION", "details": {}}), encoding="utf-8")
    (tmp_path / "audit/evidence-manifest.md").write_text("# Historical manifest\n", encoding="utf-8")
    before = {str(path.relative_to(tmp_path)): path.read_bytes() for path in tmp_path.rglob("*") if path.is_file()}
    first = adoption_gap_report(tmp_path).to_dict()
    second = adoption_gap_report(tmp_path).to_dict()
    assert first == second
    codes = {gap["code"] for gap in first["gaps"]}
    assert {
        "structure.missing", "claim_id.incompatible", "workflow.unpinned_action",
        "workflow.unpinned_container", "container.unpinned_image", "identity.creator_missing",
        "independence.metadata_missing", "adapter.manifest_absent", "migration.record_manual",
    }.issubset(codes)
    by_alias = {gap["details"]["alias"]: gap for gap in first["gaps"] if gap["code"] == "claim_id.incompatible"}
    assert by_alias["K4"]["automatic"] is True
    assert by_alias["K4"]["details"]["suggested_canonical"] == "K004"
    assert by_alias["CJ1"]["automatic"] is False
    after = {str(path.relative_to(tmp_path)): path.read_bytes() for path in tmp_path.rglob("*") if path.is_file()}
    assert after == before


def test_adoption_gap_cli_json_reports_gaps_without_writing(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    code = main(["adoption", "gaps", "--root", str(tmp_path), "--json"])
    assert code == 1
    payload = json.loads(capsys.readouterr().out)
    assert payload["ok"] is False
    assert payload["summary"]["gaps"] > 0
    assert list(tmp_path.iterdir()) == []


def test_adoption_report_distinguishes_adapter_drift(tmp_path: Path) -> None:
    from cruthunas.adapters import sync_adapters

    skill = tmp_path / "skills/example/SKILL.md"
    skill.parent.mkdir(parents=True)
    skill.write_text("---\nname: example\n---\n# Example\n", encoding="utf-8")
    sync_adapters(tmp_path)
    (tmp_path / ".claude/skills/example/SKILL.md").write_text("drift\n", encoding="utf-8")
    codes = {gap.code for gap in adoption_gap_report(tmp_path).gaps}
    assert "adapter.drift" in codes
    assert "adapter.manifest_absent" not in codes
