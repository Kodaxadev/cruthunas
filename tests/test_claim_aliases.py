from __future__ import annotations

import hashlib
from pathlib import Path

import pytest
import yaml

from cruthunas.bootstrap import plan_project_init
from cruthunas.claim_ids import legacy_canonical_id
from cruthunas.claim_register import plan_claim_proposal, plan_claim_registration
from cruthunas.evidence_policy import evidence_contract_errors
from cruthunas.models import read_yaml
from cruthunas.policy import run_checks
from cruthunas.transaction_plan import apply_plan
from cruthunas.transaction_types import TransactionError

FRAMEWORK_COMMIT = "3dd07da5534410b285a337110106bb65f9ab628e"


def _project(tmp_path: Path) -> Path:
    apply_plan(plan_project_init(
        tmp_path, mode="experimental", framework_repository="Kodaxadev/cruthunas",
        framework_commit=FRAMEWORK_COMMIT, framework_version=None,
        framework_release_manifest=None, profile="mathematics", project_id="fixture",
        project_title="Fixture", maintainer_github=["tester"],
    ))
    (tmp_path / "docs").mkdir()
    (tmp_path / "docs/source.md").write_text("# Source\n", encoding="utf-8")
    return tmp_path


def _propose(root: Path, claim_id: str, *, aliases: list[str] | None = None, dependencies: list[str] | None = None):
    return plan_claim_proposal(
        root, claim_id=claim_id, aliases=aliases or [], kind="COMPUTATIONAL_RESULT",
        title="Fixture", statement="A bounded fixture statement.", scope="fixture",
        dependencies=dependencies or [], source_document="docs/source.md",
        limitations=["Fixture only"], proposed_by="github:tester",
        timestamp="2026-07-31T18:00:00Z",
    )


def _register(root: Path, claim_id: str) -> None:
    apply_plan(plan_claim_registration(
        root, proposal_path=f"audit/proposals/{claim_id}.yaml",
        created_by_type="human", created_by_id="github:tester",
        requested_by="github:tester", approved_by_type="policy",
        approved_by_id="cruthunas/claim-registration-v1", source_revision="a" * 40,
        timestamp="2026-07-31T18:01:00Z",
    ))


def test_legacy_k4_maps_to_k004() -> None:
    assert legacy_canonical_id("K4") == "K004"
    assert legacy_canonical_id(" k4 ") == "K004"
    assert legacy_canonical_id("CJ1") is None


def test_alias_is_normalized_and_preserved_through_registration(tmp_path: Path) -> None:
    root = _project(tmp_path)
    apply_plan(_propose(root, "K004", aliases=[" k4 "]))
    proposal = read_yaml(root / "audit/proposals/K004.yaml")
    assert proposal["aliases"] == ["K4"]
    _register(root, "K004")
    ledger = read_yaml(root / "claims/claims.yaml")
    assert ledger["claims"][0]["id"] == "K004"
    assert ledger["claims"][0]["aliases"] == ["K4"]
    assert run_checks(root).ok


def test_duplicate_aliases_are_rejected_after_normalization(tmp_path: Path) -> None:
    root = _project(tmp_path)
    with pytest.raises(TransactionError, match="Duplicate claim alias"):
        _propose(root, "K004", aliases=["K4", " k4 "])


def test_alias_cannot_duplicate_its_canonical_id(tmp_path: Path) -> None:
    root = _project(tmp_path)
    with pytest.raises(TransactionError, match="duplicates its canonical"):
        _propose(root, "K004", aliases=["K004"])


def test_alias_to_existing_canonical_id_collision_is_rejected(tmp_path: Path) -> None:
    root = _project(tmp_path)
    apply_plan(_propose(root, "T001"))
    _register(root, "T001")
    with pytest.raises(TransactionError, match="collides with canonical"):
        _propose(root, "K004", aliases=["T001"])


def test_new_canonical_id_cannot_collide_with_existing_alias(tmp_path: Path) -> None:
    root = _project(tmp_path)
    apply_plan(_propose(root, "T001", aliases=["K005"]))
    _register(root, "T001")
    with pytest.raises(TransactionError, match="collides with existing alias"):
        _propose(root, "K005")


