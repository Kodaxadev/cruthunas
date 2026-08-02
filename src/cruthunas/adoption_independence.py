from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from .adoption_prose import prose_blocks
from .adoption_scan import TEXT_SUFFIXES, read_adoption_text
from .adoption_types import AdoptionGap
from .evidence_policy import INDEPENDENCE_KEYS
from .models import read_yaml


def _ci(pattern: str) -> re.Pattern[str]:
    return re.compile(pattern, re.IGNORECASE)


ACTION = (
    r"regenerated|reproduced|reimplemented|implemented|re-?verified|verified|"
    r"cross-?checked|checked|audited|reviewed|recomputed|validated|replicated|"
    r"confirmed|established|refereed|closed"
)
FORWARD_ACTION = _ci(rf"\bindependently(?:\s+|[\u2013\u2014])(?:{ACTION})\b")
REVERSE_ACTION = _ci(rf"\b(?:{ACTION})\b\s+independently\b")
SENTENCE_BOUNDARY = re.compile(r"[.!?](?=[\"'\u201d\u2019)\]]*(?:\s|$))")
CONTRAST = _ci(r"(?:,\s*)?\b(?:but|however|nevertheless)\b(?:\s+also)?")
SCOPE_BREAK = re.compile(r";")
SUBJECT_RESET = _ci(
    r"(?:,\s*|\s+)\b(?:and|or)\s+(?=(?:(?:an?|the|this|that|these|those)\s+)?"
    r"[A-Za-z0-9_-]+\s+(?:is|are|was|were|has|have|had|does|do|did)\b)"
)
INTERROGATIVE = _ci(
    r"^\s*(?:[-+>]\s+|#+\s*)?(?:question\s*:|whether\b|"
    r"(?:is|are|was|were|has|have|had|do|does|did|can|could|would|should|"
    r"will|may|might)\b|(?:how|what|when|where|why)\s+(?:is|are|was|were|"
    r"has|have|had|do|does|did|can|could|would|should|will|may|might)\b)"
)
UNCERTAINTY = _ci(r"\b(?:do|does|did)\s+not\s+know\s+whether\b|"
                  r"\b(?:unclear|uncertain|undetermined|unknown)\s+whether\b|"
                  r"\bwhether\b[\s\S]{0,120}$")
NEGATION = _ci(
    r"\bneither\b[\s\S]{0,120}$|\bno\s+(?:evidence|record|documentation|proof)"
    r"\s+of[\s\S]{0,80}$|^\s*no\b(?:\s+\w+){0,5}\s+"
    r"(?:has|have|had|does|do|did|is|are|was|were)\s*$|"
    r"\b(?:is|are|was|were|has|have|had|does|do|did)\s+"
    r"(?:not(?!\s+only\b)|never)(?:\s+(?:yet|still|be|been))*\s*$|"
    r"\b(?:cannot|can't|isn't|aren't|wasn't|weren't|hasn't|haven't|hadn't|"
    r"doesn't|don't|didn't)(?:\s+(?:yet|still|be|been))*\s*$|"
    r"\b(?:by\s+no\s+means|anything\s+but|hardly|scarcely)\s*$"
)
MODAL = _ci(r"\b(?:can|could|may|might|must|shall|should|will|would)\b[\s\S]{0,120}$")
FUTURE = _ci(r"\b(?:expected|intended|scheduled|planned|hopes?|plans?)\b"
             r"[\s\S]{0,120}(?:\bto(?:\s+be)?\s*)$")
