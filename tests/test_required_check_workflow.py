from __future__ import annotations

from pathlib import Path

import yaml

ROOT = Path(__file__).parents[1]


def test_protected_policy_context_depends_on_both_operating_system_jobs() -> None:
    workflow = yaml.safe_load(
        (ROOT / ".github/workflows/reusable-policy.yml").read_text(encoding="utf-8")
    )
    jobs = workflow["jobs"]
    assert set(jobs["policy"]["needs"]) == {"linux", "windows", "python311"}
    assert jobs["policy"]["name"] == "policy"
    assert jobs["policy"]["if"] == "always()"
    assert jobs["linux"]["runs-on"] == "ubuntu-24.04"
    assert jobs["windows"]["runs-on"] == "windows-2025"
    assert jobs["python311"]["runs-on"] == "ubuntu-24.04"
    assert jobs["python311"]["steps"][1]["with"]["python-version"] == "3.11"
