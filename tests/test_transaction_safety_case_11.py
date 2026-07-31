from __future__ import annotations

from tests.transaction_safety_support import *

def test_proposal_rejects_source_changed_after_preview_and_releases_lock(
    tmp_path: Path,
) -> None:
    from cruthunas.transaction_plan import _lock_path

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
    (root / "docs/proofs/T001.md").write_text(
        "# changed after preview\n", encoding="utf-8"
    )

    with pytest.raises(TransactionError, match="Transaction input changed"):
        apply_plan(plan)

    assert not (root / "audit/proposals/T001.yaml").exists()
    assert not _lock_path(root).exists()
