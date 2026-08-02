from __future__ import annotations

import re
from pathlib import Path

from .adapters import check_adapters
from .adoption_identifiers import legacy_id_gaps
from .adoption_independence import identity_gaps
from .adoption_scan import adoption_files, read_adoption_text
from .adoption_types import AdoptionGap, AdoptionReport
from .project_check import check_project
from .repository_check import _workflow_findings

DOCKERFILE_FROM = re.compile(r"^\s*FROM\s+([^\s]+)", re.IGNORECASE)
WORKFLOW_IMAGE = re.compile(r"^\s*image:\s*([^#\s]+)")
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
        content = read_adoption_text(path)
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
    files = adoption_files(root)
    gaps = [
        *_structure_gaps(root),
        *legacy_id_gaps(root, files),
        *_container_gaps(root, files),
        *identity_gaps(root, files),
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
