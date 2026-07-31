from __future__ import annotations

from tests.transaction_safety_support import *

def test_evidence_add_records_complete_computation_contract(tmp_path: Path) -> None:
    root = _project(tmp_path)
    _register(root)
    payload = _computation_payload(root)
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
            timestamp="2026-07-30T19:02:00Z",
            **payload,
        )
    )
    evidence_id = result["evidence_ids"][0]
    record = yaml.safe_load(
        (root / f"audit/evidence/T001/{evidence_id}.yaml").read_text(encoding="utf-8")
    )
    assert record["artifacts"][0]["path"] == "certificates/T001/result.json"
    assert len(record["artifacts"][0]["sha256"]) == 64
    assert record["environment"]["interpreter"] == "Python 3.13"
    assert record["commands"] == ["python verify.py"]
    assert record["details"]["bounds"] == "n in [1, 1], inclusive"