EVIDENTIAL = _ci(
    r"\b(?:allegedly|apparently|possibly|probably|purportedly|reportedly|"
    r"supposedly)\s*$|\b(?:alleged|apparent|possible|probable|"
    r"purported|reported|supposed)\s+$|\b(?:appear(?:s|ed)?|seem(?:s|ed)?)\b"
    r"[\s\S]{0,100}\bto\s+have\s+been[\s\S]{0,60}$|"
    r"\b(?:is|are|was|were)\s+(?:believed|likely|said)\b[\s\S]{0,100}"
    r"\bto\s+have\s+been[\s\S]{0,60}$|^\s*(?:allegedly|apparently|possibly|"
    r"probably|purportedly|reportedly|supposedly)\b[\s\S]{0,120}$|"
    r"\b(?:is|are|was|were|has|have|had)(?:\s+been)?\s+(?:allegedly|apparently|"
    r"possibly|probably|purportedly|reportedly|supposedly)\b[\s\S]{0,80}$"
)
REPORTING = r"allege(?:d|s)?|assert(?:ed|s)?|believe(?:d|s)?|claim(?:ed|s)?|maintain(?:ed|s)?|note(?:d|s)?|report(?:ed|s)?|say|says|said|states|stated|suggest(?:ed|s)?|write|writes|wrote"
ATTRIBUTOR = r"authors?|auditors?|maintainers?|papers?|reports?|researchers?|reviewers?|teams?|we|they|he|she|it"
ATTRIBUTION_PREFIX = _ci(
    rf"(?:\b(?:the\s+)?(?:{ATTRIBUTOR})\s+(?:{REPORTING})\b(?:\s+that)?"
    rf"[\s\S]{{0,120}}$|\bit\s+(?:is|was|has\s+been)\s+(?:alleged|asserted|"
    rf"believed|claimed|noted|reported|said|stated|suggested)\s+that[\s\S]{{0,120}}$|"
    r"\baccording\s+to\b[\s\S]{0,120}$|\bas\s+(?:(?:reported|stated|noted|claimed)"
    r"\s+(?:by|in)|[\w -]+\s+"
    rf"(?:{REPORTING}))\b[\s\S]{{0,120}}$)"
)
ATTRIBUTION_SUFFIX = _ci(
    rf"^[\s,;:()\"'\u201c\u201d-]*(?:according\s+to\b|as\s+(?:reported|stated|noted|"
    rf"claimed)\s+(?:by|in)\b|"
    rf"(?:the\s+)?(?:{ATTRIBUTOR})\s+(?:{REPORTING})\b|(?:allegedly|apparently|possibly|"
    r"probably|purportedly|reportedly|supposedly)\b)"
)
POSTPOSED_NOUN_TAIL = _ci(
    r"^\s*(?:(?:an?|the|this|that|these|those)\s+)?"
    r"(?:[A-Za-z0-9_-]+\s*){1,6},"
)
NEGATING_SUFFIX = _ci(r"^[\s,()\-\u2013\u2014]*(?:(?:is|are|was|were|has|have|had|"
                      r"does|do|did)\s+(?:not|never)|cannot|can't|failed\b)")
NONCOMPLETION_SUFFIX = _ci(
    r"^[\s,()\-\u2013\u2014]*(?:(?:is|are|was|were|has|have|had)\s+yet\s+to\b|"
    r"remains?\s+(?:outstanding|unfinished|incomplete|unperformed|underway|in\s+progress)\b|"
    r"(?:(?:is|are|was|were)\s+)?(?:failed|unable)\s+to\b|(?:is|are|was|were|"
    r"has\s+been|have\s+been|had\s+been)\s+(?:abandoned|cancelled|canceled|attempted)\b|"
    r"(?:refused|declined)\s+to\b|unsuccessfully\b)"
)
INCOMPLETE_PREFIX = _ci(r"\b(?:is|are|was|were)\s+being\s*$|\bto\s+be\s*$|"
                        r"\b(?:failed|unable|attempted)\s+(?:to\s+be|to)\s*$")
COORDINATION = _ci(
    r"^\s*(?:(?:,\s*)?(?:and|or)\s+(?:(?:also|again|then|separately|"
    r"subsequently)\s+)?|(?:,\s*)?nor(?:\s+(?:was|were|is|are|has|have|had)"
    r"\s+(?:it|they)|\s+(?:[A-Za-z0-9_-]+\s+){1,5})?\s+|,\s*)$"
)
NOUN_COORDINATION = _ci(
    r"^\s*(?:(?:(?:an?|the|this|that|these|those)\s+)?"
    r"(?:[A-Za-z0-9_-]+\s+){1,6})?(?:,\s*)?(?:and|or|nor)\s+"
    r"(?:(?:an?|the)\s+)?$"
)

INDEPENDENT_NOUN = r"\bindependent(?:\s+[A-Za-z0-9_+\-/]+){0,3}?\s+"
ACTOR_NOUN = _ci(INDEPENDENT_NOUN + r"(?:auditors?|referees?|reviewers?|validators?|verifiers?)\b")
ARTIFACT_NOUN = _ci(INDEPENDENT_NOUN + r"(?:certificates?|generators?|implementations?|verification\s+frameworks?)\b")
PROCESS_NOUN = _ci(r"(?:\bindependent(?:\s+[A-Za-z0-9_+\-/]+){0,2}?\s+(?:audits?|"
                   r"checks?|reimplementations?|replications?|reproductions?|reviews?|"
                   r"validations?|verifications?)\b|\bexternal\s+reviews?\b)")
