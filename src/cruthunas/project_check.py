from __future__ import annotations

import hashlib
import re
from pathlib import Path
from typing import Any

from .models import Finding, load_and_validate


MOVING_REFS = {"main", "master", "latest", "head", "trunk", "develop", "development"}
FULL_SHA = re.compile(r"^[0-9a-f]{40}$")


def _local_file(root: Path, value: Any) -> Path | None:
    if not isinstance(value, str) or not value.strip():
        return None
    candidate = (root / value).resolve()
    try:
        candidate.relative_to(root.resolve())
    except ValueError:
        return None
    return candidate if candidate.is_file() else None


def _release_findings(root: Path, project: dict[str, Any]) -> list[Finding]:
    findings: list[Finding] = []
    framework_value = project.get("framework")
    framework = framework_value if isinstance(framework_value, dict) else {}
    release = framework.get("release")
    if not isinstance(release, dict):
        findings.append(
            Finding(
                "project.release_attestation_missing",
                "Released mode requires a local immutable framework release manifest and SHA-256",
                ".cruthunas/project.yaml",
            )
        )
        return findings
    manifest_value = release.get("manifest")
    manifest_path = _local_file(root, manifest_value)
    if manifest_path is None:
        findings.append(
            Finding(
                "project.release_manifest_missing",
                f"Framework release manifest does not exist inside the project: {manifest_value}",
                ".cruthunas/project.yaml",
            )
        )
        return findings
    expected_hash = release.get("sha256")
    actual_hash = hashlib.sha256(manifest_path.read_bytes()).hexdigest()
    if expected_hash != actual_hash:
        findings.append(
            Finding(
                "project.release_hash_mismatch",
                "Framework release manifest SHA-256 does not match the referenced file",
                ".cruthunas/project.yaml",
            )
        )
    release_record, current = load_and_validate(
        manifest_path,
        root / "schemas/framework-release-v1.json",
        root,
        missing_code="project.release_manifest_missing",
    )
    findings.extend(current)
    if isinstance(release_record, dict):
        attested = release_record.get("framework", {})
        requested = {
            "repository": framework.get("repository"),
            "version": framework.get("version"),
            "commit": framework.get("commit"),
        }
        if attested != requested:
            findings.append(
                Finding(
                    "project.release_mismatch",
                    "Framework release manifest does not attest the configured repository, version, and commit",
                    str(manifest_path.relative_to(root)),
                )
            )
    return findings


def check_project(root: Path) -> list[Finding]:
    findings: list[Finding] = []
    path = root / ".cruthunas/project.yaml"
    if path.exists():
        project, current = load_and_validate(
            path,
            root / "schemas/project-v1.json",
            root,
            missing_code="project.missing",
        )
        findings.extend(current)
        if isinstance(project, dict):
            mode = project.get("mode")
            conformance = project.get("conformance")
            framework_value = project.get("framework")
            framework = framework_value if isinstance(framework_value, dict) else {}
            version = str(framework.get("version", "")).strip()
            commit = str(framework.get("commit", ""))
            if not FULL_SHA.fullmatch(commit):
                findings.append(
                    Finding(
                        "project.unpinned_commit",
                        "framework.commit must be a full 40-character lowercase SHA",
                        ".cruthunas/project.yaml",
                    )
                )
            if version.casefold() in MOVING_REFS or version.casefold().startswith(("refs/heads/", "heads/")):
                findings.append(
                    Finding(
                        "project.moving_version",
                        f"Moving framework version is forbidden: {version}",
                        ".cruthunas/project.yaml",
                    )
                )
            if mode == "experimental":
                if conformance != "non-conformant":
                    findings.append(
                        Finding(
                            "project.experimental_conformance",
                            "Experimental projects must state conformance: non-conformant",
                            ".cruthunas/project.yaml",
                        )
                    )
                if framework.get("version") is not None or framework.get("release") is not None:
                    findings.append(
                        Finding(
                            "project.experimental_release_claim",
                            "Experimental projects cannot claim a framework release or version",
                            ".cruthunas/project.yaml",
                        )
                    )
            elif mode == "released":
                if not version:
                    findings.append(
                        Finding(
                            "project.release_version_missing",
                            "Released mode requires an immutable framework version",
                            ".cruthunas/project.yaml",
                        )
                    )
                if FULL_SHA.fullmatch(version.casefold()):
                    findings.append(
                        Finding(
                            "project.version_is_commit",
                            "Released mode requires a framework version distinct from the commit SHA",
                            ".cruthunas/project.yaml",
                        )
                    )
                findings.extend(_release_findings(root, project))
            else:
                findings.append(
                    Finding(
                        "project.mode_invalid",
                        "Project mode must be experimental or released",
                        ".cruthunas/project.yaml",
                    )
                )

            canonical = project.get("canonical", {})
            for key in ("claim_ledger", "research_charter"):
                value = canonical.get(key) if isinstance(canonical, dict) else None
                if isinstance(value, str) and _local_file(root, value) is None:
                    findings.append(
                        Finding(
                            "project.canonical_missing",
                            f"Canonical {key} path does not exist: {value}",
                            ".cruthunas/project.yaml",
                        )
                    )
    if (root / "CONJECTURE_WARDEN_SPEC.md").exists():
        findings.append(
            Finding(
                "identity.stale_filename",
                "Remove the retired CONJECTURE_WARDEN_SPEC.md filename",
                "CONJECTURE_WARDEN_SPEC.md",
            )
        )
    return findings
