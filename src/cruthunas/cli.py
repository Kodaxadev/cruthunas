from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from . import __version__
from .models import discover_root
from .policy import format_text, run_checks


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="cruthunas",
        description="Cruthunas deterministic policy kernel",
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {__version__}",
    )
    subcommands = parser.add_subparsers(dest="command", required=True)

    check = subcommands.add_parser(
        "check",
        help="Validate the repository policy state",
    )
    mode = check.add_mutually_exclusive_group()
    mode.add_argument(
        "--all",
        action="store_true",
        help="Validate the complete repository",
    )
    mode.add_argument(
        "--changed",
        action="store_true",
        help="Validate changed work and all cross-file invariants; currently runs the complete policy graph",
    )
    check.add_argument("--root", type=Path, default=Path.cwd())
    check.add_argument("--json", action="store_true", dest="as_json")

    status = subcommands.add_parser(
        "status",
        help="Print a machine-readable policy summary",
    )
    status.add_argument("--root", type=Path, default=Path.cwd())
    status.add_argument("--json", action="store_true", dest="as_json")
    status.add_argument("--porcelain", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        root = discover_root(args.root)
    except FileNotFoundError as exc:
        print(f"cruthunas: {exc}", file=sys.stderr)
        return 2

    result = run_checks(root)
    if args.command == "check":
        output = (
            json.dumps(result.to_dict(), indent=2, sort_keys=True)
            if args.as_json
            else format_text(result)
        )
        print(output)
        return 0 if result.ok else 1

    if args.command == "status":
        if args.as_json:
            print(json.dumps(result.to_dict(), indent=2, sort_keys=True))
        elif args.porcelain:
            summary = result.to_dict()["summary"]
            print(
                f"ok={str(result.ok).lower()} "
                f"claims={summary['claims']} "
                f"evidence={summary['evidence']} "
                f"transitions={summary['transitions']} "
                f"errors={summary['errors']} "
                f"warnings={summary['warnings']}"
            )
        else:
            print(format_text(result))
        return 0 if result.ok else 1

    return 2
