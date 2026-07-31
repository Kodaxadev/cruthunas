from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .adapters import check_adapters, sync_adapters
from .cli_parser import _parser
from .models import discover_root
from .policy import format_text, run_checks
from .transactions import (
    TransactionError,
    TransactionPlan,
    apply_plan,
    plan_claim_proposal,
    plan_claim_registration,
    plan_claim_transition,
    plan_evidence_add,
)


def _render_plan(plan: TransactionPlan) -> str:
    lines = [f"Planned {plan.operation}:"]
    claim_id = plan.preview.get("claim_id")
    if claim_id:
        lines.append(f"- claim: {claim_id}")
    for change in plan.preview.get("changes", []):
        lines.append(f"- {change['axis']}: {change['from']!r} -> {change['to']!r}")
    for path in (item.path for item in plan.writes):
        lines.append(f"- write: {path}")
    return "\n".join(lines)


def _execute_plan(args: argparse.Namespace, plan: TransactionPlan) -> int:
    if args.as_json and not (args.yes or args.dry_run):
        raise TransactionError("--json requires --yes or --dry-run for mutating commands", exit_code=2)
    if args.dry_run:
        if args.as_json:
            print(json.dumps(plan.to_dict(applied=False), indent=2, sort_keys=True))
        else:
            print(_render_plan(plan))
            print("Dry run complete; no files were written.")
        return 0
    if not args.yes:
        print(_render_plan(plan))
        try:
            response = input("Apply transaction? [y/N] ").strip().lower()
        except EOFError:
            response = ""
        if response not in {"y", "yes"}:
            print("Transaction cancelled; no files were written.")
            return 0
    result = apply_plan(plan)
    if args.as_json:
        print(json.dumps(result, indent=2, sort_keys=True))
    else:
        print(f"Applied {plan.operation}.")
        for path in result["writes"]:
            print(f"- wrote: {path}")
    return 0


def _transaction_plan(args: argparse.Namespace, root: Path) -> TransactionPlan | None:
    if args.command == "claim" and args.claim_command == "propose":
        return plan_claim_proposal(
            root,
            claim_id=args.claim_id,
            kind=args.kind,
            title=args.title,
            statement=args.statement,
            scope=args.scope,
            dependencies=args.dependency,
            source_document=args.source_document,
            proof_location=args.proof_location,
            formal_declarations=args.formal_declaration,
            limitations=args.limitation,
            proposed_by=args.proposed_by,
            timestamp=args.timestamp,
        )
    if args.command == "claim" and args.claim_command == "register":
        return plan_claim_registration(
            root,
            proposal_path=args.proposal,
            created_by_type=args.created_by_type,
            created_by_id=args.created_by_id,
            requested_by=args.requested_by,
            approved_by_type=args.approved_by_type,
            approved_by_id=args.approved_by_id,
            source_revision=args.source_revision,
            timestamp=args.timestamp,
            establishes=args.establishes or None,
            does_not_establish=args.does_not_establish or None,
        )
    if args.command == "claim" and args.claim_command == "transition":
        return plan_claim_transition(
            root,
            claim_id=args.claim_id,
            reason=args.reason,
            requested_by=args.requested_by,
            approved_by_type=args.approved_by_type,
            approved_by_id=args.approved_by_id,
            evidence_ids=args.evidence,
            gate=args.gate,
            epistemic=args.epistemic,
            publication=args.publication,
            verification_add=args.verification_add,
            verification_remove=args.verification_remove,
            new_evidence_class=args.new_evidence_class,
            created_by_type=args.created_by_type,
            created_by_id=args.created_by_id,
            establishes=args.establishes,
            does_not_establish=args.does_not_establish,
            source_revision=args.source_revision,
            artifacts=args.artifact,
            commands=args.record_commands,
            environment_json=args.environment_json,
            notes=args.notes,
            reviewer_type=args.reviewer_type,
            reviewer_id=args.reviewer_id,
            timestamp=args.timestamp,
        )
    if args.command == "evidence" and args.evidence_command == "add":
        return plan_evidence_add(
            root,
            claim_id=args.claim_id,
            evidence_class=args.evidence_class,
            created_by_type=args.created_by_type,
            created_by_id=args.created_by_id,
            establishes=args.establishes,
            does_not_establish=args.does_not_establish,
            source_revision=args.source_revision,
            evidence_id=args.evidence_id,
            artifacts=args.artifact,
            commands=args.record_commands,
            environment_json=args.environment_json,
            notes=args.notes,
            reviewer_type=args.reviewer_type,
            reviewer_id=args.reviewer_id,
            timestamp=args.timestamp,
        )
    return None


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        root = discover_root(args.root)
    except FileNotFoundError as exc:
        print(f"cruthunas: {exc}", file=sys.stderr)
        return 2

    try:
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

        plan = _transaction_plan(args, root)
        if plan is not None:
            return _execute_plan(args, plan)

        result = run_checks(root)
        if args.command == "check":
            output = json.dumps(result.to_dict(), indent=2, sort_keys=True) if args.as_json else format_text(result)
            print(output)
            return 0 if result.ok else 1
        if args.command == "status":
            if args.as_json:
                print(json.dumps(result.to_dict(), indent=2, sort_keys=True))
            elif args.porcelain:
                summary = result.to_dict()["summary"]
                print(
                    f"ok={str(result.ok).lower()} claims={summary['claims']} "
                    f"evidence={summary['evidence']} transitions={summary['transitions']} "
                    f"errors={summary['errors']} warnings={summary['warnings']}"
                )
            else:
                print(format_text(result))
            return 0 if result.ok else 1
    except TransactionError as exc:
        print(f"cruthunas: {exc}", file=sys.stderr)
        if exc.details:
            print(json.dumps(exc.details, indent=2, sort_keys=True), file=sys.stderr)
        return exc.exit_code
    except Exception as exc:  # deterministic top-level failure boundary
        print(f"cruthunas: internal validator failure: {exc}", file=sys.stderr)
        return 5
    return 2