MODIFIER = r"(?:(?:actually|already|also|eventually|fully|independently|now|separately|successfully)\s+)*"
PAST_ACTION = rf"(?:{ACTION}|approved|found|rejected|supported)"
BASE_ACTION = r"approve|audit|check|close|confirm|cross-?check|establish|find|implement|recompute|referee|regenerate|reimplement|reject|replicate|reproduce|review|validate|verify"
RESULT = r"agrees?|agreed|covers?|covered|matches?|matched|matching"
ACTOR_SUFFIX = _ci(rf"^[\s,;()\-\u2013\u2014]*(?:(?:has|have|had)\s+{MODIFIER}{PAST_ACTION}|"
                   rf"did\s+{MODIFIER}(?:{BASE_ACTION})|{MODIFIER}(?:{PAST_ACTION}|{RESULT}))\b")
PASSIVE_PREFIX = _ci(rf"\b(?:(?:has|have|had)\s+been|is|are|was|were)\s+{MODIFIER}"
                     rf"(?:{PAST_ACTION})\s+(?:against|by|using|with)\s+(?:(?:an?|the)\s+)?"
                     r"(?:[A-Za-z0-9][A-Za-z0-9-]*\s+){0,2}$")
AGREEMENT_PREFIX = _ci(r"\bagreement\s+with\s+(?:(?:an?|the)\s+)?$")
PROCESS_SUFFIX = _ci(rf"^[\s,;()\-\u2013\u2014]*(?:(?:has|have|had)\s+(?:been\s+)?{MODIFIER}"
                     r"(?:completed|concluded|finished|performed|succeeded)|(?:is|are|was|were)\s+"
                     rf"{MODIFIER}(?:complete|completed|concluded|finished|performed|successful)|"
                     rf"(?:has|have|had)\s+{MODIFIER}(?:approved|confirmed|found)|{MODIFIER}"
                     r"(?:approved|completed|concluded|confirmed|finished|found|performed|succeeded))\b")
ARTIFACT_SUFFIX = _ci(rf"^[\s,;()\-\u2013\u2014]*{MODIFIER}(?:{PAST_ACTION}|{RESULT})\b")
SUBJECT_TOKEN = re.compile(r"[A-Za-z0-9][A-Za-z0-9_+\-/]*")
NOUN_SUBJECT_COORDINATOR = _ci(
    r"(?:,\s*|\b(?:and|or|nor)\b\s+(?:(?:an?|the)\s+)?)$"
)
DETERMINERS = {"a", "all", "an", "both", "each", "eight", "every", "five", "four", "nine", "one", "seven", "six", "ten", "that", "the", "these", "this", "those", "three", "two"}
ORDINALS = {"first", "second", "third", "fourth", "fifth", "sixth", "seventh", "eighth", "ninth", "tenth"}
EMBEDDERS = {"about", "concerning", "for", "of", "regarding", "toward", "towards"}
MODIFIER_SUFFIXES = ("al", "ary", "ed", "ent", "ic", "ical", "ive", "ory", "ous", "ly")
NOUN_HEDGES = {"alleged", "allegedly", "apparent", "apparently", "claimed", "possible",
               "possibly", "probable", "probably", "purported", "purportedly", "reported",
               "reportedly", "supposed", "supposedly"}


@dataclass(frozen=True)
class AssertionCandidate:
    start: int
    end: int
    completion_end: int
    phrase: str
    kind: str
    noun_hedged: bool = False


def _sentence_context(text: str, start_at: int, end_at: int) -> tuple[str, int, int]:
    start, end = 0, len(text)
    for boundary in SENTENCE_BOUNDARY.finditer(text):
        if boundary.end() <= start_at:
            start = boundary.end()
        elif boundary.start() >= end_at:
            end = boundary.end()
            break
    return text[start:end], start_at - start, end_at - start


def _segment_prefix(sentence: str, start: int) -> str:
    prefix = sentence[:start]
    resets = [*CONTRAST.finditer(prefix), *SUBJECT_RESET.finditer(prefix),
              *SCOPE_BREAK.finditer(prefix)]
    return prefix[max(resets, key=lambda match: match.end()).end():] if resets else prefix


