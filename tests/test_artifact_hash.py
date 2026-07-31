from __future__ import annotations

from pathlib import Path

import yaml

from cruthunas.policy import run_checks

REPO_ROOT = Path(__file__).parents[1]


def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def test_evidence_artifact_hash_mismatch_fails(tmp_path: Path) -> None:
    (tmp_path / "schemas").mkdir(parents=True)
    for source in (REPO_ROOT / "schemas").glob("*.json"):
        (tmp_path / "schemas" / source.name).write_text(source.read_text(encoding="utf-8"), encoding="utf-8")
    (tmp_path / "claims").mkdir()
    (tmp_path / "claims/schema.json").write_text((REPO_ROOT / "claims/schema.json").read_text(encoding="utf-8"), encoding="utf-8")
    _write(tmp_path / "docs/proofs/T001.md", "# T001\n")
    registration_id = "E-T001-0001"
    computation_id = "E-T001-0002"
    claim = {
        "id": "T001", "kind": "THEOREM", "title": "Finite statement",
        "statement": "For every n in {1}, n = 1.", "scope": "n in {1}",
        "epistemic_status": "OPEN", "verification_statuses": ["UNCHECKED"],
        "publication_status": "WORKING", "gate": 4, "dependencies": [],
        "evidence": [registration_id, computation_id],
        "source_document": "docs/proofs/T001.md", "proof_location": None,
        "computational_support": [computation_id], "formal_declarations": [],
        "external_reviews": [], "limitations": ["Fixture only"],
        "introduced_at": "2026-07-30T19:00:00Z", "updated_at": "2026-07-30T19:00:00Z",
    }
    _write(tmp_path / "claims/claims.yaml", yaml.safe_dump({"schema_version": 1, "claims": [claim]}, sort_keys=False))
    artifact = tmp_path / "certificates/T001/result.json"
    _write(artifact, '{"ok": true}\n')
    def evidence(evidence_id: str, evidence_class: str) -> dict:
        return {
            "schema_version": 1, "id": evidence_id, "claim_id": "T001",
            "class": evidence_class, "created_at": "2026-07-30T19:00:00Z",
            "created_by": {"type": "human", "id": "github:tester"},
            "establishes": ["Fixture evidence"],
            "does_not_establish": ["Anything outside this fixture"],
            "artifacts": [], "commands": [], "environment": None,
            "source_revision": "a" * 40, "notes": None,
        }
    registration = evidence(registration_id, "CLAIM_REGISTRATION")
    computation = evidence(computation_id, "COMPUTATION")
    computation["artifacts"] = [{"path": "certificates/T001/result.json", "sha256": "0" * 64}]
    _write(tmp_path / f"audit/evidence/T001/{registration_id}.yaml", yaml.safe_dump(registration, sort_keys=False))
    _write(tmp_path / f"audit/evidence/T001/{computation_id}.yaml", yaml.safe_dump(computation, sort_keys=False))
    transition = {
        "schema_version": 1, "claim_id": "T001", "axis": "gate",
        "from": 3, "to": 4, "requested_by": "github:tester",
        "approved_by": {"type": "policy", "id": "fixture-policy"},
        "evidence": [registration_id], "reason": "Fixture registration",
        "created_at": "2026-07-30T19:01:00Z",
    }
    _write(tmp_path / "audit/transitions/T001/20260730T190100Z-gate-4.yaml", yaml.safe_dump(transition, sort_keys=False))
    result = run_checks(tmp_path)
    assert "evidence.artifact_hash_mismatch" in {finding.code for finding in result.findings}
