from __future__ import annotations

from pathlib import Path

import yaml

from cruthunas.policy import run_checks


SCHEMA_ROOT = Path(__file__).parents[1] / "schemas"
CLAIMS_SCHEMA = Path(__file__).parents[1] / "claims" / "schema.json"


def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def _copy_schemas(root: Path) -> None:
    (root / "schemas").mkdir(parents=True)
    for source in SCHEMA_ROOT.glob("*.json"):
        target = root / "schemas" / source.name
        target.write_text(source.read_text(encoding="utf-8"), encoding="utf-8")
    (root / "claims").mkdir(parents=True)
    (root / "claims/schema.json").write_text(
        CLAIMS_SCHEMA.read_text(encoding="utf-8"),
        encoding="utf-8",
    )


def _claim(**updates):
    claim = {
        "id": "T001",
        "kind": "THEOREM",
        "title": "Finite statement",
        "statement": "For every n in {1}, n = 1.",
        "scope": "n in {1}",
        "epistemic_status": "OPEN",
        "verification_statuses": ["UNCHECKED"],
        "publication_status": "WORKING",
        "gate": 4,
        "dependencies": [],
        "evidence": [],
        "source_document": "docs/proofs/T001.md",
        "proof_location": None,
        "computational_support": [],
        "formal_declarations": [],
        "external_reviews": [],
        "limitations": ["Trivial fixture"],
        "introduced_at": "2026-07-30T19:00:00Z",
        "updated_at": "2026-07-30T19:00:00Z",
    }
    claim.update(updates)
    return claim


def _project(tmp_path: Path, claims: list[dict]) -> Path:
    _copy_schemas(tmp_path)
    _write(tmp_path / "docs/proofs/T001.md", "# T001\n")
    _write(
        tmp_path / "claims/claims.yaml",
        yaml.safe_dump(
            {"schema_version": 1, "claims": claims},
            sort_keys=False,
        ),
    )
    return tmp_path


def test_empty_ledger_is_valid(tmp_path: Path) -> None:
    result = run_checks(_project(tmp_path, []))
    assert result.ok, result.to_dict()


def test_dangling_dependency_fails(tmp_path: Path) -> None:
    result = run_checks(_project(tmp_path, [_claim(dependencies=["L999"])]))
    assert "claim.dangling_dependency" in {
        finding.code for finding in result.findings
    }


def test_external_review_requires_evidence(tmp_path: Path) -> None:
    result = run_checks(
        _project(
            tmp_path,
            [_claim(verification_statuses=["EXTERNAL_REVIEW"])],
        )
    )
    assert "claim.unsupported_verification" in {
        finding.code for finding in result.findings
    }


def test_valid_computational_claim(tmp_path: Path) -> None:
    evidence_id = "E-T001-0001"
    claim = _claim(
        epistemic_status="COMPUTATIONAL",
        verification_statuses=["INDEPENDENT_REPRODUCTION"],
        evidence=[evidence_id],
        computational_support=[evidence_id],
    )
    root = _project(tmp_path, [claim])
    evidence = {
        "schema_version": 1,
        "id": evidence_id,
        "claim_id": "T001",
        "class": "REPRODUCTION",
        "created_at": "2026-07-30T19:00:00Z",
        "created_by": {"type": "human", "id": "github:tester"},
        "establishes": ["The declared finite range reproduces"],
        "does_not_establish": ["Any universal statement"],
        "artifacts": [],
        "commands": ["python verify.py"],
        "environment": None,
        "source_revision": "a" * 40,
        "notes": None,
    }
    _write(
        root / f"audit/evidence/T001/{evidence_id}.yaml",
        yaml.safe_dump(evidence, sort_keys=False),
    )
    result = run_checks(root)
    assert result.ok, result.to_dict()


def test_project_manifest_rejects_moving_ref(tmp_path: Path) -> None:
    root = _project(tmp_path, [])
    manifest = {
        "schema_version": 1,
        "framework": {
            "repository": "Kodaxadev/cruthunas",
            "version": "main",
            "commit": "a" * 40,
        },
        "profile": "mathematics",
        "project": {
            "id": "fixture",
            "title": "Fixture",
            "maintainers": [{"github": "tester"}],
        },
        "canonical": {
            "claim_ledger": "claims/claims.yaml",
            "research_charter": "RESEARCH_CHARTER.md",
            "evidence_root": "audit/evidence",
            "transition_root": "audit/transitions",
            "release_manifest": "audit/evidence-manifest.yaml",
        },
        "policies": {},
    }
    _write(
        root / ".cruthunas/project.yaml",
        yaml.safe_dump(manifest, sort_keys=False),
    )
    result = run_checks(root)
    assert "project.moving_version" in {
        finding.code for finding in result.findings
    }


def test_adapter_sync_detects_drift(tmp_path: Path) -> None:
    from cruthunas.adapters import check_adapters, sync_adapters

    _write(
        tmp_path / "skills/example/SKILL.md",
        "---\nname: example\n---\n# Example\n",
    )
    sync_adapters(tmp_path)
    assert check_adapters(tmp_path) == []
    _write(tmp_path / ".claude/skills/example/SKILL.md", "drift\n")
    assert any("adapter drift" in item for item in check_adapters(tmp_path))


def test_command_guard_blocks_bulk_stage() -> None:
    from hooks.claude_guard import command_denial

    assert command_denial("git add -A")
    assert command_denial("npm test && git add .")
    assert command_denial("git add claims/claims.yaml") is None


def test_commit_message_contract() -> None:
    from hooks.commit_message import valid_message

    assert valid_message("policy: add validator")
    assert valid_message("transition(T018): HEURISTIC -> PROVED")
    assert not valid_message("update stuff")
