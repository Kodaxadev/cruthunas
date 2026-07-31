from __future__ import annotations

import re
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import yaml

from .adapters import check_adapters
from .claim_ids import CANONICAL_CLAIM_ID, legacy_canonical_id, normalize_alias
from .evidence_policy import INDEPENDENCE_KEYS
from .models import read_yaml
from .project_check import check_project
from .repository_check import _workflow_findings

LEGACY_TOKEN = re.compile(r"(?<![A-Za-z0-9])([A-Z]{1,2}[0-9]{1,3})(?![A-Za-z0-9])")
DOCKERFILE_FROM = re.compile(r"^\s*FROM\s+([^\s]+)", re.IGNORECASE)
WORKFLOW_IMAGE = re.compile(r"^\s*image:\s*([^#\s]+)")
TEXT_SUFFIXES = {".md", ".txt", ".yaml", ".yml", ".json", ".toml", ".py", ".rs", ".lean", ".tex"}
IGNORED_PARTS = {".git", ".venv", "venv", "node_modules", "__pycache__", ".pytest_cache", "build", "dist", "target"}
REQUIRED_STRUCTURE = (
    ".cruthunas/project.yaml",
    "claims/claims.yaml",
    "claims/schema.json",
    "schemas/project-v1.json",
    "schemas/claim-proposal-v1.json",
    "schemas/evidence-v1.json",
    "schemas/transition-v1.json",
    "schemas/exemption-v1.json",
    "schemas/framework-release-v1.json",
    "RESEARCH_CHARTER.md",
)


