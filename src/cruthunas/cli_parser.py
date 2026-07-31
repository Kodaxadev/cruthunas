from __future__ import annotations

import argparse
from pathlib import Path

from . import __version__
from .transactions import (
    ACTOR_TYPES, APPROVER_TYPES, CLAIM_KINDS, EPISTEMIC_STATUSES,
    EVIDENCE_CLASSES, PROJECT_MODES, PUBLICATION_STATUSES,
    VERIFICATION_STATUSES,
)


def _add_mutation_flags(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--yes", action="store_true", help="Apply without an interactive confirmation")
    parser.add_argument("--dry-run", action="store_true", help="Validate and preview without writing")
    parser.add_argument("--json", action="store_true", dest="as_json")
    parser.add_argument("--timestamp", help="Explicit RFC 3339 UTC timestamp for deterministic automation")


def _add_init_flags(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--root", type=Path, default=Path.cwd(), help="Existing directory to initialize")
    parser.add_argument("--yes", action="store_true", help="Apply without an interactive confirmation")
    parser.add_argument("--dry-run", action="store_true", help="Validate and preview without writing")
    parser.add_argument("--json", action="store_true", dest="as_json")


def _add_created_by(parser: argparse.ArgumentParser, *, required: bool = True) -> None:
    parser.add_argument("--created-by-type", choices=ACTOR_TYPES, required=required,
        help="Provenance actor type. Agent-created computation evidence is provenance only and does not establish independent reproduction or external review.")
    parser.add_argument("--created-by-id", required=required, help="Durable identity of the record creator")


def _add_evidence_payload(parser: argparse.ArgumentParser, *, required: bool) -> None:
    parser.add_argument("--establishes", action="append", required=required, default=[])
    parser.add_argument("--does-not-establish", action="append", required=required, default=[])
    parser.add_argument("--source-revision")
    parser.add_argument("--artifact", action="append", default=[])
    parser.add_argument("--command", action="append", default=[], dest="record_commands")
    parser.add_argument("--environment-json")
    parser.add_argument("--details-json", help="JSON object containing class-specific evidence details required by policy")
    parser.add_argument("--notes")
    parser.add_argument("--reviewer-type", choices=ACTOR_TYPES, help="REVIEW_EXTERNAL requires a named human or venue")
    parser.add_argument("--reviewer-id", help="Durable reviewer or venue identity")


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="cruthunas", description="Cruthunas deterministic policy kernel")
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    subcommands = parser.add_subparsers(dest="command", required=True)

    init = subcommands.add_parser("init", help="Initialize minimum governed project structure atomically")
    init.add_argument("--mode", choices=PROJECT_MODES, required=True)
    init.add_argument("--framework-repository", default="Kodaxadev/cruthunas", help="Framework repository in owner/name form")
    init.add_argument("--framework-commit", required=True, help="Exact 40-character framework commit SHA")
    init.add_argument("--framework-version", help="Immutable framework release version; released mode only")
    init.add_argument("--framework-release-manifest", help="Local immutable release attestation; released mode only")
    init.add_argument("--profile", default="mathematics")
    init.add_argument("--project-id", required=True)
    init.add_argument("--project-title", required=True)
    init.add_argument("--maintainer-github", action="append", required=True, help="Repeat for multiple maintainers")
    _add_init_flags(init)

    adoption = subcommands.add_parser("adoption", help="Inspect adoption readiness without mutation")
    adoption_commands = adoption.add_subparsers(dest="adoption_command", required=True)
    gaps = adoption_commands.add_parser("gaps", help="Report deterministic adoption and migration gaps")
    gaps.add_argument("--root", type=Path, default=Path.cwd())
    gaps.add_argument("--json", action="store_true", dest="as_json")

    check = subcommands.add_parser("check", help="Validate the repository policy state")
    mode = check.add_mutually_exclusive_group()
    mode.add_argument("--all", action="store_true", help="Validate the complete repository")
    mode.add_argument("--changed", action="store_true", help="Validate changed work and all cross-file invariants; currently runs the complete policy graph")
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
    propose = claim_commands.add_parser("propose", help="Create a non-ledger claim proposal under audit/proposals/")
    propose.add_argument("--id", required=True, dest="claim_id", help="Canonical ID matching ^[A-Z][0-9]{3,}$")
    propose.add_argument("--alias", action="append", default=[], help="Historical alias such as K4; normalized and preserved as metadata")
    propose.add_argument("--kind", choices=CLAIM_KINDS, required=True)
    propose.add_argument("--title")
    propose.add_argument("--statement", required=True)
    propose.add_argument("--scope")
    propose.add_argument("--dependency", action="append", default=[], help="Registered canonical claim ID; aliases are not accepted")
    propose.add_argument("--source-document", required=True)
    propose.add_argument("--proof-location")
    propose.add_argument("--formal-declaration", action="append", default=[])
    propose.add_argument("--limitation", action="append", required=True)
    propose.add_argument("--proposed-by", required=True, help="Durable proposal-originator identity")
    _add_mutation_flags(propose)

    register = claim_commands.add_parser("register", help="Atomically register a proposal with Gate 3 -> 4 evidence and history")
    register.add_argument("proposal")
    _add_created_by(register)
    register.add_argument("--requested-by", help="Durable registration-requester identity")
    register.add_argument("--approved-by-type", choices=APPROVER_TYPES, default="policy")
    register.add_argument("--approved-by-id", default="cruthunas/claim-registration-v1")
    register.add_argument("--source-revision")
    register.add_argument("--establishes", action="append", default=[])
    register.add_argument("--does-not-establish", action="append", default=[])
    _add_mutation_flags(register)

    transition = claim_commands.add_parser("transition", help="Atomically change claim axes with evidence and history")
    transition.add_argument("claim_id", help="Canonical claim ID; aliases are not accepted")
    transition.add_argument("--gate", type=int)
    transition.add_argument("--epistemic", choices=EPISTEMIC_STATUSES)
    transition.add_argument("--publication", choices=PUBLICATION_STATUSES)
    transition.add_argument("--verification-add", action="append", choices=VERIFICATION_STATUSES, default=[])
    transition.add_argument("--verification-remove", action="append", choices=VERIFICATION_STATUSES, default=[])
    transition.add_argument("--evidence", action="append", default=[])
    transition.add_argument("--new-evidence-class", choices=EVIDENCE_CLASSES)
    transition.add_argument("--reason", required=True)
    transition.add_argument("--requested-by", required=True, help="Durable transition-requester identity")
    transition.add_argument("--approved-by-type", choices=APPROVER_TYPES, default="policy")
    transition.add_argument("--approved-by-id", default="cruthunas/transition-v1")
    _add_created_by(transition, required=False)
    _add_evidence_payload(transition, required=False)
    _add_mutation_flags(transition)

    evidence = subcommands.add_parser("evidence", help="Create and link governed evidence")
    evidence_commands = evidence.add_subparsers(dest="evidence_command", required=True)
    evidence_add = evidence_commands.add_parser("add", help="Atomically create evidence and link it from the ledger")
    evidence_add.add_argument("evidence_class", choices=EVIDENCE_CLASSES, help="Class alone never establishes independence or external review")
    evidence_add.add_argument("--claim", required=True, dest="claim_id", help="Canonical claim ID; aliases are not accepted")
    evidence_add.add_argument("--id", dest="evidence_id")
    _add_created_by(evidence_add)
    _add_evidence_payload(evidence_add, required=True)
    _add_mutation_flags(evidence_add)
    return parser
