from __future__ import annotations

import re
from pathlib import Path

from .adoption_scan import TEXT_SUFFIXES, read_adoption_text
from .adoption_types import AdoptionGap
from .evidence_policy import INDEPENDENCE_KEYS
from .models import read_yaml

INDEPENDENCE_ACTION = (
    r"regenerated|reproduced|reimplemented|implemented|re-?verified|verified|"
    r"cross-?checked|checked|audited|reviewed|recomputed|validated|replicated|"
    r"confirmed|established|refereed|closed"
)
ASSERTION_PATTERNS = (
    re.compile(
        r"\bindependent(?:\s+[A-Za-z0-9_+\-/]+){0,3}\s+"
        r"(?:implementations?|verifiers?|reproductions?|reimplementations?|"
        r"certificates?|generators?|checks?|verification\s+frameworks?)\b",
        re.IGNORECASE,
    ),
    re.compile(r"\bexternal\s+reviews?\b", re.IGNORECASE),
    re.compile(
        rf"\bindependently(?:[\s,;:()\-\u2013\u2014]+)(?:{INDEPENDENCE_ACTION})\b",
        re.IGNORECASE,
    ),
    re.compile(
        rf"\b(?:{INDEPENDENCE_ACTION})\b"
        r"(?:[\s,;:()\-\u2013\u2014]+[A-Za-z0-9_+\-/]+){0,4}"
        r"[\s,;:()\-\u2013\u2014]+independently\b",
        re.IGNORECASE,
    ),
)
CLAUSE_BOUNDARY = re.compile(r"[.!?;]|\bbut\b|\bhowever\b", re.IGNORECASE)
NEGATING_CLAUSE = re.compile(
    r"\b(?:(?:does|do|did|has|have|had|is|are|was|were)\s+not|"
    r"no|not|never|without|cannot|can't|isn't|aren't|wasn't|weren't|"
    r"hasn't|haven't|hadn't|doesn't|don't|didn't)\b",
    re.IGNORECASE,
)
REQUIREMENT_CLAUSE = re.compile(
    r"\b(?:must|should|shall|will|would|could|can|may|might|needs?|needed|"
    r"requires?|required|awaits?|awaiting|pending|planned|proposed)\b",
    re.IGNORECASE,
)
NONASSERTIVE_SUFFIX = re.compile(
    r"^[\s,;:()\-\u2013\u2014]*(?:(?:is|are|was|were|remains?)\s+)?"
    r"(?:still\s+)?(?:required|needed|pending|awaiting|planned|proposed|"
    r"must|should|shall|will|would|could|can|may|might)\b",
    re.IGNORECASE,
)


def _is_nonassertive(line: str, match: re.Match[str]) -> bool:
    if line.rstrip().endswith("?"):
        return True
    prefix = CLAUSE_BOUNDARY.split(line[: match.start()])[-1]
    suffix = line[match.end() : match.end() + 100]
    return bool(
        NEGATING_CLAUSE.search(prefix)
        or REQUIREMENT_CLAUSE.search(prefix)
        or NONASSERTIVE_SUFFIX.search(suffix)
    )


def _affirmative_phrases(line: str) -> set[str]:
    phrases: set[str] = set()
    for pattern in ASSERTION_PATTERNS:
        for match in pattern.finditer(line):
            if _is_nonassertive(line, match):
                continue
            phrase = re.sub(r"\s+", " ", match.group(0).strip().casefold())
            phrases.add(phrase)
    return phrases


def _structured_identity_gaps(root: Path, evidence_files: list[Path]) -> list[AdoptionGap]:
    gaps: list[AdoptionGap] = []
    for path in evidence_files:
        relative = str(path.relative_to(root)).replace("\\", "/")
        try:
            record = read_yaml(path)
        except Exception as exc:
            gaps.append(
                AdoptionGap(
                    "record.unparseable",
                    "manual_migration",
                    f"Evidence record cannot be parsed automatically: {exc}",
                    relative,
                    False,
                )
            )
            continue
        if not isinstance(record, dict):
            continue
        creator = record.get("created_by")
        if not isinstance(creator, dict) or not creator.get("type") or not creator.get("id"):
            gaps.append(
                AdoptionGap(
                    "identity.creator_missing",
                    "identity_independence",
                    "Evidence record lacks durable creator type and identity",
                    relative,
                    False,
                )
            )
        evidence_class = record.get("class")
        details = record.get("details")
        if evidence_class in {"REPRODUCTION", "REVIEW_EXTERNAL"}:
            required = set(INDEPENDENCE_KEYS)
            if not isinstance(details, dict) or not required.issubset(details):
                label = "Reproduction" if evidence_class == "REPRODUCTION" else "External review"
                gaps.append(
                    AdoptionGap(
                        "independence.metadata_missing",
                        "identity_independence",
                        f"{label} record lacks the complete structured identity and independence boundary",
                        relative,
                        False,
                        {"required_keys": sorted(required)},
                    )
                )
        if evidence_class == "REPRODUCTION" and isinstance(creator, dict) and creator.get("type") == "agent":
            gaps.append(
                AdoptionGap(
                    "independence.agent_creator",
                    "identity_independence",
                    "Agent-created reproduction evidence records provenance but cannot establish independent reproduction",
                    relative,
                    False,
                )
            )
        if evidence_class == "REVIEW_EXTERNAL":
            reviewer = record.get("reviewer")
            if not isinstance(reviewer, dict) or reviewer.get("type") not in {"human", "venue"} or not reviewer.get("id"):
                gaps.append(
                    AdoptionGap(
                        "identity.external_reviewer_missing",
                        "identity_independence",
                        "External review record lacks a named human reviewer or venue",
                        relative,
                        False,
                    )
                )
    return gaps


def _unstructured_identity_gaps(root: Path, files: list[Path]) -> list[AdoptionGap]:
    gaps: list[AdoptionGap] = []
    for path in files:
        if path.suffix.lower() not in TEXT_SUFFIXES:
            continue
        relative = str(path.relative_to(root)).replace("\\", "/")
        content = read_adoption_text(path)
        if content is None:
            continue
        matched: set[str] = set()
        for line in content.splitlines():
            matched.update(_affirmative_phrases(line))
        if matched:
            gaps.append(
                AdoptionGap(
                    "identity.unstructured_assertion",
                    "identity_independence",
                    "Affirmative independence or external-review language exists without governed identity metadata",
                    relative,
                    False,
                    {"phrases": sorted(matched)},
                )
            )
    return gaps


def identity_gaps(root: Path, files: list[Path]) -> list[AdoptionGap]:
    evidence_root = root / "audit/evidence"
    evidence_files = (
        sorted([*evidence_root.rglob("*.yaml"), *evidence_root.rglob("*.yml")])
        if evidence_root.is_dir()
        else []
    )
    if evidence_files:
        return _structured_identity_gaps(root, evidence_files)
    return _unstructured_identity_gaps(root, files)
