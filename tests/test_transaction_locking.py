from __future__ import annotations

import hashlib
import json
import os
import time
from pathlib import Path

import pytest

from cruthunas import transaction_plan
from cruthunas.transaction_types import PlannedWrite, TransactionError, TransactionPlan
from cruthunas.transactions import apply_plan, plan_claim_proposal

REPO_ROOT = Path(__file__).parents[1]


def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def _project(tmp_path: Path) -> Path:
    (tmp_path / "schemas").mkdir(parents=True)
    for source in (REPO_ROOT / "schemas").glob("*.json"):
        (tmp_path / "schemas" / source.name).write_text(
            source.read_text(encoding="utf-8"), encoding="utf-8"
        )
    (tmp_path / "claims").mkdir()
    (tmp_path / "claims/schema.json").write_text(
        (REPO_ROOT / "claims/schema.json").read_text(encoding="utf-8"),
        encoding="utf-8",
    )
    _write(tmp_path / "claims/claims.yaml", "schema_version: 1\nclaims: []\n")
    _write(tmp_path / "docs/proofs/T001.md", "# T001\n")
    return tmp_path


def _proposal_plan(root: Path):
    return plan_claim_proposal(
        root,
        claim_id="T001",
        kind="THEOREM",
        statement="For every n in {1}, n = 1.",
        source_document="docs/proofs/T001.md",
        limitations=["Fixture only"],
        proposed_by="github:tester",
        timestamp="2026-07-30T19:00:00Z",
    )


def test_stale_dead_process_lock_is_recovered(tmp_path: Path) -> None:
    root = _project(tmp_path)
    lock = transaction_plan._lock_path(root)
    lock.write_text(
        json.dumps({"pid": 2147483647, "root": str(root.resolve()), "token": "stale"}),
        encoding="utf-8",
    )
    apply_plan(_proposal_plan(root))
    assert (root / "audit/proposals/T001.yaml").is_file()
    assert not lock.exists()


def test_live_process_lock_is_not_removed(tmp_path: Path) -> None:
    root = _project(tmp_path)
    lock = transaction_plan._lock_path(root)
    lock.write_text(
        json.dumps({"pid": os.getpid(), "root": str(root.resolve()), "token": "live"}),
        encoding="utf-8",
    )
    try:
        with pytest.raises(TransactionError, match="transaction is active"):
            apply_plan(_proposal_plan(root))
        assert lock.exists()
    finally:
        lock.unlink(missing_ok=True)


def test_fresh_malformed_lock_is_treated_as_active(tmp_path: Path) -> None:
    root = _project(tmp_path)
    lock = transaction_plan._lock_path(root)
    lock.write_text("", encoding="utf-8")
    try:
        with pytest.raises(TransactionError, match="transaction is active"):
            apply_plan(_proposal_plan(root))
        assert lock.exists()
    finally:
        lock.unlink(missing_ok=True)


def test_old_malformed_lock_is_recovered(tmp_path: Path) -> None:
    root = _project(tmp_path)
    lock = transaction_plan._lock_path(root)
    lock.write_text("{", encoding="utf-8")
    old = time.time() - transaction_plan._MALFORMED_LOCK_GRACE_SECONDS - 1.0
    os.utime(lock, (old, old))

    apply_plan(_proposal_plan(root))

    assert (root / "audit/proposals/T001.yaml").is_file()
    assert not lock.exists()


def test_target_is_rechecked_after_backup_before_replace(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root = tmp_path
    target = root / "claims/claims.yaml"
    original = b"schema_version: 1\nclaims: []\n"
    concurrent = b"schema_version: 1\nclaims:\n- concurrent: true\n"
    replacement = b"schema_version: 1\nclaims:\n- replacement: true\n"
    target.parent.mkdir(parents=True)
    target.write_bytes(original)
    expected = hashlib.sha256(original).hexdigest()
    plan = TransactionPlan(
        root,
        "test.concurrent-recheck",
        (),
        (PlannedWrite("claims/claims.yaml", replacement, expected),),
        None,
        {},
    )
    original_copy = transaction_plan.shutil.copy2

    def mutate_after_backup(source, destination, *args, **kwargs):
        result = original_copy(source, destination, *args, **kwargs)
        target.write_bytes(concurrent)
        return result

    monkeypatch.setattr(transaction_plan.shutil, "copy2", mutate_after_backup)
    with pytest.raises(TransactionError, match="Concurrent modification"):
        apply_plan(plan)
    assert target.read_bytes() == concurrent
