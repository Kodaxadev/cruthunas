from __future__ import annotations

from tests.transaction_safety_support import *

def test_concurrent_modification_is_not_overwritten(tmp_path: Path) -> None:
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
    competing = root / "audit/proposals/T001.yaml"
    _write(competing, "user-created content\n")
    with pytest.raises(TransactionError, match="Concurrent modification"):
        apply_plan(plan)
    assert competing.read_text(encoding="utf-8") == "user-created content\n"
