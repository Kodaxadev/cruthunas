from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path


GOVERNED = (
    "claims/",
    "audit/",
    "formal/",
    "manuscript/",
    "schemas/",
    "skills/",
    "CRUTHUNAS_SPEC.md",
    "RESEARCH_CHARTER.md",
)


def _governed(path: str) -> bool:
    normalized = path.replace("\\", "/")
    return any(
        part in normalized or normalized.endswith(part)
        for part in GOVERNED
    )


def main() -> int:
    payload = json.load(sys.stdin)
    event = payload.get("hook_event_name")
    if event == "PostToolUse":
        tool_input = payload.get("tool_input", {})
        path = str(tool_input.get("file_path", ""))
        if path and not _governed(path):
            return 0
    root = Path(
        os.environ.get(
            "CLAUDE_PROJECT_DIR",
            payload.get("cwd", "."),
        )
    ).resolve()
    environment = os.environ.copy()
    source_root = str(root / "src")
    existing = environment.get("PYTHONPATH")
    environment["PYTHONPATH"] = (
        source_root if not existing else source_root + os.pathsep + existing
    )
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "cruthunas",
            "check",
            "--changed",
            "--root",
            str(root),
        ],
        capture_output=True,
        text=True,
        env=environment,
    )
    if result.returncode == 0:
        return 0
    print((result.stdout or result.stderr).strip(), file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
