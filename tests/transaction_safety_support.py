from __future__ import annotations

import json

import subprocess

from pathlib import Path

import pytest

import yaml

from cruthunas.models import read_yaml

from cruthunas.policy import run_checks

from cruthunas.transactions import (
    TransactionError,
    apply_plan,
    plan_claim_proposal,
    plan_claim_registration,
    plan_claim_transition,
    plan_evidence_add,
)


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
    _write(
        tmp_path / "claims/claims.yaml",
        "# ledger header\n\nschema_version: 1\nclaims: []\n",
    )
    _write(tmp_path / "docs/proofs/T001.md", "# T001\n")
    return tmp_path


def _register(root: Path) -> None:
    apply_plan(
        plan_claim_proposal(
            root,
            claim_id="T001",
            kind="THEOREM",
            title="Fixture theorem",
            statement="For every n in {1}, n = 1.",
            scope="n in {1}",
            dependencies=[],
            source_document="docs/proofs/T001.md",
            limitations=["Fixture only"],
            proposed_by="github:tester",
            timestamp="2026-07-30T19:00:00Z",
        )
    )
    apply_plan(
        plan_claim_registration(
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
    )


def _computation_payload(root: Path) -> dict[str, object]:
    artifact = "certificates/T001/result.json"
    environment = "experiments/T001/environment.json"
    details = "experiments/T001/details.json"
    _write(root / artifact, '{"ok": true}\n')
    _write(
        root / environment,
        json.dumps(
            {
                "interpreter": "Python 3.13",
                "dependencies": ["none"],
                "operating_system": "fixture",
                "locale": "C",
                "timezone": "UTC",
                "environment_variables": "none",
                "random_seeds": "not applicable",
            }
        ),
    )
    _write(
        root / details,
        json.dumps(
            {
                "algorithm": "Direct finite enumeration",
                "bounds": "n in [1, 1], inclusive",
                "arithmetic": "unbounded Python integers",
                "inputs": ["n = 1"],
                "input_hashes": "not applicable: generated scalar input",
                "outputs": [artifact],
                "output_hashes": "recorded in artifacts",
                "runtime": "under one second",
                "resources": "single process, under 64 MiB",
            }
        ),
    )
    return {
        "artifacts": [artifact],
        "commands": ["python verify.py"],
        "environment_json": environment,
        "details_json": details,
    }


def _git(root: Path, *arguments: str) -> str:
    completed = subprocess.run(
        ["git", "-C", str(root), *arguments],
        check=True,
        capture_output=True,
        text=True,
    )
    return completed.stdout.strip()


def _commit_fixture(root: Path, message: str = "fixture") -> str:
    if not (root / ".git").exists():
        _git(root, "init")
        _git(root, "config", "user.name", "Fixture")
        _git(root, "config", "user.email", "fixture@example.invalid")
    files = [
        str(path.relative_to(root))
        for path in sorted(root.rglob("*"))
        if path.is_file() and ".git" not in path.parts
    ]
    _git(root, "add", "--", *files)
    _git(root, "commit", "-m", message)
    return _git(root, "rev-parse", "HEAD")


__all__ = [name for name in globals() if not name.startswith("__")]
