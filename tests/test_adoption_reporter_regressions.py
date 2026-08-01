from __future__ import annotations

from pathlib import Path

import pytest

from cruthunas.adoption import adoption_gap_report


def _write_fixture(root: Path, text: str) -> None:
    path = root / "docs/fixture.md"
    path.parent.mkdir(parents=True)
    path.write_text(text, encoding="utf-8")


def _gaps(root: Path, code: str):
    return [gap for gap in adoption_gap_report(root).gaps if gap.code == code]


def test_dotted_historical_id_is_preserved_and_requires_manual_mapping(
    tmp_path: Path,
) -> None:
    _write_fixture(
        tmp_path,
        "theorem-status.md: | C2.1 | positive eventual increment | proved |\n",
    )

    gaps = _gaps(tmp_path, "claim_id.incompatible")

    assert len(gaps) == 1
    assert gaps[0].automatic is False
    assert gaps[0].details == {
        "alias": "C2.1",
        "suggested_canonical": None,
        "occurrences": ["docs/fixture.md"],
    }
    assert "C2.1" in gaps[0].message
    assert "C2 " not in gaps[0].message


def test_simple_historical_ids_keep_lossless_punctuation_boundaries(tmp_path: Path) -> None:
    _write_fixture(tmp_path, "See K4, C7; and T18.\n")

    by_alias = {
        gap.details["alias"]: gap
        for gap in _gaps(tmp_path, "claim_id.incompatible")
        if gap.details is not None
    }

    assert set(by_alias) == {"C7", "K4", "T18"}
    assert by_alias["C7"].details["suggested_canonical"] == "C007"
    assert by_alias["K4"].details["suggested_canonical"] == "K004"
    assert by_alias["T18"].details["suggested_canonical"] == "T018"
    assert all(gap.automatic for gap in by_alias.values())


@pytest.mark.parametrize(
    "text, expected_phrase",
    [
        ("The certificate is independently regenerated and checked.\n", "independently regenerated"),
        ("The certificate was independently—recomputed against the source.\n", "independently—recomputed"),
        ("Three independent implementations agree on every row.\n", "independent implementations"),
        ("All rows were re-verified independently in u128.\n", "re-verified independently"),
        ("An independent arbitrary-precision certificate covers the range.\n", "independent arbitrary-precision certificate"),
        ("The required certificate was independently regenerated.\n", "independently regenerated"),
        ("As required by policy, the certificate was independently regenerated.\n", "independently regenerated"),
        ("The certificate was not required and was independently regenerated.\n", "independently regenerated"),
        ("The certificate was independently regenerated. Was the process documented?\n", "independently regenerated"),
        ("The certificate was independently regenerated; was the process documented?\n", "independently regenerated"),
        ("Although probably unnecessary, the certificate was independently verified.\n", "independently verified"),
        ("The estimate was probably correct, but the certificate was independently verified.\n", "independently verified"),
    ],
)
def test_affirmative_independence_variants_are_reported(
    tmp_path: Path,
    text: str,
    expected_phrase: str,
) -> None:
    _write_fixture(tmp_path, text)

    gaps = _gaps(tmp_path, "identity.unstructured_assertion")

    assert len(gaps) == 1
    assert gaps[0].automatic is False
    assert gaps[0].details is not None
    assert expected_phrase in gaps[0].details["phrases"]


@pytest.mark.parametrize(
    "text",
    [
        "The certificate was not independently regenerated.\n",
        "This does not establish independent reproduction.\n",
        "No independent verifier checked the complete census.\n",
        "The certificate has never been independently recomputed.\n",
        "Independent reproduction was not performed.\n",
        "External review has not occurred.\n",
        "An independent verifier did not check the census.\n",
        "Independent reproduction, however, was not performed.\n",
        "No human specialist has independently refereed the proofs.\n",
    ],
)
def test_negated_independence_language_is_not_reported(tmp_path: Path, text: str) -> None:
    _write_fixture(tmp_path, text)

    assert not _gaps(tmp_path, "identity.unstructured_assertion")


