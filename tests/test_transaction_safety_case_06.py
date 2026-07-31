from __future__ import annotations

from tests.transaction_safety_support import *

def test_guard_recognizes_command_managed_records() -> None:
    from hooks.claude_guard import protected_record

    assert protected_record("claims/claims.yaml")
    assert protected_record(r"C:\repo\audit\proposals\T001.yaml")
    assert protected_record("audit/evidence/T001/E-T001-0001.yaml")
    assert protected_record("audit/transitions/T001/x.yaml")
    assert not protected_record("docs/proofs/T001.md")

