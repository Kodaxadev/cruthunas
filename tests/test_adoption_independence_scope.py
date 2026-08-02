from __future__ import annotations

import pytest

from cruthunas.adoption_independence import _affirmative_phrases


@pytest.mark.parametrize(
    "text",
    [
        "The process ran independently; reviewed later.",
        "The process ran independently: reviewed later.",
        "The tool operated independently, reviewed by staff.",
        "The tool operated independently (reviewed by staff).",
        "The result was neither independently verified nor independently reproduced.",
        "The result was not independently verified, nor was it independently reproduced.",
        "The result may have been independently verified or separately independently reproduced.",
        "The result may have been independently verified and then independently reproduced.",
        "The result was neither independently verified, independently reproduced, nor independently checked.",
        "Neither the result was independently verified nor the certificate was independently reproduced.",
        "The result was neither independently verified nor was the certificate independently reproduced.",
        "The authors stated that the result was independently verified.",
        "The result was independently verified, according to the authors.",
        "According to the authors, the result was independently verified.",
        "The result, according to the authors, was independently verified.",
        "The result was independently verified, as reported by the authors.",
        "The result was independently verified, the authors stated.",
        "It was stated that the result was independently verified.",
        '"The result was independently verified," the authors stated.',
        "The authors asserted that the result was independently verified.",
        "As the authors wrote, the result was independently verified.",
        "As stated in the report, the result was independently verified.",
        "The result was by no means independently verified.",
        "Reportedly, after review, the result was independently verified.",
        "```text\nIndependent review was completed.\n```",
        "~~~~ text\nIndependent review was completed.\n~~~~",
        "````text\nIndependent review was completed.\n```\nstill code\n````",
        "```text\nIndependent review was completed.",
        "    Independent review was completed.",
        "A purportedly formal independent review was completed.",
        "An alleged formal independent review was completed.",
        "The result was independently verified and independently reproduced, according to the authors.",
        "The result was independently verified and independently reproduced, reportedly.",
        "The result was independently verified, independently reproduced, and independently checked, as reported by the authors.",
        "<!--\nContext\n\nIndependent review was completed.\n-->",
        "<!--\nContext\n\nIndependent review was completed.",
        "Independent review was completed and independent verification was completed, according to the authors.",
        "Independent audit concluded successfully and independent review was completed, reportedly.",
        "The independent reviewer checked the proof and the independent auditor confirmed the result, as reported by the authors.",
    ],
)
def test_eighth_cycle_nonassertions_are_excluded(text: str) -> None:
    assert not _affirmative_phrases(text)


@pytest.mark.parametrize(
    "text",
    [
        "Example: `Independent review was completed.`",
        "<!-- Independent review was completed. -->",
        "![Independent review was completed.](example.png)",
    ],
)
def test_literal_inline_examples_are_excluded(text: str) -> None:
    assert not _affirmative_phrases(text)


@pytest.mark.parametrize(
    "text, expected",
    [
        ("The result was not independently verified but was independently reproduced.", "independently reproduced"),
        ("The certificate was independently reviewed.", "independently reviewed"),
        ("The certificate was independently\u2014recomputed against the source.", "independently\u2014recomputed"),
        ("The result may have been independently verified, but the certificate was independently reproduced.", "independently reproduced"),
        ("The result was not only independently verified but also independently reproduced.", "independently reproduced"),
        ("The authors stated the theorem, but the result was independently verified.", "independently verified"),
        ("The authors independently verified the result.", "independently verified"),
        ("The result was independently **verified**.", "independently verified"),
        ("The result was **independently verified**.", "independently verified"),
        ("The *independent review* was completed.", "independent review"),
        ("[Independent review](review.md) was completed.", "independent review"),
        ("The _independent review_ was completed.", "independent review"),
        ("The result was __independently verified__.", "independently verified"),
        ("The result was independently verified, but the certificate may be independently reproduced.", "independently verified"),
        ("The result may have been independently verified, and the certificate was independently reproduced.", "independently reproduced"),
        ("Example: ``The result was independently verified.```", "independently verified"),
    ],
)
def test_eighth_cycle_affirmative_controls_are_reported(
    text: str,
    expected: str,
) -> None:
    assert expected in _affirmative_phrases(text)


def test_prose_after_fence_is_scanned_without_scanning_the_fence() -> None:
    text = (
        "```text\nIndependent review was completed.\n```\n"
        "The certificate was independently verified."
    )

    assert _affirmative_phrases(text) == {"independently verified"}


def test_single_newline_remains_a_supported_hard_wrap() -> None:
    assert _affirmative_phrases("Independent review\nwas completed.") == {
        "independent review"
    }


def test_non_markdown_text_retains_plain_text_scanning() -> None:
    text = '    print("The result was independently verified.")'

    assert _affirmative_phrases(text, markdown=False) == {"independently verified"}


def test_contrast_resets_preposed_attribution_scope() -> None:
    text = (
        "According to the authors, the theorem is old, but the certificate "
        "was independently verified."
    )

    assert _affirmative_phrases(text) == {"independently verified"}


def test_visible_prose_after_multiline_html_comment_is_scanned() -> None:
    text = (
        "<!--\ncommented material\n-->\n"
        "The certificate was independently verified."
    )

    assert _affirmative_phrases(text) == {"independently verified"}


def test_contrast_resets_preposed_attribution_for_process_nouns() -> None:
    text = (
        "According to the authors, independent review was completed, but "
        "independent verification was completed directly by the team."
    )

    assert _affirmative_phrases(text) == {"independent verification"}


@pytest.mark.parametrize(
    "text, expected",
    [
        (
            "Independent review was completed; independent verification was "
            "completed, reportedly.",
            {"independent review"},
        ),
        (
            "Independent review was completed, and the committee said independent "
            "verification was completed, reportedly.",
            {"independent review"},
        ),
        (
            "Independent review was completed.\n\nIndependent verification was "
            "completed, reportedly.",
            {"independent review"},
        ),
    ],
)
def test_noun_attribution_stops_at_unsupported_boundaries(
    text: str,
    expected: set[str],
) -> None:
    assert _affirmative_phrases(text) == expected


def test_coordinated_completed_nouns_remain_affirmative_without_exclusion() -> None:
    text = (
        "Independent review was completed and independent verification was "
        "completed directly by the team."
    )

    assert _affirmative_phrases(text) == {
        "independent review",
        "independent verification",
    }