@dataclass(frozen=True, slots=True)
class AdoptionGap:
    code: str
    category: str
    message: str
    path: str
    automatic: bool
    details: dict[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class AdoptionReport:
    root: str
    gaps: tuple[AdoptionGap, ...]

    @property
    def ok(self) -> bool:
        return not self.gaps

    def to_dict(self) -> dict[str, Any]:
        return {
            "ok": self.ok,
            "root": self.root,
            "summary": {
                "gaps": len(self.gaps),
                "automatic": sum(item.automatic for item in self.gaps),
                "manual": sum(not item.automatic for item in self.gaps),
            },
            "gaps": [item.to_dict() for item in self.gaps],
        }


def _files(root: Path) -> list[Path]:
    found: list[Path] = []
    for path in root.rglob("*"):
        if not path.is_file():
            continue
        relative = path.relative_to(root)
        if any(part in IGNORED_PARTS for part in relative.parts):
            continue
        found.append(path)
    return sorted(found, key=lambda item: str(item.relative_to(root)).replace("\\", "/"))


def _text(path: Path) -> str | None:
    try:
        if path.stat().st_size > 2_000_000:
            return None
        return path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return None


def _structure_gaps(root: Path) -> list[AdoptionGap]:
    return [
        AdoptionGap(
            "structure.missing",
            "project_structure",
            "Required governed project path is missing",
            relative,
            True,
        )
        for relative in REQUIRED_STRUCTURE
        if not (root / relative).is_file()
    ]


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


def _legacy_id_gaps(root: Path, files: list[Path]) -> list[AdoptionGap]:
    occurrences: dict[str, list[str]] = {}
    declared_aliases = _declared_aliases(root)
    for path in files:
        if path.suffix.lower() not in TEXT_SUFFIXES:
            continue
        content = _text(path)
        if content is None:
            continue
        relative = str(path.relative_to(root)).replace("\\", "/")
        if (
            relative == "claims/schema.json"
            or relative.startswith("schemas/")
            or relative.startswith("src/cruthunas/templates/")
        ):
            continue
        for match in LEGACY_TOKEN.finditer(content):
            token = match.group(1)
            try:
                normalized = normalize_alias(token)
            except ValueError:
                continue
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


def _container_gaps(root: Path, files: list[Path]) -> list[AdoptionGap]:
    gaps: list[AdoptionGap] = []
    for finding in _workflow_findings(root):
        gaps.append(
            AdoptionGap(
                finding.code,
                "workflow_pinning",
                finding.message,
                finding.path,
                True,
            )
        )
    for path in files:
        relative = str(path.relative_to(root)).replace("\\", "/")
        name = path.name.lower()
        content = _text(path)
        if content is None:
            continue
        if name == "dockerfile" or name.startswith("dockerfile."):
            for number, line in enumerate(content.splitlines(), 1):
                match = DOCKERFILE_FROM.match(line)
                if not match:
                    continue
                image = match.group(1)
                if image.casefold() == "scratch" or "@sha256:" in image:
                    continue
                gaps.append(
                    AdoptionGap(
                        "container.unpinned_image",
                        "workflow_pinning",
                        f"Container base image is not digest-pinned on line {number}: {image}",
                        relative,
                        True,
                    )
                )
        if relative.startswith(".github/workflows/") and path.suffix in {".yml", ".yaml"}:
            for number, line in enumerate(content.splitlines(), 1):
                match = WORKFLOW_IMAGE.match(line)
                if not match:
                    continue
                image = match.group(1)
                if "@sha256:" in image:
                    continue
                gaps.append(
                    AdoptionGap(
                        "workflow.unpinned_container",
                        "workflow_pinning",
                        f"Workflow container image is not digest-pinned on line {number}: {image}",
                        relative,
                        True,
                    )
                )
    return gaps


def _identity_gaps(root: Path, files: list[Path]) -> list[AdoptionGap]:
    gaps: list[AdoptionGap] = []
    evidence_root = root / "audit/evidence"
    evidence_files = sorted([*evidence_root.rglob("*.yaml"), *evidence_root.rglob("*.yml")]) if evidence_root.is_dir() else []
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

    if not evidence_files:
        phrases = ("independent implementation", "independent verifier", "independent reproduction", "external review")
        for path in files:
            if path.suffix.lower() not in TEXT_SUFFIXES:
                continue
            relative = str(path.relative_to(root)).replace("\\", "/")
            lowered_path = relative.casefold()
            if not (
                lowered_path.startswith(("audit/", "independent/"))
                or any(token in lowered_path for token in ("review", "reproduc", "evidence"))
            ):
                continue
            content = _text(path)
            if content is None:
                continue
            matched: set[str] = set()
            for line in content.splitlines():
                lowered = line.casefold()
                if any(negation in lowered for negation in ("does not", "do not", "not establish", "no external", "no independent")):
                    continue
                matched.update(phrase for phrase in phrases if phrase in lowered)
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


def _migration_gaps(root: Path, files: list[Path]) -> list[AdoptionGap]:
    gaps: list[AdoptionGap] = []
    legacy_manifest = root / "audit/evidence-manifest.md"
    canonical_manifest = root / "audit/evidence-manifest.yaml"
    if legacy_manifest.is_file() and not canonical_manifest.is_file():
        gaps.append(
            AdoptionGap(
                "migration.record_manual",
                "manual_migration",
                "Historical Markdown evidence manifest cannot be converted without a claim-by-claim mapping and release-scope decision",
                "audit/evidence-manifest.md",
                False,
            )
        )

    governed_roots = (
        "audit/proposals/",
        "audit/evidence/",
        "audit/transitions/",
        "audit/exemptions/",
    )
    for path in files:
        relative = str(path.relative_to(root)).replace("\\", "/")
        if not relative.startswith(governed_roots):
            continue
        if path.suffix.lower() in {".yaml", ".yml"}:
            continue
        gaps.append(
            AdoptionGap(
                "migration.record_manual",
                "manual_migration",
                "Record under a governed audit path is not a typed YAML record and cannot be migrated automatically",
                relative,
                False,
            )
        )
    return gaps


def _adapter_gaps(root: Path) -> list[AdoptionGap]:
    skills = root / "skills"
    manifest = root / ".cruthunas/adapters.json"
    if skills.is_dir() and not manifest.is_file():
        return [
            AdoptionGap(
                "adapter.manifest_absent",
                "adapters",
                "Canonical skills exist but no adapter adoption manifest is present",
                ".cruthunas/adapters.json",
                True,
            )
        ]
    if not manifest.is_file():
        return []
    return [
        AdoptionGap(
            "adapter.drift",
            "adapters",
            message,
            ".cruthunas/adapters.json",
            True,
        )
        for message in check_adapters(root)
    ]


def _project_gaps(root: Path) -> list[AdoptionGap]:
    path = root / ".cruthunas/project.yaml"
    if not path.is_file():
        return []
    gaps: list[AdoptionGap] = []
    for finding in check_project(root):
        if finding.code.startswith("identity."):
            continue
        gaps.append(
            AdoptionGap(
                finding.code,
                "framework_adoption",
                finding.message,
                finding.path,
                finding.code in {
                    "project.moving_version",
                    "project.unpinned_commit",
                    "project.release_hash_mismatch",
                },
            )
        )
    return gaps


def adoption_gap_report(root: Path) -> AdoptionReport:
    root = root.resolve()
    if not root.is_dir():
        raise FileNotFoundError(f"Adoption root is not an existing directory: {root}")
    files = _files(root)
    gaps = [
        *_structure_gaps(root),
        *_legacy_id_gaps(root, files),
        *_container_gaps(root, files),
        *_identity_gaps(root, files),
        *_migration_gaps(root, files),
        *_adapter_gaps(root),
        *_project_gaps(root),
    ]
    unique: dict[tuple[str, str, str], AdoptionGap] = {}
    for gap in gaps:
        unique[(gap.path, gap.code, gap.message)] = gap
    ordered = tuple(
        sorted(unique.values(), key=lambda item: (item.category, item.path, item.code, item.message))
    )
    return AdoptionReport(str(root), ordered)


def format_adoption_report(report: AdoptionReport) -> str:
    if report.ok:
        return "No deterministic Cruthunas adoption gaps were found."
    lines = ["Cruthunas adoption gaps:"]
    for gap in report.gaps:
        mode = "automatic" if gap.automatic else "manual"
        lines.append(f"- [{gap.code}] {gap.path}: {gap.message} ({mode})")
    return "\n".join(lines)
