from __future__ import annotations

from tests.transaction_safety_support import *

def test_default_source_revision_rejects_dirty_worktree(tmp_path: Path) -> None:
    root = _project(tmp_path)
    _register(root)
    _commit_fixture(root)
    (root / "docs/proofs/T001.md").write_text("# changed\n", encoding="utf-8")

    with pytest.raises(TransactionError, match="Working tree is dirty"):
        plan_evidence_add(
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