def _directly_excluded(sentence: str, start: int, end: int) -> bool:
    prefix = _segment_prefix(sentence, start)
    suffix = sentence[end:end + 140]
    terminator = re.search(r"[!?;]", sentence[end:])
    question = bool(INTERROGATIVE.search(sentence.lstrip(' \t\"\u201c')) or
                    UNCERTAINTY.search(prefix) or
                    (terminator is not None and terminator.group(0) == "?"))
    return question or any(pattern.search(prefix) for pattern in (
        NEGATION, MODAL, FUTURE, EVIDENTIAL, ATTRIBUTION_PREFIX, INCOMPLETE_PREFIX,
    )) or any(pattern.search(suffix) for pattern in (
        NEGATING_SUFFIX, NONCOMPLETION_SUFFIX, ATTRIBUTION_SUFFIX,
    ))


def _action_candidates(text: str) -> list[AssertionCandidate]:
    matches = [match for pattern in (FORWARD_ACTION, REVERSE_ACTION) for match in pattern.finditer(text)]
    candidates: list[AssertionCandidate] = []
    for match in sorted(matches, key=lambda item: (item.start(), -(item.end() - item.start()))):
        if candidates and match.start() < candidates[-1].end:
            continue
        phrase = re.sub(r"\s+", " ", match.group(0).strip().casefold())
        candidates.append(AssertionCandidate(
            match.start(), match.end(), match.end(), phrase, "action",
        ))
    return candidates


def _supported_coordination(
    text: str,
    left: AssertionCandidate,
    right: AssertionCandidate,
) -> bool:
    bridge = text[left.completion_end:right.start]
    if COORDINATION.fullmatch(bridge):
        return True
    return left.kind != "action" and right.kind != "action" and bool(
        NOUN_COORDINATION.fullmatch(bridge)
    )


def _has_postposed_scope(sentence: str, end: int, kind: str) -> bool:
    suffix = sentence[end:end + 140]
    if ATTRIBUTION_SUFFIX.search(suffix):
        return True
    if kind == "action":
        return False
    nominal_tail = POSTPOSED_NOUN_TAIL.match(suffix)
    return bool(nominal_tail and ATTRIBUTION_SUFFIX.search(
        suffix[nominal_tail.end() - 1:],
    ))


def _candidate_exclusions(text: str, candidates: list[AssertionCandidate]) -> list[bool]:
    excluded: list[bool] = []
    postposed: list[bool] = []
    for index, candidate in enumerate(candidates):
        sentence, start, end = _sentence_context(
            text, candidate.start, candidate.completion_end,
        )
        has_postposed = _has_postposed_scope(sentence, end, candidate.kind)
        direct = (
            candidate.noun_hedged
            or _directly_excluded(sentence, start, end)
            or has_postposed
        )
        postposed.append(has_postposed)
        if not direct and index:
            prior = candidates[index - 1]
            if _supported_coordination(text, prior, candidate):
                direct = excluded[index - 1]
        excluded.append(direct)
    for index in range(len(candidates) - 2, -1, -1):
        if postposed[index + 1] and _supported_coordination(
            text, candidates[index], candidates[index + 1],
        ):
            excluded[index] = True
            postposed[index] = True
    return excluded


def _noun_context(text: str, match: re.Match[str]) -> tuple[str, str, str, int, int]:
    sentence, start, end = _sentence_context(text, match.start(), match.end())
    return sentence, _segment_prefix(sentence, start), sentence[end:end + 140], start, end


def _has_noun_subject(prefix: str) -> bool:
    if NOUN_SUBJECT_COORDINATOR.search(prefix):
        return True
    cell = re.sub(r"^\s*(?:[-+>]\s+|#+\s*)?", "", prefix.rsplit("|", 1)[-1]).strip()
    tokens = SUBJECT_TOKEN.findall(cell)
    if SUBJECT_TOKEN.sub("", cell).strip(" \t_`") or any(t.casefold() in EMBEDDERS for t in tokens):
        return False
    if len(tokens) == 2 and tokens[1].casefold() == "and":
        return True
    if tokens and tokens[0].casefold() in DETERMINERS:
        tokens = tokens[1:]
    return len(tokens) <= 3 and all(t.isdigit() or t.casefold() in ORDINALS or
                                    t.casefold().endswith(MODIFIER_SUFFIXES) for t in tokens)


