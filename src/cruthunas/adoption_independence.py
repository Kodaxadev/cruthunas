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
ACTOR_NOUN_PATTERNS = (
    re.compile(
        r"\bindependent"
        r"(?:\s+[A-Za-z0-9_+\-/]+){0,3}?\s+"
        r"(?:implementations?|verifiers?|certificates?|generators?|"
        r"verification\s+frameworks?)\b",
        re.IGNORECASE,
    ),
)
PROCESS_NOUN_PATTERNS = (
    re.compile(
        r"\bindependent\s+(?:audits?|checks?|reimplementations?|replications?|"
        r"reproductions?|reviews?|validations?|verifications?)\b",
        re.IGNORECASE,
    ),
    re.compile(r"\bexternal\s+reviews?\b", re.IGNORECASE),
)
COMPLETED_ACTION_PATTERNS = (
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
SENTENCE_BOUNDARY = re.compile(r"[.!?](?=[\"'\u201d\u2019)\]]*(?:\s|$))")
CLAUSE_TERMINATOR = re.compile(r"[.!?;](?=[\"'\u201d\u2019)\]]*(?:\s|$))")
CLAUSE_BOUNDARY = re.compile(r"[.!?;]|\bbut\b|\bhowever\b", re.IGNORECASE)
INTERROGATIVE_START = re.compile(
    r"^\s*(?:[-*+>]\s+|#+\s*)?(?:question\s*:|"
    r"(?:is|are|was|were|has|have|had|do|does|did|can|could|would|should|"
    r"will|may|might)\b|"
    r"(?:how|what|when|where|why)\s+"
    r"(?:is|are|was|were|has|have|had|do|does|did|can|could|would|should|"
    r"will|may|might)\b)",
    re.IGNORECASE,
)
UNCERTAINTY_PREFIX = re.compile(
    r"(?:^\s*(?:[-*+>]\s+|#+\s*)?whether\b|"
    r"\b(?:do|does|did)\s+not\s+know\s+whether\b|"
    r"\b(?:unclear|uncertain|undetermined|unknown)\s+whether\b)",
    re.IGNORECASE,
)
NEGATING_PREFIX = re.compile(
    r"(?:\b(?:(?:does|do|did)\s+not|doesn't|don't|didn't|cannot|can't)\s+"
    r"(?:establish|constitute|provide|demonstrate|claim)\b.*|"
    r"\bno\b(?:\s+\w+){0,4}\s+"
    r"(?:has|have|had|does|do|did|is|are|was|were)\s*|"
    r"\b(?:is|are|was|were|has|have|had|does|do|did)\s+(?:not|never)"
    r"(?:\s+(?:yet|still|be|been))*\s*|"
    r"\b(?:no|not|never|without|cannot|can't|isn't|aren't|wasn't|weren't|"
    r"hasn't|haven't|hadn't|doesn't|don't|didn't)"
    r"(?:\s+(?:yet|still|be|been))*\s*)$",
    re.IGNORECASE,
)
GOVERNING_REQUIREMENT_PREFIX = re.compile(
    r"(?:\b(?:must|should|shall|will|would|could|can|may|might)"
    r"(?:\s+(?:not|still|be|have|been|to)){0,4}|"
    r"\b(?:needs?|needed|requires?|required|awaits?|awaiting|pending|planned|"
    r"proposed))\s*$",
    re.IGNORECASE,
)
NONCOMPLETION_PREFIX = re.compile(
    r"(?:\bno\s+(?:evidence|record|documentation|proof)\s+of\s*|"
    r"\b(?:(?:is|are|was|were)\s+)?(?:failed|unable|attempted)\s+"
    r"(?:to\s+be|to)\s*|"
    r"\b(?:expected|intended|scheduled|planned)\b.{0,80}\bto"
    r"(?:\s+be)?\s*)$",
    re.IGNORECASE,
)
NEGATING_SUFFIX = re.compile(
    r"^[\s,;:()\-\u2013\u2014]*(?:(?:however|nevertheless|in\s+fact)"
    r"[\s,;:()\-\u2013\u2014]+)?(?:(?:is|are|was|were|has|have|had|does|do|did)"
    r"\s+(?:not|never)|cannot|can't|isn't|aren't|wasn't|weren't|hasn't|"
    r"haven't|hadn't|doesn't|don't|didn't)\b",
    re.IGNORECASE,
)
NONCOMPLETION_SUFFIX = re.compile(
    r"^[\s,;:()\-\u2013\u2014]*(?:(?:however|nevertheless|in\s+fact)"
    r"[\s,;:()\-\u2013\u2014]+)?(?:"
    r"(?:is|are|was|were|has|have|had)\s+yet\s+to\b|"
    r"remains?\s+(?:outstanding|unfinished|incomplete|unperformed)\b|"
    r"(?:(?:is|are|was|were)\s+)?(?:failed|unable)\s+to\b|"
    r"(?:is|are|was|were|has\s+been|have\s+been|had\s+been)\s+"
    r"(?:abandoned|cancelled|canceled)\b|"
    r"(?:refused|declined)\s+to\b|"
    r"unsuccessfully\b|"
    r"(?:is|are|was|were|has\s+been|have\s+been|had\s+been)\s+attempted\b"
    r".*\bbut\s+(?:failed|did\s+not\s+succeed)\b)",
    re.IGNORECASE,
)
NONASSERTIVE_SUFFIX = re.compile(
    r"^[\s,;:()\-\u2013\u2014]*(?:(?:is|are|was|were|remains?)\s+)?"
    r"(?:still\s+)?(?:required|needed|pending|awaiting|planned|proposed|"
    r"must|should|shall|will|would|could|can|may|might)\b",
    re.IGNORECASE,
)
PROGRESSIVE_PREFIX = re.compile(
    r"\b(?:is|are|was|were)\s+being\s*$",
    re.IGNORECASE,
)
INFINITIVE_PASSIVE_PREFIX = re.compile(r"\bto\s+be\s*$", re.IGNORECASE)
MODAL_CHAIN_PREFIX = re.compile(
    r"\b(?:can|could|may|might|must|shall|should|will|would)\b"
    r"[\s\S]{0,96}\b(?:be|been|have)\s*$",
    re.IGNORECASE,
)
MODAL_SCOPE = re.compile(
    r"\b(?:can|could|may|might|must|shall|should|will|would)\b[\s\S]{0,120}$",
    re.IGNORECASE,
)
COMPLETION_MODIFIER = (
    r"actually|already|also|eventually|fully|independently|now|separately|"
    r"successfully"
)
COMPLETION_MODIFIERS = rf"(?:(?:{COMPLETION_MODIFIER})\s+)*"
AGENT_BASE_ACTION = (
    r"audit|check|close|confirm|cross-?check|establish|implement|recompute|"
    r"referee|regenerate|reimplement|reject|replicate|reproduce|review|validate|"
    r"verify"
)
AGENT_PAST_ACTION = rf"(?:{INDEPENDENCE_ACTION}|rejected)"
AGENT_RESULT = r"agrees?|agreed|covers?|covered|matches?|matched|matching"
ACTOR_COMPLETION_SUFFIX = re.compile(
    rf"^[\s,;:()\-\u2013\u2014]*(?:"
    rf"(?:has|have|had)\s+{COMPLETION_MODIFIERS}{AGENT_PAST_ACTION}|"
    rf"did\s+{COMPLETION_MODIFIERS}(?:{AGENT_BASE_ACTION})|"
    rf"{COMPLETION_MODIFIERS}(?:{AGENT_PAST_ACTION}|{AGENT_RESULT}))\b",
    re.IGNORECASE,
)
ACTOR_COMPLETION_PREFIX = re.compile(
    rf"(?:\b(?:(?:has|have|had)\s+been|(?:is|are|was|were))\s+"
    rf"{COMPLETION_MODIFIERS}(?:{INDEPENDENCE_ACTION}|supported)\s+"
    r"(?:against|by|using|with)\s+"
    r"(?:(?:an?|the|\d+)\s+)?|"
    r"\bagreement\s+with\s+(?:(?:an?|the)\s+)?)$",
    re.IGNORECASE,
)
PROCESS_COMPLETION_SUFFIX = re.compile(
    rf"^[\s,;:()\-\u2013\u2014]*(?:"
    rf"(?:has|have|had)\s+(?:been\s+)?{COMPLETION_MODIFIERS}"
    r"(?:completed|concluded|finished|performed|succeeded)|"
    rf"(?:is|are|was|were)\s+{COMPLETION_MODIFIERS}"
    r"(?:complete|completed|concluded|finished|performed|successful)|"
    rf"{COMPLETION_MODIFIERS}(?:completed|concluded|finished|performed|"
    r"succeeded))\b",
    re.IGNORECASE,
)
NOUN_SUBJECT_PREFIX = re.compile(
    r"^\s*(?:[-*+>]\s+|#+\s*)?"
    r"(?:(?:an?|all|both|each|every|that|the|these|this|those)\s+)?"
    r"(?:(?:\d+|eight|five|four|nine|one|seven|six|ten|three|two)\s+)?"
    r"(?:[A-Za-z0-9_+\-/]+\s+and\s+)?$",
    re.IGNORECASE,
)


def _sentence_context(text: str, match: re.Match[str]) -> tuple[str, int, int]:
    start = 0
    end = len(text)
    for boundary in SENTENCE_BOUNDARY.finditer(text):
        if boundary.end() <= match.start():
            start = boundary.end()
        elif boundary.start() >= match.end():
            end = boundary.end()
            break
    return text[start:end], match.start() - start, match.end() - start


def _clause_prefix(sentence: str, match_start: int) -> str:
    return CLAUSE_BOUNDARY.split(sentence[:match_start])[-1]


def _is_question_context(sentence: str, match_start: int, match_end: int) -> bool:
    prefix = _clause_prefix(sentence, match_start)
    if INTERROGATIVE_START.search(prefix) or UNCERTAINTY_PREFIX.search(prefix):
        return True
    terminator = CLAUSE_TERMINATOR.search(sentence, match_end)
    return terminator is not None and terminator.group(0) == "?"


def _is_nonassertive(text: str, match: re.Match[str]) -> bool:
    sentence, match_start, match_end = _sentence_context(text, match)
    if _is_question_context(sentence, match_start, match_end):
        return True
    prefix = _clause_prefix(sentence, match_start)
    suffix = sentence[match_end : match_end + 100]
    return bool(
        NEGATING_PREFIX.search(prefix)
        or GOVERNING_REQUIREMENT_PREFIX.search(prefix)
        or NONCOMPLETION_PREFIX.search(prefix)
        or NEGATING_SUFFIX.search(suffix)
        or NONCOMPLETION_SUFFIX.search(suffix)
        or NONASSERTIVE_SUFFIX.search(suffix)
        or PROGRESSIVE_PREFIX.search(prefix)
        or INFINITIVE_PASSIVE_PREFIX.search(prefix)
        or MODAL_CHAIN_PREFIX.search(prefix)
    )


def _noun_context(text: str, match: re.Match[str]) -> tuple[str, str]:
    sentence, match_start, match_end = _sentence_context(text, match)
    prefix = _clause_prefix(sentence, match_start)
    suffix = sentence[match_end : match_end + 120]
    return prefix, suffix


def _has_noun_subject(prefix: str) -> bool:
    markdown_cell_prefix = prefix.rsplit("|", 1)[-1]
    return bool(NOUN_SUBJECT_PREFIX.fullmatch(markdown_cell_prefix))


def _actor_noun_has_completion(text: str, match: re.Match[str]) -> bool:
    prefix, suffix = _noun_context(text, match)
    if _has_noun_subject(prefix):
        return bool(ACTOR_COMPLETION_SUFFIX.search(suffix))
    return bool(
        not MODAL_SCOPE.search(prefix) and ACTOR_COMPLETION_PREFIX.search(prefix)
    )


def _process_noun_has_completion(text: str, match: re.Match[str]) -> bool:
    prefix, suffix = _noun_context(text, match)
    return bool(
        _has_noun_subject(prefix)
        and PROCESS_COMPLETION_SUFFIX.search(suffix)
    )


def _normalized_phrase(match: re.Match[str]) -> str:
    return re.sub(r"\s+", " ", match.group(0).strip().casefold())


def _affirmative_phrases(text: str) -> set[str]:
    phrases: set[str] = set()
    for pattern in ACTOR_NOUN_PATTERNS:
        for match in pattern.finditer(text):
            if _is_nonassertive(text, match) or not _actor_noun_has_completion(
                text, match
            ):
                continue
            phrases.add(_normalized_phrase(match))
    for pattern in PROCESS_NOUN_PATTERNS:
        for match in pattern.finditer(text):
            if _is_nonassertive(text, match) or not _process_noun_has_completion(
                text, match
            ):
                continue
            phrases.add(_normalized_phrase(match))
    for pattern in COMPLETED_ACTION_PATTERNS:
        for match in pattern.finditer(text):
            if _is_nonassertive(text, match):
                continue
            phrases.add(_normalized_phrase(match))
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


def _unstructured_identity_gaps(
    root: Path,
    files: list[Path],
    evidence_files: set[Path],
) -> list[AdoptionGap]:
    gaps: list[AdoptionGap] = []
    for path in files:
        if path in evidence_files or path.suffix.lower() not in TEXT_SUFFIXES:
            continue
        relative = str(path.relative_to(root)).replace("\\", "/")
        content = read_adoption_text(path)
        if content is None:
            continue
        matched: set[str] = set()
        matched.update(_affirmative_phrases(content))
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
    return [
        *_structured_identity_gaps(root, evidence_files),
        *_unstructured_identity_gaps(root, files, set(evidence_files)),
    ]
