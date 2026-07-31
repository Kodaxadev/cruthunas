from __future__ import annotations

import argparse
from pathlib import Path

from . import __version__
from .transactions import (
    ACTOR_TYPES,
    APPROVER_TYPES,
    CLAIM_KINDS,
    EPISTEMIC_STATUSES,
    EVIDENCE_CLASSES,
    PUBLICATION_STATUSES,
    VERIFICATION_STATUSES,
)


def _add_mutation_flags(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--yes", action="store_true", help="Apply without an interactive confirmation")
    parser.add_argument("--dry-run", action="store_true", help="Validate and preview without writing")
    parser.add_argument("--json", action="store_true", dest="as_json")
    parser.add_argument("--timestamp", help="Explicit RFC 3339 UTC timestamp for deterministic automation")


def _add_created_by(parser: argparse.ArgumentParser, *, required: bool = True) -> None:
    parser.add_argument("--created-by-type", choices=ACTOR_TYPES, required=required)
    parser.add_argument("--created-by-id", required=required)


def _add_evidence_payload(parser: argparse.ArgumentParser, *, required: bool) -> None:
    parser.add_argument("--establishes", action="append", required=required, default=[])
    parser.add_argument(
        "--does-not-establish",
        action="append",
        required=required,
        default=[],
    )
    parser.add_argument("--source-revision")
    parser.add_argument("--artifact", action="append", default=[])
    parser.add_argument("--command", action="append", default=[], dest="record_commands")
    parser.add_argument("--environment-json")
    parser.add_argument(
        "--details-json",
        help="JSON object containing class-specific evidence details required by policy",
    )
    parser.add_argument("--notes")
    parser.add_argument("--reviewer-type", choices=ACTOR_TYPES)
    parser.add_argument("--reviewer-id")


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="cruthunas",
        description="Cruthunas deterministic policy kernel",
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    subcommands = parser.add_subparsers(dest="command", required=True)

    check = subcommands.add_parser("check", help="Validate the repository policy state")
    mode = check.add_mutually_exclusive_group()
    mode.add_argument("--all", action="store_true", help="Validate the complete repository")
    mode.add_argument(
        "--changed",
        action="store_true",
        help="Validate changed work and all cross-file invariants; currently runs the complete policy graph",
    )
    check.add_argument("--root", type=Path, default=Path.cwd())
    check.add_argument("--json", action="store_true", dest="as_json")

    adapters = subcommands.add_parser("adapters", help="Synchronize tool-specific skill adapters")
    adapter_commands = adapters.add_subparsers(dest="adapter_command", required=True)
    adapter_sync = adapter_commands.add_parser("sync", help="Regenerate Claude and Codex skill adapters")
    adapter_sync.add_argument("--root", type=Path, default=Path.cwd())
    adapter_check = adapter_commands.add_parser("check", help="Fail when generated adapters drift")
    adapter_check.add_argument("--root", type=Path, default=Path.cwd())

    status = subcommands.add_parser("status", help="Print a machine-readable policy summary")
    status.add_argument("--root", type=Path, default=Path.cwd())
    status.add_argument("--json", action="store_true", dest="as_json")
    status.add_argument("--porcelain", action="store_true")

    claim = subcommands.add_parser("claim", help="Create and transition governed claims")
    claim_commands = claim.add_subparsers(dest="claim_command", required=True)

    propose = claim_commands.add_parser(
        "propose",
        help="Create a non-ledger claim proposal under audit/proposals/",
    )
    propose.add_argument("--id", required=True, dest="claim_id")
    propose.add_argument("--kind", choices=CLAIM_KINDS, required=True)
    propose.add_argument("--title")
    propose.add_argument("--statement", required=True)
    propose.add_argument("--scope")
    propose.add_argument("--dependency", action="append", default=[])
    propose.add_argument("--source-document", required=True)
    propose.add_argument("--proof-location")
    propose.add_argument("--formal-declaration", action="append", default=[])
    propose.add_argument("--limitation", action="append", required=True)
    propose.add_argument("--proposed-by", required=True)
    _add_mutation_flags(propose)

    register = claim_commands.add_parser(
        "register",
        help="Atomically register a proposal with Gate 3 -> 4 evidence and history",
    )
    register.add_argument("proposal")
    _add_created_by(register)
    register.add_argument("--requested-by")
    register.add_argument("--approved-by-type", choices=APPROVER_TYPES, default="policy")
    register.add_argument("--approved-by-id", default="cruthunas/claim-registration-v1")
    register.add_argument("--source-revision")
    register.add_argument("--establishes", action="append", default=[])
    register.add_argument("--does-not-establish", action="append", default=[])
    _add_mutation_flags(register)

    transition = claim_commands.add_parser(
        "transition",
        help="Atomically change one or more claim axes with evidence and transition records",
    )
    transition.add_argument("claim_id")
    transition.add_argument("--gate", type=int)
    transition.add_argument("--epistemic", choices=EPISTEMIC_STATUSES)
    transition.add_argument("--publication", choices=PUBLICATION_STATUSES)
    transition.add_argument("--verification-add", action="append", choices=VERIFICATION_STATUSES, default=[])
    transition.add_argument("--verification-remove", action="append", choices=VERIFICATION_STATUSES, default=[])
    transition.add_argument("--evidence", action="append", default=[])
    transition.add_argument("--new-evidence-class", choices=EVIDENCE_CLASSES)
    transition.add_argument("--reason", required=True)
    transition.add_argument("--requested-by", required=True)
    transition.add_argument("--approved-by-type", choices=APPROVER_TYPES, default="policy")
    transition.add_argument("--approved-by-id", default="cruthunas/transition-v1")
    _add_created_by(transition, required=False)
    _add_evidence_payload(transition, required=False)
    _add_mutation_flags(transition)

    evidence = subcommands.add_parser("evidence", help="Create and link governed evidence")
    evidence_commands = evidence.add_subparsers(dest="evidence_command", required=True)
    evidence_add = evidence_commands.add_parser(
        "add",
        help="Atomically create an evidence record and link it from the claim ledger",
    )
    evidence_add.add_argument("evidence_class", choices=EVIDENCE_CLASSES)
    evidence_add.add_argument("--claim", required=True, dest="claim_id")
    evidence_add.add_argument("--id", dest="evidence_id")
    _add_created_by(evidence_add)
    _add_evidence_payload(evidence_add, required=True)
    _add_mutation_flags(evidence_add)
    return parser
