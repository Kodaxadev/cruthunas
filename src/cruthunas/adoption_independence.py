from __future__ import annotations

import re
from pathlib import Path

from .adoption_scan import TEXT_SUFFIXES, read_adoption_text
from .adoption_types import AdoptionGap
from .evidence_policy import INDEPENDENCE_KEYS
from .models import read_yaml


def _ci(pattern: str) -> re.Pattern[str]:
    return re.compile(pattern, re.IGNORECASE)


INDEPENDENCE_ACTION = (
    r"regenerated|reproduced|reimplemented|implemented|re-?verified|verified|"
    r"cross-?checked|checked|audited|reviewed|recomputed|validated|replicated|"
    r"confirmed|established|refereed|closed"
)
ATTRIBUTED_ACTION = rf"(?:{INDEPENDENCE_ACTION}|approved|found|supported)"
ATTRIBUTION_TAIL = rf"{ATTRIBUTED_ACTION}\s+(?:against|by|using|with)\s+" \
    r"(?:(?:an?|the|\d+)\s+)?(?:[A-Za-z0-9_+\-/]+\s+){0,3}"
INDEPENDENT_NOUN = r"\bindependent(?:\s+[A-Za-z0-9_+\-/]+){0,3}?\s+"
ACTOR_NOUN_PATTERN = _ci(
    INDEPENDENT_NOUN + r"(?:auditors?|referees?|reviewers?|validators?|verifiers?)\b",
)
ARTIFACT_NOUN_PATTERN = _ci(
    INDEPENDENT_NOUN
    + r"(?:certificates?|generators?|implementations?|verification\s+frameworks?)\b",
)
PROCESS_NOUN_PATTERN = _ci(
    r"(?:\bindependent(?:\s+[A-Za-z0-9_+\-/]+){0,2}?\s+"
    r"(?:audits?|checks?|reimplementations?|replications?|reproductions?|"
    r"reviews?|validations?|verifications?)\b|\bexternal\s+reviews?\b)",
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
CLAUSE_BOUNDARY = _ci(r"[.!?;]|,\s+(?:and|but)\b|\bbut\b|\bhowever\b")
INTERROGATIVE_START = _ci(
    r"^\s*(?:[-*+>]\s+|#+\s*)?(?:question\s*:|"
    r"(?:is|are|was|were|has|have|had|do|does|did|can|could|would|should|"
    r"will|may|might)\b|"
    r"(?:how|what|when|where|why)\s+"
    r"(?:is|are|was|were|has|have|had|do|does|did|can|could|would|should|"
    r"will|may|might)\b)",
)
UNCERTAINTY_PREFIX = _ci(
    r"(?:^\s*(?:[-*+>]\s+|#+\s*)?whether\b|"
    r"\b(?:do|does|did)\s+not\s+know\s+whether\b|"
    r"\b(?:unclear|uncertain|undetermined|unknown)\s+whether\b)",
)
EPISTEMIC_PREFIX = _ci(
    rf"(?:\b(?:allegedly|apparently|possibly|probably|purportedly|reportedly|"
    rf"supposedly)(?:\s+{ATTRIBUTION_TAIL})?\s*|"
    r"\b(?:appear(?:s|ed)?|seem(?:s|ed)?)\b[\s\S]{0,80}"
    rf"\bto\s+have\s+been(?:\s+{ATTRIBUTION_TAIL})?\s*|"
    r"\b(?:is|are|was|were)\s+(?:very\s+)?(?:believed|likely|said)\b"
    rf"[\s\S]{{0,80}}\bto\s+have\s+been(?:\s+{ATTRIBUTION_TAIL})?\s*|"
    r"\b(?:alleged|believed|claimed|reported|said|supposed)\s+that"
    rf"[\s\S]{{0,96}}\b(?:has|have|had|is|are|was|were)(?:\s+been)?"
    rf"(?:\s+{ATTRIBUTION_TAIL})?\s*)$",
)
NEGATING_PREFIX = _ci(
    r"(?:\b(?:(?:does|do|did)\s+not|doesn't|don't|didn't|cannot|can't)\s+"
    r"(?:establish|constitute|provide|demonstrate|claim)\b.*|"
    r"\bno\b(?:\s+\w+){0,4}\s+"
    r"(?:has|have|had|does|do|did|is|are|was|were)\s*|"
    r"\b(?:is|are|was|were|has|have|had|does|do|did)\s+(?:not|never)"
    r"(?:\s+(?:yet|still|be|been))*\s*|"
    r"\b(?:no|not|never|without|cannot|can't|isn't|aren't|wasn't|weren't|"
    r"hasn't|haven't|hadn't|doesn't|don't|didn't)"
    r"(?:\s+(?:yet|still|be|been))*\s*)$",
)
GOVERNING_REQUIREMENT_PREFIX = _ci(
    r"(?:\b(?:must|should|shall|will|would|could|can|may|might)"
    r"(?:\s+(?:not|still|be|have|been|to)){0,4}|"
    r"\b(?:needs?|needed|requires?|required|awaits?|awaiting|pending|planned|"
    r"proposed))\s*$",
)
NONCOMPLETION_PREFIX = _ci(
    r"(?:\bno\s+(?:evidence|record|documentation|proof)\s+of\s*|"
    r"\b(?:(?:is|are|was|were)\s+)?(?:failed|unable|attempted)\s+"
    r"(?:to\s+be|to)\s*|"
    r"\b(?:expected|intended|scheduled|planned)\b.{0,80}\bto"
    r"(?:\s+be)?\s*)$",
)
NEGATING_SUFFIX = _ci(
    r"^[\s,;:()\-\u2013\u2014]*(?:(?:however|nevertheless|in\s+fact)"
    r"[\s,;:()\-\u2013\u2014]+)?(?:(?:is|are|was|were|has|have|had|does|do|did)"
    r"\s+(?:not|never)|cannot|can't|isn't|aren't|wasn't|weren't|hasn't|"
    r"haven't|hadn't|doesn't|don't|didn't)\b",
)
NONCOMPLETION_SUFFIX = _ci(
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
)
NONASSERTIVE_SUFFIX = _ci(
    r"^[\s,;:()\-\u2013\u2014]*(?:(?:is|are|was|were|remains?)\s+)?"
    r"(?:still\s+)?(?:required|needed|pending|awaiting|planned|proposed|"
    r"must|should|shall|will|would|could|can|may|might)\b",
)
PROGRESSIVE_PREFIX = _ci(r"\b(?:is|are|was|were)\s+being\s*$")
INFINITIVE_PASSIVE_PREFIX = re.compile(r"\bto\s+be\s*$", re.IGNORECASE)
MODAL_CHAIN_PREFIX = _ci(
    r"\b(?:can|could|may|might|must|shall|should|will|would)\b"
    r"[\s\S]{0,96}\b(?:be|been|have)\s*$",
)
MODAL_SCOPE = _ci(r"\b(?:can|could|may|might|must|shall|should|will|would)\b[\s\S]{0,120}$")
COMPLETION_MODIFIER = (
    r"actually|already|also|eventually|fully|independently|now|separately|"
    r"successfully"
)
COMPLETION_MODIFIERS = rf"(?:(?:{COMPLETION_MODIFIER})\s+)*"
AGENT_BASE_ACTION = (
    r"approve|audit|check|close|confirm|cross-?check|establish|find|implement|recompute|"
    r"referee|regenerate|reimplement|reject|replicate|reproduce|review|validate|verify"
)
AGENT_PAST_ACTION = rf"(?:{INDEPENDENCE_ACTION}|approved|found|rejected)"
AGENT_RESULT = r"agrees?|agreed|covers?|covered|matches?|matched|matching"
ACTOR_COMPLETION_SUFFIX = _ci(
    rf"^[\s,;:()\-\u2013\u2014]*(?:"
    rf"(?:has|have|had)\s+{COMPLETION_MODIFIERS}{AGENT_PAST_ACTION}|"
    rf"did\s+{COMPLETION_MODIFIERS}(?:{AGENT_BASE_ACTION})|"
    rf"{COMPLETION_MODIFIERS}(?:{AGENT_PAST_ACTION}|{AGENT_RESULT}))\b",
)
ACTOR_COMPLETION_PREFIX = _ci(
    rf"(?:\b(?:(?:has|have|had)\s+been|(?:is|are|was|were))\s+"
    rf"{COMPLETION_MODIFIERS}{ATTRIBUTION_TAIL}|"
    r"\bagreement\s+with\s+(?:(?:an?|the)\s+)?)$",
)
PROCESS_COMPLETION_SUFFIX = _ci(
    rf"^[\s,;:()\-\u2013\u2014]*(?:"
    rf"(?:has|have|had)\s+(?:been\s+)?{COMPLETION_MODIFIERS}"
    r"(?:completed|concluded|finished|performed|succeeded)|"
    rf"(?:is|are|was|were)\s+{COMPLETION_MODIFIERS}"
    r"(?:complete|completed|concluded|finished|performed|successful)|"
    rf"(?:has|have|had)\s+{COMPLETION_MODIFIERS}(?:approved|confirmed|found)|"
    rf"{COMPLETION_MODIFIERS}(?:approved|completed|concluded|confirmed|finished|found|"
    r"performed|succeeded))\b",
)
ARTIFACT_RESULT_SUFFIX = _ci(
    rf"^[\s,;:()\-\u2013\u2014]*(?:{COMPLETION_MODIFIERS}"
    rf"(?:{AGENT_PAST_ACTION}|{AGENT_RESULT}))\b",
)
SUBJECT_TOKEN = re.compile(r"[A-Za-z0-9][A-Za-z0-9_+\-/]*")
SUBJECT_DETERMINERS = {
    "a", "all", "an", "both", "each", "eight", "every", "five", "four",
    "nine", "one", "seven", "six", "ten", "that", "the", "these", "this",
    "those", "three", "two"}
SUBJECT_ORDINALS = {"first", "second", "third", "fourth", "fifth", "sixth", "seventh", "eighth", "ninth", "tenth"}
SUBJECT_EMBEDDERS = {"about", "concerning", "for", "of", "regarding", "toward", "towards"}
MODIFIER_SUFFIXES = ("al", "ary", "ed", "ent", "ic", "ical", "ive", "ory", "ous", "ly")


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
        or EPISTEMIC_PREFIX.search(prefix)
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
    cell = prefix.rsplit("|", 1)[-1]
    cell = re.sub(r"^\s*(?:[-*+>]\s+|#+\s*)?", "", cell).strip()
    tokens = SUBJECT_TOKEN.findall(cell)
    residue = SUBJECT_TOKEN.sub("", cell).strip(" \t*_`")
    if residue or any(token.casefold() in SUBJECT_EMBEDDERS for token in tokens):
        return False
    if len(tokens) == 2 and tokens[1].casefold() == "and":
        return True
    if tokens and tokens[0].casefold() in SUBJECT_DETERMINERS:
        tokens = tokens[1:]
    if len(tokens) > 3:
        return False
    return all(
        token.isdigit() or token.casefold() in SUBJECT_ORDINALS
        or token.casefold().endswith(MODIFIER_SUFFIXES) for token in tokens
    )


def _actor_noun_has_completion(text: str, match: re.Match[str]) -> bool:
    prefix, suffix = _noun_context(text, match)
    if _has_noun_subject(prefix):
        return bool(ACTOR_COMPLETION_SUFFIX.search(suffix))
    return bool(not MODAL_SCOPE.search(prefix) and ACTOR_COMPLETION_PREFIX.search(prefix))


def _artifact_noun_has_completion(text: str, match: re.Match[str]) -> bool:
    prefix, suffix = _noun_context(text, match)
    if _has_noun_subject(prefix):
        return bool(ARTIFACT_RESULT_SUFFIX.search(suffix))
    return bool(not MODAL_SCOPE.search(prefix) and ACTOR_COMPLETION_PREFIX.search(prefix))


def _process_noun_has_completion(text: str, match: re.Match[str]) -> bool:
    prefix, suffix = _noun_context(text, match)
    return bool(_has_noun_subject(prefix) and PROCESS_COMPLETION_SUFFIX.search(suffix))


def _normalized_phrase(match: re.Match[str]) -> str:
    return re.sub(r"\s+", " ", match.group(0).strip().casefold())


def _affirmative_phrases(text: str) -> set[str]:
    phrases: set[str] = set()
    noun_rules = (
        (ACTOR_NOUN_PATTERN, _actor_noun_has_completion),
        (ARTIFACT_NOUN_PATTERN, _artifact_noun_has_completion),
        (PROCESS_NOUN_PATTERN, _process_noun_has_completion),
    )
    for pattern, completion_rule in noun_rules:
        for match in pattern.finditer(text):
            if _is_nonassertive(text, match) or not completion_rule(text, match):
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
    evidence_files = sorted(
        [*evidence_root.rglob("*.yaml"), *evidence_root.rglob("*.yml")]
    ) if evidence_root.is_dir() else []
    return [
        *_structured_identity_gaps(root, evidence_files),
        *_unstructured_identity_gaps(root, files, set(evidence_files)),
    ]
