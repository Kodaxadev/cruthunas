from __future__ import annotations

from tests.transaction_safety_support import *

def test_apply_rolls_back_when_post_write_validation_fails(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from cruthunas import transaction_plan
    from cruthunas.models import CheckResult, Finding

    root = _project(tmp_path)
    plan = plan_claim_proposal(
        root,
        claim_id="T001",
        kind="THEOREM",
        statement="For every n in {1}, n = 1.",
        source_document="docs/proofs/T001.md",
        limitations=["Fixture only"],
        proposed_by="github:tester",
        timestamp="2026-07-30T19:00:00Z",
    )
    failure = CheckResult(
        root=str(root),
        findings=(Finding("fixture.failure", "forced", "claims/claims.yaml"),),
        claim_count=0,
        evidence_count=0,
        transition_count=0,
    )
    monkeypatch.setattr(transaction_plan, "run_checks", lambda _root: failure)
    with pytest.raises(TransactionError, match="post-write validation"):
        apply_plan(plan)
    assert not (root / "audit/proposals/T001.yaml").exists()