def test_alias_cannot_be_assigned_to_two_claims(tmp_path: Path) -> None:
    root = _project(tmp_path)
    apply_plan(_propose(root, "K004", aliases=["K4"]))
    _register(root, "K004")
    with pytest.raises(TransactionError, match="already assigned"):
        _propose(root, "K005", aliases=["k4"])


def test_alias_is_not_accepted_as_dependency_substitute(tmp_path: Path) -> None:
    root = _project(tmp_path)
    apply_plan(_propose(root, "K004", aliases=["K4"]))
    _register(root, "K004")
    with pytest.raises(TransactionError, match="canonical claim ID"):
        _propose(root, "T001", dependencies=["K4"])


def test_whole_repository_checker_rejects_alias_collisions(tmp_path: Path) -> None:
    root = _project(tmp_path)
    ledger = {
        "schema_version": 1,
        "claims": [
            {
                "id": claim_id, "aliases": ["K4"], "kind": "COMPUTATIONAL_RESULT",
                "statement": "Fixture", "scope": "fixture", "epistemic_status": "OPEN",
                "verification_statuses": ["UNCHECKED"], "publication_status": "WORKING",
                "gate": 4, "dependencies": [], "evidence": [],
                "source_document": "docs/source.md", "proof_location": None,
                "computational_support": [], "formal_declarations": [],
                "external_reviews": [], "limitations": ["Fixture"],
                "introduced_at": "2026-07-31T18:00:00Z",
                "updated_at": "2026-07-31T18:00:00Z",
            }
            for claim_id in ("K004", "K005")
        ],
    }
    (root / "claims/claims.yaml").write_text(yaml.safe_dump(ledger, sort_keys=False), encoding="utf-8")
    result = run_checks(root)
    assert "claim.alias_collision" in {item.code for item in result.findings}


def _computational_record(evidence_class: str, creator_type: str) -> dict:
    artifact = b"{}\n"
    details = {
        "algorithm": "fixture", "bounds": "fixture", "arithmetic": "exact",
        "inputs": ["fixture"], "input_hashes": [hashlib.sha256(artifact).hexdigest()],
        "outputs": ["fixture"], "output_hashes": [hashlib.sha256(artifact).hexdigest()],
        "runtime": "0s", "resources": "fixture",
    }
    if evidence_class in {"REPRODUCTION", "REVIEW_EXTERNAL"}:
        details = {
            "independent": True, "relationship_to_originator": "none",
            "inputs_received": ["statement"], "saw_original_work": False,
            "implementation_boundary": "separate", "dependency_boundary": "separate",
            "result": "agreed", "disagreements": ["none"],
        }
    record = {
        "class": evidence_class,
        "created_by": {"type": creator_type, "id": "agent:test" if creator_type == "agent" else "github:test"},
        "commands": ["python fixture.py"],
        "artifacts": [{"path": "fixture.json", "sha256": hashlib.sha256(artifact).hexdigest()}],
        "environment": {
            "interpreter": "CPython 3.13", "dependencies": ["none"],
            "operating_system": "fixture", "locale": "C", "timezone": "UTC",
            "environment_variables": {"PYTHONHASHSEED": "0"}, "random_seeds": [0],
        },
        "details": details,
    }
    if evidence_class == "REVIEW_EXTERNAL":
        record["reviewer"] = {"type": "human", "id": "github:reviewer"}
    return record


def test_agent_created_computation_is_valid_provenance() -> None:
    errors = evidence_contract_errors(_computational_record("COMPUTATION", "agent"))
    assert not any("provenance only" in item for item in errors)


def test_agent_created_reproduction_cannot_establish_independence() -> None:
    errors = evidence_contract_errors(_computational_record("REPRODUCTION", "agent"))
    assert any("provenance only" in item and "independent reproduction" in item for item in errors)


def test_agent_created_external_review_cannot_establish_review() -> None:
    errors = evidence_contract_errors(_computational_record("REVIEW_EXTERNAL", "agent"))
    assert any("provenance only" in item and "external review" in item for item in errors)
