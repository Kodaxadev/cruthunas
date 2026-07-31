from __future__ import annotations

import ast
import re
from pathlib import Path

from .adapters import check_adapters
from .models import Finding


EXTERNAL_USE = re.compile(r"^\s*-?\s*uses:\s*([^#\s]+)")
FULL_ACTION_SHA = re.compile(r"^[^@]+@[0-9a-f]{40}$")
BINARY_SUFFIXES = {
    ".7z",
    ".class",
    ".dll",
    ".dylib",
    ".exe",
    ".gz",
    ".jar",
    ".o",
    ".obj",
    ".pdf",
    ".pyc",
    ".so",
    ".tar",
    ".tgz",
    ".whl",
    ".zip",
}
GENERATED_ROOTS = {"build", "dist", "out", "target", ".pytest_cache", "__pycache__"}


def _workflow_findings(root: Path) -> list[Finding]:
    findings: list[Finding] = []
    workflow_root = root / ".github/workflows"
    if not workflow_root.is_dir():
        return findings
    for path in sorted([*workflow_root.glob("*.yml"), *workflow_root.glob("*.yaml")]):
        for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            match = EXTERNAL_USE.match(line)
            if not match:
                continue
            reference = match.group(1)
            if reference.startswith("./"):
                continue
            if reference.startswith("docker://"):
                if "@sha256:" not in reference:
                    findings.append(
                        Finding(
                            "workflow.unpinned_container",
                            f"Container reference is not digest-pinned on line {number}: {reference}",
                            str(path.relative_to(root)),
                        )
                    )
                continue
            if not FULL_ACTION_SHA.fullmatch(reference):
                findings.append(
                    Finding(
                        "workflow.unpinned_action",
                        f"Action is not pinned to a full commit SHA on line {number}: {reference}",
                        str(path.relative_to(root)),
                    )
                )
    return findings


def _binary_findings(root: Path) -> list[Finding]:
    findings: list[Finding] = []
    ignored = {".git", ".venv", "venv", "node_modules"}
    for path in root.rglob("*"):
        if not path.is_file():
            continue
        relative = path.relative_to(root)
        if any(part in ignored for part in relative.parts):
            continue
        generated = bool(relative.parts and relative.parts[0] in GENERATED_ROOTS)
        manuscript_pdf = (
            bool(relative.parts)
            and relative.parts[0] == "manuscript"
            and path.suffix.lower() == ".pdf"
        )
        if (generated or manuscript_pdf) and path.suffix.lower() in BINARY_SUFFIXES:
            findings.append(
                Finding(
                    "repository.generated_binary",
                    "Generated binary/build artifact must not be committed; attach it to a release or workflow run instead",
                    str(relative),
                )
            )
    return findings


def _project_modules(root: Path) -> set[str]:
    modules: set[str] = set()
    source_root = root / "src"
    if source_root.is_dir():
        modules.update(path.name for path in source_root.iterdir() if path.is_dir())
        modules.update(path.stem for path in source_root.glob("*.py"))
    modules.update(path.stem for path in root.glob("*.py"))
    return modules


def _independent_findings(root: Path) -> list[Finding]:
    findings: list[Finding] = []
    independent = root / "independent"
    if not independent.is_dir():
        return findings
    project_modules = _project_modules(root)
    for path in independent.rglob("*.py"):
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        except (OSError, SyntaxError) as exc:
            findings.append(
                Finding(
                    "independent.parse_failed",
                    str(exc),
                    str(path.relative_to(root)),
                )
            )
            continue
        for node in ast.walk(tree):
            imported: str | None = None
            if isinstance(node, ast.Import):
                for alias in node.names:
                    top = alias.name.split(".", 1)[0]
                    if top in project_modules:
                        imported = alias.name
                        break
            elif isinstance(node, ast.ImportFrom):
                if node.level:
                    imported = "." * node.level + (node.module or "")
                elif node.module:
                    top = node.module.split(".", 1)[0]
                    if top in project_modules:
                        imported = node.module
            if imported:
                findings.append(
                    Finding(
                        "independent.project_import",
                        f"Independent verifier imports project implementation: {imported}",
                        str(path.relative_to(root)),
                    )
                )
    return findings


def check_repository(root: Path) -> list[Finding]:
    findings = _workflow_findings(root)
    findings.extend(_binary_findings(root))
    findings.extend(_independent_findings(root))
    if (root / "skills").is_dir() or (root / ".cruthunas/adapters.json").exists():
        findings.extend(
            Finding("adapter.drift", message, ".cruthunas/adapters.json")
            for message in check_adapters(root)
        )
    return findings
