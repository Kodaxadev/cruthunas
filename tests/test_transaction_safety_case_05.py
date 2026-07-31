from __future__ import annotations

from tests.transaction_safety_support import *

def test_default_source_revision_rechecks_head_before_apply(tmp_path: Path) -> None:
    root = _project(tmp_path)
    _register(root)
    _commit_fixture(root)
    plan = plan_evidence_add(
        root,
        claim_id="T001",
        evidence_class="REVIEW_INTERNAL",
        created_by_type="human",
        created_by_id="github:tester",
        establishes=["Internal review completed"],
        does_not_establish=["External review"],
        source_revision=None,
        timestamp="2026-07-30T19:02:00Z",
    )
    _git(root, "commit", "--allow-empty", "-m", "move head")

    with pytest.raises(TransactionError, match="Git HEAD changed"):
        apply_plan(plan)

    assert not (root / "audit/evidence/T001/E-T001-0002.yaml").exists()

