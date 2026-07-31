from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

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


def _command() -> str:
    executable = shutil.which("cruthunas")
    assert executable is not None, "editable install did not expose the cruthunas console script"
    return executable


def test_installed_console_script_reports_version() -> None:
    completed = subprocess.run(
        [_command(), "--version"],
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    assert completed.returncode == 0
    assert completed.stdout.startswith("cruthunas ")
    assert completed.stderr == ""


def test_installed_console_script_dry_run_json_is_non_mutating(tmp_path: Path) -> None:
    root = _project(tmp_path)
    completed = subprocess.run(
        [
            _command(),
            "claim",
            "propose",
            "--root",
            str(root),
            "--id",
            "T001",
            "--kind",
            "THEOREM",
            "--statement",
            "For every n in {1}, n = 1.",
            "--source-document",
            "docs/proofs/T001.md",
            "--limitation",
            "Fixture only",
            "--proposed-by",
            "github:tester",
            "--timestamp",
            "2026-07-30T19:00:00Z",
            "--dry-run",
            "--json",
        ],
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    assert completed.returncode == 0, completed.stderr
    payload = json.loads(completed.stdout)
    assert payload["applied"] is False
    assert completed.stderr == ""
    assert not (root / "audit/proposals/T001.yaml").exists()


def test_installed_console_script_preserves_error_exit_and_stderr(tmp_path: Path) -> None:
    root = _project(tmp_path)
    completed = subprocess.run(
        [
            _command(),
            "claim",
            "propose",
            "--root",
            str(root),
            "--id",
            "T001",
            "--kind",
            "THEOREM",
            "--statement",
            "   ",
            "--source-document",
            "docs/proofs/T001.md",
            "--limitation",
            "Fixture only",
            "--proposed-by",
            "github:tester",
            "--dry-run",
        ],
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    assert completed.returncode == 2
    assert "Claim statement must not be empty" in completed.stderr
    assert completed.stdout == ""
