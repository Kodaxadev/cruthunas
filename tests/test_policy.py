from __future__ import annotations

import hashlib
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


def _evidence(evidence_id: str, evidence_class: str) -> dict:
    return {
        "schema_version": 1,
        "id": evidence_id,
        "claim_id": "T001",
        "class": evidence_class,
        "created_at": "2026-07-30T19:00:00Z",
        "created_by": {"type": "human", "id": "github:tester"},
        "establishes": [f"Fixture evidence class {evidence_class}"],
        "does_not_establish": ["Anything outside this fixture"],
        "artifacts": [],
        "commands": [],
        "environment": None,
        "source_revision": "a" * 40,
        "notes": None,
    }


def _transition(axis: str, before, after, evidence_id: str, timestamp: str) -> dict:
    return {
        "schema_version": 1,
        "claim_id": "T001",
        "axis": axis,
        "from": before,
        "to": after,
        "requested_by": "github:tester",
        "approved_by": {"type": "policy", "id": "fixture-policy"},
        "evidence": [evidence_id],
        "reason": "Fixture transition",
        "created_at": timestamp,
    }


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
    registration_id = "E-T001-0001"
    reproduction_id = "E-T001-0002"
    claim = _claim(
        epistemic_status="COMPUTATIONAL",
        verification_statuses=["INDEPENDENT_REPRODUCTION"],
        evidence=[registration_id, reproduction_id],
        computational_support=[reproduction_id],
        updated_at="2026-07-30T19:03:00Z",
    )
    root = _project(tmp_path, [claim])

    artifact_bytes = b'{"ok": true}\n'
    artifact_path = "certificates/T001/reproduction.json"
    artifact = root / artifact_path
    artifact.parent.mkdir(parents=True, exist_ok=True)
    artifact.write_bytes(artifact_bytes)

    registration = _evidence(registration_id, "CLAIM_REGISTRATION")
    registration["created_at"] = "2026-07-30T19:01:00Z"

    reproduction = _evidence(reproduction_id, "REPRODUCTION")
    reproduction.update(
        {
            "created_at": "2026-07-30T19:02:00Z",
            "created_by": {
                "type": "human",
                "id": "github:independent-tester",
            },
            "artifacts": [
                {
                    "path": artifact_path,
                    "sha256": hashlib.sha256(artifact_bytes).hexdigest(),
                }
            ],
            "commands": ["python independent/reproduce.py"],
            "environment": {
                "interpreter": "CPython 3.13",
                "dependencies": ["PyYAML 6.0.3"],
                "operating_system": "fixture",
                "locale": "C.UTF-8",
                "timezone": "UTC",
                "environment_variables": {"PYTHONHASHSEED": "0"},
                "random_seeds": [0],
            },
            "details": {
                "independent": True,
                "relationship_to_originator": "No collaboration",
                "inputs_received": ["Registered claim statement"],
                "saw_original_work": False,
                "implementation_boundary": "Independent fixture implementation",
                "dependency_boundary": "No project implementation imports",
                "result": "Reproduced",
                "disagreements": ["None"],
            },
        }
    )

    for evidence_id, record in (
        (registration_id, registration),
        (reproduction_id, reproduction),
    ):
        _write(
            root / f"audit/evidence/T001/{evidence_id}.yaml",
            yaml.safe_dump(record, sort_keys=False),
        )

    transitions = (
        (
            "20260730T190100Z-gate-4.yaml",
            _transition("gate", 3, 4, registration_id, "2026-07-30T19:01:00Z"),
        ),
        (
            "20260730T190200Z-epistemic.yaml",
            _transition(
                "epistemic",
                "OPEN",
                "COMPUTATIONAL",
                reproduction_id,
                "2026-07-30T19:02:00Z",
            ),
        ),
        (
            "20260730T190300Z-verification.yaml",
            _transition(
                "verification",
                ["UNCHECKED"],
                ["INDEPENDENT_REPRODUCTION"],
                reproduction_id,
                "2026-07-30T19:03:00Z",
            ),
        ),
    )
    for name, transition in transitions:
        _write(
            root / f"audit/transitions/T001/{name}",
            yaml.safe_dump(transition, sort_keys=False),
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


def test_unpinned_action_fails(tmp_path: Path) -> None:
    root = _project(tmp_path, [])
    _write(
        root / ".github/workflows/bad.yml",
        "name: bad\non: push\njobs:\n  bad:\n    runs-on: ubuntu-latest\n    steps:\n      - uses: actions/checkout@v4\n",
    )
    result = run_checks(root)
    assert "workflow.unpinned_action" in {
        finding.code for finding in result.findings
    }


def test_independent_verifier_cannot_import_project(tmp_path: Path) -> None:
    root = _project(tmp_path, [])
    _write(root / "src/projectcore/__init__.py", "")
    _write(root / "independent/check.py", "import projectcore\n")
    result = run_checks(root)
    assert "independent.project_import" in {
        finding.code for finding in result.findings
    }
