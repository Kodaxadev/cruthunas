from __future__ import annotations

from tests.transaction_safety_support import *

def test_transition_timestamp_collision_does_not_overwrite_history(tmp_path: Path) -> None:
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
    apply_plan(
        plan_claim_transition(
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
    )
    before = {
        path.name: path.read_bytes()
        for path in (root / "audit/transitions/T001").glob("*.yaml")
    }
    with pytest.raises(TransactionError, match="must be later"):
        plan_claim_transition(
            root,
            claim_id="T001",
            verification_remove=["INTERNAL_AUDIT"],
            reason="Audit mark withdrawn",
            requested_by="github:tester",
            approved_by_type="policy",
            approved_by_id="cruthunas/transition-v1",
            evidence_ids=["E-T001-0002"],
            timestamp="2026-07-30T19:03:00Z",
        )
    after = {
        path.name: path.read_bytes()
        for path in (root / "audit/transitions/T001").glob("*.yaml")
    }
    assert after == before
    assert run_checks(root).ok

