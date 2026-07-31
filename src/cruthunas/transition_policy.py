from __future__ import annotations

from typing import Any, Iterable, Mapping


VERIFICATION_EVIDENCE = {
    "INTERNAL_AUDIT": frozenset({"REVIEW_INTERNAL"}),
    "INDEPENDENT_REPRODUCTION": frozenset({"REPRODUCTION"}),
    "FORMALIZED": frozenset({"FORMALIZATION"}),
    "EXTERNAL_REVIEW": frozenset({"REVIEW_EXTERNAL"}),
}

GATE_PROMOTION_EVIDENCE = {
    5: (frozenset({"REVIEW_INTERNAL", "REVIEW_EXTERNAL", "GATE_DISPOSITION"}),),
    6: (frozenset({"COMPUTATION", "REPRODUCTION", "GATE_DISPOSITION"}),),
    7: (frozenset({"FORMALIZATION", "GATE_DISPOSITION"}),),
    8: (frozenset({"MANUSCRIPT_AUDIT"}),),
    9: (frozenset({"RELEASE"}),),
    10: (frozenset({"CORRECTION", "REFUTATION"}),),
}

GATE_5_REVIEW_ROLES = (
    "prover",
    "falsifier",
    "dependency_auditor",
    "statement_auditor",
)


def evidence_classes(records: Iterable[Mapping[str, Any]]) -> frozenset[str]:
    return frozenset(
        value
        for record in records
        if isinstance((value := record.get("class")), str)
    )


def _format_group(group: frozenset[str]) -> str:
    return " or ".join(sorted(group))


def _missing_groups(
    classes: frozenset[str],
    groups: Iterable[frozenset[str]],
) -> list[str]:
    return [_format_group(group) for group in groups if classes.isdisjoint(group)]


def _recorded_review_role(value: Any) -> bool:
    if isinstance(value, str):
        return bool(value.strip())
    if isinstance(value, Mapping):
        return bool(value)
    if isinstance(value, (list, tuple, set)):
        return bool(value)
    return value is True


def _gate_five_role_errors(records: tuple[Mapping[str, Any], ...]) -> list[str]:
    classes = evidence_classes(records)
    if "GATE_DISPOSITION" in classes:
        return []
    if classes.isdisjoint({"REVIEW_INTERNAL", "REVIEW_EXTERNAL"}):
        return []

    recorded: set[str] = set()
    for record in records:
        if record.get("class") not in {"REVIEW_INTERNAL", "REVIEW_EXTERNAL"}:
            continue
        details = record.get("details")
        if not isinstance(details, Mapping):
            continue
        review_roles = details.get("review_roles")
        if not isinstance(review_roles, Mapping):
            continue
        recorded.update(
            role
            for role in GATE_5_REVIEW_ROLES
            if _recorded_review_role(review_roles.get(role))
        )

    missing = [role for role in GATE_5_REVIEW_ROLES if role not in recorded]
    if not missing:
        return []
    return [
        "Gate 5 review evidence must record non-empty details.review_roles for: "
        + ", ".join(missing)
    ]


def required_support_groups(axis: str, before: Any, after: Any) -> tuple[frozenset[str], ...]:
    if before == after:
        return ()

    if axis == "gate":
        if not isinstance(before, int) or not isinstance(after, int) or after <= before:
            return ()
        return GATE_PROMOTION_EVIDENCE.get(after, ())

    if axis == "verification":
        before_set = set(before) if isinstance(before, list) else set()
        after_set = set(after) if isinstance(after, list) else set()
        additions = after_set - before_set - {"UNCHECKED"}
        return tuple(
            VERIFICATION_EVIDENCE[item]
            for item in sorted(additions)
            if item in VERIFICATION_EVIDENCE
        )

    if axis == "epistemic":
        if after == "REFUTED":
            return (frozenset({"REFUTATION"}),)
        if after == "OPEN":
            return (frozenset({"CORRECTION"}),) if before == "REFUTED" else ()
        if after == "HEURISTIC":
            if before in {"COMPUTATIONAL", "PROVED"}:
                return ()
            groups = [frozenset({"DERIVATION", "BASELINE", "COMPUTATION", "REPRODUCTION"})]
            if before == "REFUTED":
                groups.append(frozenset({"CORRECTION"}))
            return tuple(groups)
        if after == "COMPUTATIONAL":
            if before == "PROVED":
                return ()
            groups = [frozenset({"COMPUTATION", "REPRODUCTION"})]
            if before == "REFUTED":
                groups.append(frozenset({"CORRECTION"}))
            return tuple(groups)
        if after == "PROVED":
            groups = [
                frozenset({"PROOF", "FORMALIZATION"}),
                frozenset({"REVIEW_INTERNAL", "REVIEW_EXTERNAL"}),
            ]
            if before == "REFUTED":
                groups.append(frozenset({"CORRECTION"}))
            return tuple(groups)
        return ()

    if axis == "publication":
        if after == "WORKING":
            return (frozenset({"CORRECTION"}),)
        if after == "FROZEN":
            if before == "WORKING":
                return (frozenset({"MANUSCRIPT_AUDIT"}),)
            return (frozenset({"CORRECTION"}),)
        if after in {"PREPRINT", "SUBMITTED", "PUBLISHED"}:
            return (frozenset({"RELEASE"}),)
        if after in {"CORRECTED", "WITHDRAWN"}:
            return (frozenset({"CORRECTION"}),)
        return ()

    return ()


def transition_support_errors(
    axis: str,
    before: Any,
    after: Any,
    records: Iterable[Mapping[str, Any]],
) -> list[str]:
    record_list = tuple(records)
    classes = evidence_classes(record_list)
    missing = _missing_groups(classes, required_support_groups(axis, before, after))
    errors = [
        f"{axis} transition {before!r} -> {after!r} requires transition evidence class {requirement}"
        for requirement in missing
    ]
    if axis == "gate" and isinstance(before, int) and after == 5 and after > before:
        errors.extend(_gate_five_role_errors(record_list))
    return errors
