from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from . import __version__
from .adapters import check_adapters, sync_adapters
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

    adapters = subcommands.add_parser(
        "adapters",
        help="Synchronize tool-specific skill adapters",
    )
    adapter_commands = adapters.add_subparsers(
        dest="adapter_command",
        required=True,
    )
    adapter_sync = adapter_commands.add_parser(
        "sync",
        help="Regenerate Claude and Codex skill adapters",
    )
    adapter_sync.add_argument("--root", type=Path, default=Path.cwd())
    adapter_check = adapter_commands.add_parser(
        "check",
        help="Fail when generated adapters drift",
    )
    adapter_check.add_argument("--root", type=Path, default=Path.cwd())

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

    if args.command == "adapters":
        if args.adapter_command == "sync":
            manifest = sync_adapters(root)
            print(f"Synchronized {len(manifest['skills'])} skill adapter(s).")
            return 0
        errors = check_adapters(root)
        if errors:
            print("Adapter check failed:")
            for error in errors:
                print(f"- {error}")
            return 1
        print("Adapter check passed.")
        return 0

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
