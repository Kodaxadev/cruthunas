from __future__ import annotations

from tests.transaction_safety_support import *

def test_evidence_add_rejects_artifact_changed_after_preview(tmp_path: Path) -> None:
    root = _project(tmp_path)
    _register(root)
    payload = _computation_payload(root)
    plan = plan_evidence_add(
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
    (root / "certificates/T001/result.json").write_text(
        '{"value": 2}\n', encoding="utf-8"
    )

    with pytest.raises(TransactionError, match="Transaction input changed"):
        apply_plan(plan)

    claim = read_yaml(root / "claims/claims.yaml")["claims"][0]
    assert claim["evidence"] == ["E-T001-0001"]
    assert not (root / "audit/evidence/T001/E-T001-0002.yaml").exists()