@pytest.mark.parametrize(
    "text",
    [
        "The certificate must be independently regenerated and checked.\n",
        "Independent reproduction is required before release.\n",
        "External review is pending.\n",
        "The verifier should independently recompute every row.\n",
        "The result will soon be independently verified.\n",
        "The result may already have been independently verified.\n",
        "The result could conceivably have been independently verified.\n",
        "The result should already have been independently checked.\n",
        "The result will, after approval, be independently validated.\n",
    ],
)
def test_requirement_or_future_language_is_not_reported(tmp_path: Path, text: str) -> None:
    _write_fixture(tmp_path, text)

    assert not _gaps(tmp_path, "identity.unstructured_assertion")


@pytest.mark.parametrize(
    "text",
    [
        "Was the certificate independently regenerated? The status remains unknown.\n",
        "Question: can the certificate be independently regenerated? Status unknown.\n",
    ],
)
def test_question_local_independence_language_is_not_reported(
    tmp_path: Path,
    text: str,
) -> None:
    _write_fixture(tmp_path, text)

    assert not _gaps(tmp_path, "identity.unstructured_assertion")


@pytest.mark.parametrize(
    "text",
    [
        "Was the certificate independently regenerated; was it documented?\n",
        "Question: was the certificate independently regenerated; status unknown.\n",
        "Whether the certificate was independently regenerated remains unknown.\n",
        "We do not know whether the certificate was independently regenerated.\n",
        "It is unclear whether the certificate was independently regenerated.\n",
        "The result appears to have been independently verified.\n",
        "The result seems to have been independently verified.\n",
        "The result was allegedly independently verified.\n",
        "The result was reportedly independently verified.\n",
        "The result was probably independently verified.\n",
        "The result was possibly independently verified.\n",
        "The result was apparently independently verified.\n",
        "The result was purportedly independently verified.\n",
        "The result was supposedly independently verified.\n",
        "The result is likely to have been independently verified.\n",
        "The result is said to have been independently verified.\n",
        "The result is believed to have been independently verified.\n",
        "It is alleged that the result was independently verified.\n",
        "The proof appears to have been approved by an independent verifier.\n",
        "The proof was allegedly approved by an independent reviewer.\n",
        "Independent review reportedly confirmed the proof.\n",
        "The independent reviewer reportedly checked the proof.\n",
    ],
)
def test_interrogative_or_uncertain_independence_language_is_not_reported(
    tmp_path: Path,
    text: str,
) -> None:
    _write_fixture(tmp_path, text)

    assert not _gaps(tmp_path, "identity.unstructured_assertion")


@pytest.mark.parametrize(
    "text",
    [
        "Independent reproduction is yet to be performed.\n",
        "External review has yet to occur.\n",
        "External review remains outstanding.\n",
        "An independent verifier failed to check the census.\n",
        "An independent verifier was unable to check the census.\n",
        "Independent reproduction was attempted but failed.\n",
        "No evidence of independent reproduction exists.\n",
        "The result is expected to be independently reproduced.\n",
        "The result is intended to be independently reproduced.\n",
        "The result is scheduled to be independently reproduced.\n",
        "The certificate is expected after review to be independently regenerated.\n",
        "The certificate is scheduled next week to be independently reproduced.\n",
        "The result is intended, after cleanup, to be independently verified.\n",
        "Independent reproduction was abandoned.\n",
        "External review was cancelled.\n",
        "An independent verifier refused to check the census.\n",
        "An independent verifier may check the census.\n",
        "An independent verifier should check the census.\n",
        "An independent verifier will check the census.\n",
        "An independent verifier plans to check the census.\n",
        "An independent verifier hopes to check the census.\n",
        "An independent verifier is scheduled to check the census.\n",
        "External review is scheduled for Monday.\n",
        "Independent reproduction is underway.\n",
        "External review is in progress.\n",
        "The certificate is being independently regenerated.\n",
        "The certificate is being regenerated independently.\n",
        "The census may be checked by an independent verifier.\n",
        "The census is being checked by an independent verifier.\n",
        "The team hopes to be independently verified.\n",
        "Independent reproduction was rejected before execution.\n",
        "The independent verifier was approved for future work.\n",
        "A plan for independent reproduction passed committee review.\n",
        "The requirement for independent reproduction supports the proposal.\n",
        "The concept of independent reproduction matches the policy.\n",
        "A completed plan for independent verification was approved.\n",
        "The requirement for independent review was completed.\n",
        "The concept of independent audit was confirmed.\n",
        "The proposal for independent validation was approved.\n",
    ],
)
def test_noncompletion_independence_language_is_not_reported(
    tmp_path: Path,
    text: str,
) -> None:
    _write_fixture(tmp_path, text)

    assert not _gaps(tmp_path, "identity.unstructured_assertion")


