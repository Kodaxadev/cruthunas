from __future__ import annotations

import json
import re
from importlib import resources
from pathlib import Path
from typing import Any

import yaml
from jsonschema import Draft202012Validator, FormatChecker

from .transaction_plan import _plan
from .transaction_types import (
    FULL_SHA,
    FileSnapshot,
    TransactionError,
    TransactionPlan,
    _capture_file,
    _relative_text,
)

PROJECT_MODES = ("experimental", "released")
MOVING_REFS = {"main", "master", "latest", "head", "trunk", "develop", "development"}
PROJECT_ID = re.compile(r"^[a-z0-9][a-z0-9-]*$")
REPOSITORY = re.compile(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$")

_TEMPLATE_DESTINATIONS = {
    "claims-schema.json": "claims/schema.json",
    "project-v1.json": "schemas/project-v1.json",
    "claim-proposal-v1.json": "schemas/claim-proposal-v1.json",
    "evidence-v1.json": "schemas/evidence-v1.json",
    "transition-v1.json": "schemas/transition-v1.json",
    "exemption-v1.json": "schemas/exemption-v1.json",
    "framework-release-v1.json": "schemas/framework-release-v1.json",
}


def _template_bytes(name: str) -> bytes:
    return resources.files("cruthunas.templates").joinpath(name).read_bytes()


def _immutable_version(value: str) -> str:
    normalized = value.strip()
    if not normalized:
        raise TransactionError("Released mode requires a non-empty framework version", exit_code=2)
    lowered = normalized.casefold()
    if lowered in MOVING_REFS or lowered.startswith(("refs/heads/", "heads/")):
        raise TransactionError(
            f"Moving framework version is forbidden in released mode: {normalized}",
            exit_code=2,
        )
    if FULL_SHA.fullmatch(lowered):
        raise TransactionError(
            "Released mode requires a release version distinct from the framework commit",
            exit_code=2,
        )
    return normalized


def _release_attestation(
    root: Path,
    value: str,
    *,
    repository: str,
    version: str,
    commit: str,
) -> tuple[str, str, FileSnapshot]:
    relative = _relative_text(root, value)
    snapshot = _capture_file(root, relative, required=True)
    assert snapshot.content is not None and snapshot.sha256 is not None
    try:
        decoded = snapshot.content.decode("utf-8")
        record = json.loads(decoded) if relative.endswith(".json") else yaml.safe_load(decoded)
    except (UnicodeDecodeError, ValueError, yaml.YAMLError) as exc:
        raise TransactionError(f"Could not read framework release manifest: {exc}") from exc
    schema = json.loads(_template_bytes("framework-release-v1.json").decode("utf-8"))
    errors = sorted(
        Draft202012Validator(schema, format_checker=FormatChecker()).iter_errors(record),
        key=lambda item: list(item.absolute_path),
    )
    if errors:
        rendered = "; ".join(error.message for error in errors)
        raise TransactionError(f"Invalid framework release manifest: {rendered}", exit_code=2)
    assert isinstance(record, dict)
    framework = record["framework"]
    expected = (repository, version, commit)
    actual = (framework["repository"], framework["version"], framework["commit"])
    if actual != expected:
        raise TransactionError(
            "Framework release manifest does not match requested repository, version, and commit",
            exit_code=2,
            details={"expected": expected, "actual": actual},
        )
    return relative, snapshot.sha256, snapshot


def _conflicting_governed_paths(root: Path, destinations: list[str]) -> list[str]:
    conflicts = [relative for relative in destinations if (root / relative).exists()]
    for relative in (
        ".cruthunas/adapters.json",
        "audit/evidence-manifest.yaml",
        "audit/evidence-manifest.yml",
        "audit/evidence-manifest.md",
    ):
        if (root / relative).exists():
            conflicts.append(relative)
    for relative in (
        "audit/proposals",
        "audit/evidence",
        "audit/transitions",
        "audit/exemptions",
    ):
        directory = root / relative
        if directory.is_dir() and any(path.is_file() for path in directory.rglob("*")):
            conflicts.append(relative)
    return sorted(set(conflicts))


def plan_project_init(
    root: Path,
    *,
    mode: str,
    framework_repository: str,
    framework_commit: str,
    framework_version: str | None,
    framework_release_manifest: str | None,
    profile: str,
    project_id: str,
    project_title: str,
    maintainer_github: list[str],
) -> TransactionPlan:
    root = root.resolve()
    if not root.is_dir():
        raise TransactionError("Initialization root must be an existing directory", exit_code=2)
    if mode not in PROJECT_MODES:
        raise TransactionError(f"Unknown project mode: {mode}", exit_code=2)
    if not FULL_SHA.fullmatch(framework_commit):
        raise TransactionError(
            "framework commit must be an exact 40-character lowercase Git SHA",
            exit_code=2,
        )
    if not REPOSITORY.fullmatch(framework_repository):
        raise TransactionError("framework repository must use owner/name form", exit_code=2)
    if not PROJECT_ID.fullmatch(project_id):
        raise TransactionError(
            "project id must match ^[a-z0-9][a-z0-9-]*$", exit_code=2
        )
    title = project_title.strip()
    if not title:
        raise TransactionError("project title must not be empty", exit_code=2)
    selected_profile = profile.strip()
    if not selected_profile:
        raise TransactionError("profile must not be empty", exit_code=2)
    maintainers = sorted({value.strip() for value in maintainer_github if value.strip()})
    if not maintainers:
        raise TransactionError("at least one maintainer GitHub identity is required", exit_code=2)

    framework: dict[str, Any] = {
        "repository": framework_repository,
        "commit": framework_commit,
    }
    read_snapshots: list[FileSnapshot] = []
    if mode == "experimental":
        if framework_version is not None or framework_release_manifest is not None:
            raise TransactionError(
                "Experimental mode cannot claim a framework version or release manifest",
                exit_code=2,
            )
        conformance = "non-conformant"
    else:
        if framework_version is None:
            raise TransactionError("Released mode requires --framework-version", exit_code=2)
        if framework_release_manifest is None:
            raise TransactionError(
                "Released mode requires --framework-release-manifest", exit_code=2
            )
        version = _immutable_version(framework_version)
        release_path, release_hash, release_snapshot = _release_attestation(
            root,
            framework_release_manifest,
            repository=framework_repository,
            version=version,
            commit=framework_commit,
        )
        read_snapshots.append(release_snapshot)
        framework.update(
            {
                "version": version,
                "release": {
                    "manifest": release_path,
                    "sha256": release_hash,
                },
            }
        )
        conformance = "not-claimed"

    manifest = {
        "schema_version": 1,
        "mode": mode,
        "conformance": conformance,
        "framework": framework,
        "profile": selected_profile,
        "project": {
            "id": project_id,
            "title": title,
            "maintainers": [{"github": item} for item in maintainers],
        },
        "canonical": {
            "claim_ledger": "claims/claims.yaml",
            "research_charter": "RESEARCH_CHARTER.md",
            "evidence_root": "audit/evidence",
            "transition_root": "audit/transitions",
            "release_manifest": "audit/evidence-manifest.yaml",
        },
        "policies": {
            "workflow_pinning_required": True,
            "agent_evidence_is_provenance_only": True,
        },
    }
    project_bytes = yaml.safe_dump(
        manifest, sort_keys=False, allow_unicode=True, width=1000
    ).encode("utf-8")
    ledger_bytes = b"schema_version: 1\nclaims: []\n"
    charter_bytes = (
        "# Research Charter\n\n"
        "Status: UNFROZEN INITIALIZATION TEMPLATE\n\n"
        "This project was initialized for governed work. Replace this template with a "
        "project-specific frozen charter before relying on charter evidence. Initialization "
        "does not establish Cruthunas conformance, mathematical correctness, independent "
        "reproduction, external review, publication, or release.\n"
    ).encode("utf-8")

    writes: list[tuple[str, bytes]] = [
        (".cruthunas/project.yaml", project_bytes),
        ("claims/claims.yaml", ledger_bytes),
        ("RESEARCH_CHARTER.md", charter_bytes),
    ]
    writes.extend(
        (destination, _template_bytes(template))
        for template, destination in _TEMPLATE_DESTINATIONS.items()
    )
    destinations = [path for path, _content in writes]
    conflicts = _conflicting_governed_paths(root, destinations)
    if conflicts:
        raise TransactionError(
            "Initialization refuses to overwrite existing governed structure",
            exit_code=2,
            details={"conflicts": conflicts},
        )
    write_snapshots = {
        path: _capture_file(root, path)
        for path in destinations
    }
    return _plan(
        root,
        "project.init",
        writes,
        {
            "mode": mode,
            "conformance": conformance,
            "framework_commit": framework_commit,
            "project_id": project_id,
        },
        read_snapshots=read_snapshots,
        write_snapshots=write_snapshots,
        validation_profile="bootstrap",
    )
