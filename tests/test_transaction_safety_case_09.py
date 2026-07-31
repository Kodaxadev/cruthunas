from __future__ import annotations

from tests.transaction_safety_support import *

def test_registration_rejects_proposal_changed_after_preview(tmp_path: Path) -> None:
    root = _project(tmp_path)
    apply_plan(
        plan_claim_proposal(
            root,
            claim_id="T001",
            kind="THEOREM",
            statement="For every n in {1}, n = 1.",
            source_document="docs/proofs/T001.md",
            limitations=["Fixture only"],
            proposed_by="github:tester",
            timestamp="2026-07-30T19:00:00Z",
        )
    )
    plan = plan_claim_registration(
        root,
        proposal_path="audit/proposals/T001.yaml",
        created_by_type="human",
        created_by_id="github:tester",
        requested_by="github:tester",
        approved_by_type="policy",
        approved_by_id="cruthunas/claim-registration-v1",
        source_revision="a" * 40,
        timestamp="2026-07-30T19:01:00Z",
    )
    proposal_path = root / "audit/proposals/T001.yaml"
    proposal = yaml.safe_load(proposal_path.read_text(encoding="utf-8"))
    proposal["statement"] = "Changed after preview."
    proposal_path.write_text(yaml.safe_dump(proposal, sort_keys=False), encoding="utf-8")

    with pytest.raises(TransactionError, match="Transaction input changed"):
        apply_plan(plan)

    assert read_yaml(root / "claims/claims.yaml")["claims"] == []
    assert not (root / "audit/evidence/T001").exists()
    assert not (root / "audit/transitions/T001").exists()
