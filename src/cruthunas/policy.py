from __future__ import annotations

from pathlib import Path

from .claims_check import check_claims
from .models import CheckResult
from .project_check import check_project
from .records_check import check_records
from .repository_check import check_repository


def run_checks(root: Path) -> CheckResult:
    root = root.resolve()
    claims, findings = check_claims(root)
    evidence, transitions, record_findings = check_records(root, claims)
    findings.extend(record_findings)
    findings.extend(check_project(root))
    findings.extend(check_repository(root))
    findings.sort(key=lambda item: (item.path, item.code, item.message))
    return CheckResult(
        root=str(root),
        findings=tuple(findings),
        claim_count=len(claims),
        evidence_count=len(evidence),
        transition_count=len(transitions),
    )


def format_text(result: CheckResult) -> str:
    if result.ok:
        return (
            f"Cruthunas policy check passed: {result.claim_count} claims, "
            f"{result.evidence_count} evidence records, {result.transition_count} transitions."
        )
    lines = ["Cruthunas policy check failed:"]
    lines.extend(
        f"- [{item.code}] {item.path}: {item.message}"
        for item in result.findings
    )
    return "\n".join(lines)
