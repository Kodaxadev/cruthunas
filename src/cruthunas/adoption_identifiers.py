from __future__ import annotations

import re
from pathlib import Path

from .adoption_scan import TEXT_SUFFIXES, read_adoption_text
from .adoption_types import AdoptionGap
from .claim_ids import CANONICAL_CLAIM_ID, legacy_canonical_id, normalize_alias
from .models import read_yaml

# Try the dotted form first and forbid the simple form from stopping before a
# dotted alphanumeric continuation. This preserves C2.1 as one historical token
# instead of silently reporting its C2 prefix.
HISTORICAL_TOKEN = re.compile(
    r"(?<![A-Za-z0-9])(?:"
    r"([A-Z]{1,2}[0-9]{1,3}(?:\.[0-9]+)+)(?![A-Za-z0-9])"
    r"|([A-Z]{1,2}[0-9]{1,3})(?!\.[A-Za-z0-9])(?![A-Za-z0-9])"
    r")"
)
EXCLUDED_ID_PATHS = ("schemas/", "src/cruthunas/templates/")


def _declared_aliases(root: Path) -> set[str]:
    declared: set[str] = set()
    ledger = root / "claims/claims.yaml"
    candidates = [ledger]
    proposals = root / "audit/proposals"
    if proposals.is_dir():
        candidates.extend(sorted([*proposals.glob("*.yaml"), *proposals.glob("*.yml")]))
    for path in candidates:
        if not path.is_file():
            continue
        try:
            value = read_yaml(path)
        except Exception:
            continue
        records = value.get("claims", []) if isinstance(value, dict) and path == ledger else [value]
        for record in records:
            if not isinstance(record, dict):
                continue
            for alias in record.get("aliases", []):
                if not isinstance(alias, str):
                    continue
                try:
                    declared.add(normalize_alias(alias))
                except ValueError:
                    pass
    return declared


def _historical_tokens(content: str) -> list[str]:
    return [match.group(1) or match.group(2) for match in HISTORICAL_TOKEN.finditer(content)]


def legacy_id_gaps(root: Path, files: list[Path]) -> list[AdoptionGap]:
    occurrences: dict[str, list[str]] = {}
    declared_aliases = _declared_aliases(root)
    for path in files:
        if path.suffix.lower() not in TEXT_SUFFIXES:
            continue
        content = read_adoption_text(path)
        if content is None:
            continue
        relative = str(path.relative_to(root)).replace("\\", "/")
        if relative == "claims/schema.json" or relative.startswith(EXCLUDED_ID_PATHS):
            continue
        for token in _historical_tokens(content):
            try:
                normalized = normalize_alias(token)
            except ValueError:
                normalized = token.upper()
            if CANONICAL_CLAIM_ID.fullmatch(normalized) or normalized in declared_aliases:
                continue
            occurrences.setdefault(normalized, []).append(relative)

    gaps: list[AdoptionGap] = []
    for alias in sorted(occurrences):
        paths = sorted(set(occurrences[alias]))
        canonical = legacy_canonical_id(alias)
        automatic = canonical is not None
        message = (
            f"Historical claim ID {alias} can be represented as canonical {canonical} with alias {alias}"
            if canonical
            else f"Historical claim ID {alias} has no lossless automatic canonical-ID mapping"
        )
        gaps.append(
            AdoptionGap(
                "claim_id.incompatible",
                "historical_claim_ids",
                message,
                paths[0],
                automatic,
                {"alias": alias, "suggested_canonical": canonical, "occurrences": paths},
            )
        )
    return gaps
