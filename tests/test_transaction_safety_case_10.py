from __future__ import annotations

from tests.transaction_safety_support import *

def test_transition_rejects_evidence_changed_after_preview(tmp_path: Path) -> None:
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
    plan = plan_claim_transition(
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
    evidence_path = root / "audit/evidence/T001/E-T001-0002.yaml"
    evidence = yaml.safe_load(evidence_path.read_text(encoding="utf-8"))
    evidence["notes"] = "Changed after preview"
    evidence_path.write_text(yaml.safe_dump(evidence, sort_keys=False), encoding="utf-8")

    with pytest.raises(TransactionError, match="Transaction input changed"):
        apply_plan(plan)

    claim = read_yaml(root / "claims/claims.yaml")["claims"][0]
    assert claim["verification_statuses"] == ["UNCHECKED"]