@pytest.mark.parametrize(
    "text, expected_phrase",
    [
        ("The result was independently reproduced as required.\n", "independently reproduced"),
        ("Independent reproduction was completed.\n", "independent reproduction"),
        ("The independent verifier successfully checked the census.\n", "independent verifier"),
        ("The independent verifier checked the census.\n", "independent verifier"),
        ("External review concluded successfully.\n", "external review"),
        ("The certificate was independently regenerated.\n", "independently regenerated"),
        ("The verifier independently checked the census.\n", "independently checked"),
        ("The verifier has independently checked the census.\n", "independently checked"),
        ("The census was checked by an independent verifier.\n", "independent verifier"),
        ("The generator was cross-checked against the independent implementation.\n", "independent implementation"),
        ("The independent verifier\nrejected both rows.\n", "independent verifier"),
        ("Independent Python generators; matching trajectory digest.\n", "independent python generators"),
        ("Independent verification was completed.\n", "independent verification"),
        ("Independent audit concluded successfully.\n", "independent audit"),
        ("Independent review was completed.\n", "independent review"),
        ("Independent replication succeeded.\n", "independent replication"),
        ("Independent validation was completed.\n", "independent validation"),
        ("The independent verifier has now checked the census.\n", "independent verifier"),
        ("The independent verifier actually checked the census.\n", "independent verifier"),
        ("The independent verifier did check the census.\n", "independent verifier"),
        ("The independent verifier eventually checked the census.\n", "independent verifier"),
        ("| Result | Rust and independent Python generators agree. |\n", "independent python generators"),
        ("A documented independent verification was completed.\n", "independent verification"),
        ("A formal independent review concluded successfully.\n", "independent review"),
        ("The second independent verification was completed.\n", "independent verification"),
        ("An independent external audit was completed.\n", "independent external audit"),
        ("Independent review confirmed the proof.\n", "independent review"),
        ("Independent verification found no issues.\n", "independent verification"),
        ("The independent verifier found no issues.\n", "independent verifier"),
        ("The independent reviewer checked the proof.\n", "independent reviewer"),
        ("The independent auditor confirmed the result.\n", "independent auditor"),
        ("The proof was approved by an independent verifier.\n", "independent verifier"),
        ("The independent validator approved the certificate.\n", "independent validator"),
        ("Although probably unnecessary, the proof was approved by an independent verifier.\n", "independent verifier"),
        ("The proof was approved by a formal independent reviewer.\n", "independent reviewer"),
        ("A highly documented independent verification was completed.\n", "independent verification"),
        ("Independent review approved the proof.\n", "independent review"),
        ("The independent auditor found no issues.\n", "independent auditor"),
    ],
)
def test_completed_independence_controls_are_reported(
    tmp_path: Path,
    text: str,
    expected_phrase: str,
) -> None:
    _write_fixture(tmp_path, text)

    gaps = _gaps(tmp_path, "identity.unstructured_assertion")

    assert len(gaps) == 1
    assert gaps[0].details is not None
    assert expected_phrase in gaps[0].details["phrases"]


@pytest.mark.parametrize(
    "text",
    [
        "The estimate holds independently of q.\n",
        "Choose x and y independently from the same distribution.\n",
        "The variables x and y are independent.\n",
    ],
)
def test_ordinary_mathematical_independence_language_is_not_reported(
    tmp_path: Path,
    text: str,
) -> None:
    _write_fixture(tmp_path, text)

    assert not _gaps(tmp_path, "identity.unstructured_assertion")


def test_evidence_yaml_does_not_disable_unstructured_prose_scanning(tmp_path: Path) -> None:
    evidence = tmp_path / "audit/evidence/placeholder.yaml"
    evidence.parent.mkdir(parents=True)
    evidence.write_text("", encoding="utf-8")
    result = tmp_path / "docs/result.md"
    result.parent.mkdir(parents=True)
    result.write_text(
        "The certificate was independently regenerated.\n",
        encoding="utf-8",
    )

    gaps = _gaps(tmp_path, "identity.unstructured_assertion")

    assert len(gaps) == 1
    assert gaps[0].path == "docs/result.md"
