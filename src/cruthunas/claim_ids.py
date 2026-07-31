from __future__ import annotations

import re
from collections.abc import Iterable, Mapping
from typing import Any

CANONICAL_CLAIM_ID = re.compile(r"^[A-Z][0-9]{3,}$")
HISTORICAL_ALIAS = re.compile(r"^[A-Z][A-Z0-9-]*$")
LEGACY_PADDED_ID = re.compile(r"^([A-Z])([0-9]{1,2})$")


class ClaimAliasError(ValueError):
    pass


def normalize_alias(value: str) -> str:
    if not isinstance(value, str):
        raise ClaimAliasError("Claim alias must be text")
    normalized = value.strip().upper()
    if not normalized:
        raise ClaimAliasError("Claim alias must not be empty")
    if not HISTORICAL_ALIAS.fullmatch(normalized):
        raise ClaimAliasError(
            "Claim alias must match ^[A-Z][A-Z0-9-]*$ after trimming and uppercasing"
        )
    return normalized


def normalize_aliases(values: Iterable[str]) -> list[str]:
    normalized: list[str] = []
    seen: set[str] = set()
    for value in values:
        alias = normalize_alias(value)
        if alias in seen:
            raise ClaimAliasError(f"Duplicate claim alias after normalization: {alias}")
        seen.add(alias)
        normalized.append(alias)
    return normalized


def legacy_canonical_id(value: str) -> str | None:
    try:
        alias = normalize_alias(value)
    except ClaimAliasError:
        return None
    match = LEGACY_PADDED_ID.fullmatch(alias)
    if not match:
        return None
    return f"{match.group(1)}{int(match.group(2)):03d}"


def claim_aliases(claim: Mapping[str, Any]) -> list[str]:
    values = claim.get("aliases", [])
    if not isinstance(values, list):
        return []
    return [item for item in values if isinstance(item, str)]


def claim_reference_index(
    claims: Iterable[Mapping[str, Any]],
) -> tuple[set[str], dict[str, str], list[str]]:
    canonical_ids: set[str] = set()
    aliases: dict[str, str] = {}
    errors: list[str] = []
    claim_list = list(claims)

    for claim in claim_list:
        claim_id = claim.get("id")
        if isinstance(claim_id, str):
            canonical_ids.add(claim_id)

    for claim in claim_list:
        claim_id = claim.get("id")
        if not isinstance(claim_id, str):
            continue
        raw_aliases = claim.get("aliases", [])
        if not isinstance(raw_aliases, list):
            continue
        seen_local: set[str] = set()
        for raw in raw_aliases:
            if not isinstance(raw, str):
                continue
            try:
                alias = normalize_alias(raw)
            except ClaimAliasError as exc:
                errors.append(f"Claim {claim_id} has invalid alias {raw!r}: {exc}")
                continue
            if alias in seen_local:
                errors.append(
                    f"Claim {claim_id} repeats alias {alias} after normalization"
                )
                continue
            seen_local.add(alias)
            if alias in canonical_ids:
                errors.append(
                    f"Claim alias {alias} collides with canonical claim ID {alias}"
                )
                continue
            owner = aliases.get(alias)
            if owner is not None and owner != claim_id:
                errors.append(
                    f"Claim alias {alias} is assigned to both {owner} and {claim_id}"
                )
                continue
            aliases[alias] = claim_id
    return canonical_ids, aliases, errors


def validate_new_claim_references(
    claim_id: str,
    aliases: Iterable[str],
    existing_claims: Iterable[Mapping[str, Any]],
) -> list[str]:
    canonical_ids, alias_index, existing_errors = claim_reference_index(existing_claims)
    errors = list(existing_errors)
    if claim_id in alias_index:
        errors.append(
            f"Canonical claim ID {claim_id} collides with existing alias owned by {alias_index[claim_id]}"
        )
    try:
        normalized = normalize_aliases(aliases)
    except ClaimAliasError as exc:
        errors.append(str(exc))
        return errors
    for alias in normalized:
        if alias == claim_id:
            errors.append(f"Claim alias {alias} duplicates its canonical claim ID")
        if alias in canonical_ids:
            errors.append(f"Claim alias {alias} collides with canonical claim ID {alias}")
        owner = alias_index.get(alias)
        if owner is not None:
            errors.append(f"Claim alias {alias} is already assigned to {owner}")
    return errors
