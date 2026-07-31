from __future__ import annotations

import json
import re
from pathlib import Path

from cruthunas.transactions import EVIDENCE_CLASSES


ROOT = Path(__file__).parents[1]


def test_evidence_classes_match_normative_spec_schema_and_cli() -> None:
    schema = json.loads((ROOT / "schemas/evidence-v1.json").read_text(encoding="utf-8"))
    schema_classes = tuple(schema["properties"]["class"]["enum"])

    specification = (ROOT / "CRUTHUNAS_SPEC.md").read_text(encoding="utf-8")
    section = specification.split("## 8. Evidence classes", 1)[1].split("## 9. Independence", 1)[0]
    normative_classes = tuple(re.findall(r"^- `([A-Z_]+)`", section, flags=re.MULTILINE))

    assert normative_classes == schema_classes
    assert normative_classes == EVIDENCE_CLASSES
