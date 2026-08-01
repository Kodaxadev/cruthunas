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
        (
            "The certificate is independently regenerated and checked.\n",
            "independently regenerated",
        ),
        (
            "The certificate was independently—recomputed against the source.\n",
            "independently—recomputed",
        ),
        (
            "Three independent implementations agree on every row.\n",
            "independent implementations",
        ),
        (
            "All rows were re-verified independently in u128.\n",
            "re-verified independently",
        ),
        (
            "An independent arbitrary-precision certificate covers the range.\n",
            "independent arbitrary-precision certificate",
        ),
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
    ],
)
def test_requirement_or_future_language_is_not_reported(tmp_path: Path, text: str) -> None:
    _write_fixture(tmp_path, text)

    assert not _gaps(tmp_path, "identity.unstructured_assertion")


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
