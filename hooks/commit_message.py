from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path


PATTERN = re.compile(
    r"^(claim\([A-Z][0-9]{3,}\)|"
    r"transition\([A-Z][0-9]{3,}\)|"
    r"review\([A-Z][0-9]{3,}\)|"
    r"release\([^)]+\)|"
    r"correction\([A-Z][0-9]{3,}\)|"
    r"policy): .+"
)
GOVERNED_PREFIXES = (
    "claims/",
    "audit/",
    "CORRECTIONS.md",
    "manuscript/",
)


def requires_governed_message(paths: list[str]) -> bool:
    return any(
        path == prefix or path.startswith(prefix)
        for path in paths
        for prefix in GOVERNED_PREFIXES
    )


def valid_message(message: str) -> bool:
    lines = message.splitlines()
    first = lines[0].strip() if lines else ""
    return bool(PATTERN.fullmatch(first))


def main(argv: list[str] | None = None) -> int:
    args = argv or sys.argv[1:]
    if len(args) != 1:
        print("usage: commit_message.py <commit-message-file>", file=sys.stderr)
        return 2
    try:
        changed = subprocess.run(
            ["git", "diff", "--cached", "--name-only", "--diff-filter=ACMR"],
            check=True,
            capture_output=True,
            text=True,
        ).stdout.splitlines()
    except (OSError, subprocess.CalledProcessError) as exc:
        print(f"could not inspect staged files: {exc}", file=sys.stderr)
        return 2
    if not requires_governed_message(changed):
        return 0
    message = Path(args[0]).read_text(encoding="utf-8")
    if valid_message(message):
        return 0
    print(
        "Governed changes require claim(...), transition(...), review(...), "
        "release(...), correction(...), or policy: commit syntax.",
        file=sys.stderr,
    )
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
