from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import yaml
from jsonschema import Draft202012Validator, FormatChecker


class CruthunasLoader(yaml.SafeLoader):
    """Safe YAML loader that preserves ISO timestamps as strings."""


for first, resolvers in list(CruthunasLoader.yaml_implicit_resolvers.items()):
    CruthunasLoader.yaml_implicit_resolvers[first] = [
        item for item in resolvers if item[0] != "tag:yaml.org,2002:timestamp"
    ]


@dataclass(frozen=True, slots=True)
class Finding:
    code: str
    message: str
    path: str
    severity: str = "error"

    def to_dict(self) -> dict[str, str]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class CheckResult:
    root: str
    findings: tuple[Finding, ...]
    claim_count: int
    evidence_count: int
    transition_count: int

    @property
    def ok(self) -> bool:
        return not any(item.severity == "error" for item in self.findings)

    def to_dict(self) -> dict[str, Any]:
        return {
            "ok": self.ok,
            "root": self.root,
            "summary": {
                "claims": self.claim_count,
                "evidence": self.evidence_count,
                "transitions": self.transition_count,
                "errors": sum(item.severity == "error" for item in self.findings),
                "warnings": sum(item.severity == "warning" for item in self.findings),
            },
            "findings": [item.to_dict() for item in self.findings],
        }


def discover_root(start: Path) -> Path:
    current = start.resolve()
    for candidate in (current, *current.parents):
        if (candidate / "claims" / "claims.yaml").is_file() or (
            candidate / ".cruthunas" / "project.yaml"
        ).is_file():
            return candidate
    raise FileNotFoundError(
        "No Cruthunas project found; expected claims/claims.yaml or .cruthunas/project.yaml"
    )


def read_yaml(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as handle:
        return yaml.load(handle, Loader=CruthunasLoader)


def read_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def load_and_validate(
    data_path: Path,
    schema_path: Path,
    root: Path,
    *,
    missing_code: str,
) -> tuple[Any | None, list[Finding]]:
    if not data_path.is_file():
        return None, [
            Finding(
                missing_code,
                "Required file is missing",
                str(data_path.relative_to(root)),
            )
        ]
    if not schema_path.is_file():
        return None, [
            Finding(
                "schema.missing",
                f"Schema required for {data_path.name} is missing",
                str(schema_path.relative_to(root)),
            )
        ]
    try:
        instance = (
            read_yaml(data_path)
            if data_path.suffix in {".yaml", ".yml"}
            else read_json(data_path)
        )
    except (OSError, ValueError, yaml.YAMLError) as exc:
        return None, [
            Finding("parse.failed", str(exc), str(data_path.relative_to(root)))
        ]
    try:
        schema = read_json(schema_path)
    except (OSError, ValueError) as exc:
        return None, [
            Finding(
                "schema.parse_failed",
                str(exc),
                str(schema_path.relative_to(root)),
            )
        ]
    validator = Draft202012Validator(schema, format_checker=FormatChecker())
    findings: list[Finding] = []
    for error in sorted(
        validator.iter_errors(instance),
        key=lambda item: list(item.absolute_path),
    ):
        location = ".".join(str(part) for part in error.absolute_path)
        suffix = f" at {location}" if location else ""
        findings.append(
            Finding(
                "schema.invalid",
                f"{error.message}{suffix}",
                str(data_path.relative_to(root)),
            )
        )
    return instance, findings


def yaml_files(root: Path, relative: str) -> list[Path]:
    directory = root / relative
    if not directory.is_dir():
        return []
    return sorted([*directory.rglob("*.yaml"), *directory.rglob("*.yml")])


def path_exists(root: Path, value: str) -> bool:
    if value.startswith(("https://", "http://", "doi:")):
        return True
    candidate = (root / value).resolve()
    try:
        candidate.relative_to(root.resolve())
    except ValueError:
        return False
    return candidate.exists()