def _noun_candidate(
    text: str,
    match: re.Match[str],
    kind: str,
) -> AssertionCandidate | None:
    _, prefix, suffix, _, _ = _noun_context(text, match)
    subject = _has_noun_subject(prefix)
    completion: re.Match[str] | None = None
    if kind == "process":
        if not subject:
            return None
        completion = PROCESS_SUFFIX.search(suffix)
    elif subject:
        completion = (ACTOR_SUFFIX if kind == "actor" else ARTIFACT_SUFFIX).search(suffix)
    elif not MODAL.search(prefix) and (PASSIVE_PREFIX.search(prefix) or AGREEMENT_PREFIX.search(prefix)):
        completion_end = match.end()
    else:
        return None
    if subject and completion is None:
        return None
    if completion is not None:
        completion_end = match.end() + completion.end()
    hedged = subject and any(
        token.casefold() in NOUN_HEDGES for token in SUBJECT_TOKEN.findall(prefix)
    )
    return AssertionCandidate(
        match.start(), match.end(), completion_end, _normalized(match), kind, hedged,
    )


def _normalized(match: re.Match[str]) -> str:
    return re.sub(r"\s+", " ", match.group(0).strip().casefold())


def _affirmative_phrases(text: str, *, markdown: bool = True) -> set[str]:
    phrases: set[str] = set()
    for block in prose_blocks(text, markdown=markdown):
        candidates = _action_candidates(block)
        for pattern, kind in ((ACTOR_NOUN, "actor"), (ARTIFACT_NOUN, "artifact"),
                              (PROCESS_NOUN, "process")):
            for match in pattern.finditer(block):
                candidate = _noun_candidate(block, match, kind)
                if candidate is not None:
                    candidates.append(candidate)
        candidates.sort(key=lambda candidate: (candidate.start, candidate.end))
        for candidate, excluded in zip(candidates, _candidate_exclusions(block, candidates)):
            if not excluded:
                phrases.add(candidate.phrase)
    return phrases


def _structured_identity_gaps(root: Path, evidence_files: list[Path]) -> list[AdoptionGap]:
    gaps: list[AdoptionGap] = []
    for path in evidence_files:
        relative = str(path.relative_to(root)).replace("\\", "/")
        try:
            record = read_yaml(path)
        except Exception as exc:
            gaps.append(AdoptionGap(
                "record.unparseable", "manual_migration",
                f"Evidence record cannot be parsed automatically: {exc}", relative, False,
            ))
            continue
        if not isinstance(record, dict):
            continue
        creator = record.get("created_by")
        if not isinstance(creator, dict) or not creator.get("type") or not creator.get("id"):
            gaps.append(AdoptionGap(
                "identity.creator_missing", "identity_independence",
                "Evidence record lacks durable creator type and identity", relative, False,
            ))
        evidence_class = record.get("class")
        details = record.get("details")
        if evidence_class in {"REPRODUCTION", "REVIEW_EXTERNAL"}:
            required = set(INDEPENDENCE_KEYS)
            if not isinstance(details, dict) or not required.issubset(details):
                label = "Reproduction" if evidence_class == "REPRODUCTION" else "External review"
                gaps.append(AdoptionGap(
                    "independence.metadata_missing", "identity_independence",
                    f"{label} record lacks the complete structured identity and independence boundary",
                    relative, False, {"required_keys": sorted(required)},
                ))
        if evidence_class == "REPRODUCTION" and isinstance(creator, dict) and creator.get("type") == "agent":
            gaps.append(AdoptionGap(
                "independence.agent_creator", "identity_independence",
                "Agent-created reproduction evidence records provenance but cannot establish independent reproduction",
                relative, False,
            ))
        if evidence_class == "REVIEW_EXTERNAL":
            reviewer = record.get("reviewer")
            if not isinstance(reviewer, dict) or reviewer.get("type") not in {"human", "venue"} or not reviewer.get("id"):
                gaps.append(AdoptionGap(
                    "identity.external_reviewer_missing", "identity_independence",
                    "External review record lacks a named human reviewer or venue", relative, False,
                ))
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
        matched.update(_affirmative_phrases(content, markdown=path.suffix.lower() == ".md"))
        if matched:
            gaps.append(AdoptionGap(
                "identity.unstructured_assertion", "identity_independence",
                "Affirmative independence or external-review language exists without governed identity metadata",
                relative, False, {"phrases": sorted(matched)},
            ))
    return gaps


def identity_gaps(root: Path, files: list[Path]) -> list[AdoptionGap]:
    evidence_root = root / "audit/evidence"
    evidence_files = sorted([*evidence_root.rglob("*.yaml"), *evidence_root.rglob("*.yml")]
                            ) if evidence_root.is_dir() else []
    return [
        *_structured_identity_gaps(root, evidence_files),
        *_unstructured_identity_gaps(root, files, set(evidence_files)),
    ]
