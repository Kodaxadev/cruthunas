from __future__ import annotations

import re
from pathlib import Path

from .models import Finding, load_and_validate


MOVING_REFS = {"main", "master", "latest", "head", "trunk"}
FULL_SHA = re.compile(r"^[0-9a-f]{40}$")


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
            framework = project.get("framework", {})
            version = str(framework.get("version", "")).lower()
            commit = str(framework.get("commit", ""))
            if version in MOVING_REFS:
                findings.append(
                    Finding(
                        "project.moving_version",
                        f"Moving framework version is forbidden: {version}",
                        ".cruthunas/project.yaml",
                    )
                )
            if not FULL_SHA.fullmatch(commit):
                findings.append(
                    Finding(
                        "project.unpinned_commit",
                        "framework.commit must be a full 40-character lowercase SHA",
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
