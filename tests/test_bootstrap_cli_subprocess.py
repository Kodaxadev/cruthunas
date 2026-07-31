from __future__ import annotations

import json
import subprocess
from pathlib import Path

FRAMEWORK_COMMIT = "3dd07da5534410b285a337110106bb65f9ab628e"


def test_installed_console_script_supports_init_dry_run(tmp_path: Path) -> None:
    completed = subprocess.run(
        [
            "cruthunas", "init", "--root", str(tmp_path), "--mode", "experimental",
            "--framework-commit", FRAMEWORK_COMMIT, "--project-id", "fixture",
            "--project-title", "Fixture", "--maintainer-github", "tester",
            "--dry-run", "--json",
        ],
        check=True, capture_output=True, text=True,
    )
    payload = json.loads(completed.stdout)
    assert payload["operation"] == "project.init"
    assert payload["applied"] is False
    assert not (tmp_path / ".cruthunas/project.yaml").exists()
