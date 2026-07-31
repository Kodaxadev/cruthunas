from __future__ import annotations

import hashlib
import re
import subprocess
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml
from jsonschema import Draft202012Validator, FormatChecker

from .models import read_json, read_yaml, yaml_files

CLAIM_ID = re.compile(r"^[A-Z][0-9]{3,}$")
EVIDENCE_ID = re.compile(r"^E-([A-Z][0-9]{3,})-([0-9]{4,})$")
FULL_SHA = re.compile(r"^[0-9a-f]{40}$")
CLAIM_KINDS = (
    "CONJECTURE",
    "DEFINITION",
    "LEMMA",
    "THEOREM",
    "COROLLARY",
    "COMPUTATIONAL_RESULT",
    "COUNTEREXAMPLE",
)
EPISTEMIC_STATUSES = ("OPEN", "HEURISTIC", "COMPUTATIONAL", "PROVED", "REFUTED")
VERIFICATION_STATUSES = (
    "INTERNAL_AUDIT",
    "INDEPENDENT_REPRODUCTION",
    "FORMALIZED",
    "EXTERNAL_REVIEW",
)
PUBLICATION_STATUSES = (
    "WORKING",
    "FROZEN",
    "PREPRINT",
    "SUBMITTED",
    "PUBLISHED",
    "CORRECTED",
    "WITHDRAWN",
)
EVIDENCE_CLASSES = (
    "ATTRIBUTION",
    "CHARTER",
    "BASELINE",
    "CLAIM_REGISTRATION",
    "PROOF",
    "COMPUTATION",
    "REPRODUCTION",
    "FORMALIZATION",
    "REVIEW_INTERNAL",
    "REVIEW_EXTERNAL",
    "MANUSCRIPT_AUDIT",
    "RELEASE",
    "CORRECTION",
    "REFUTATION",
)
ACTOR_TYPES = ("human", "agent", "policy", "venue")
APPROVER_TYPES = ("human", "policy", "venue")


class TransactionError(Exception):
    def __init__(
        self,
        message: str,
        *,
        exit_code: int = 1,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message)
        self.exit_code = exit_code
        self.details = details or {}


@dataclass(frozen=True, slots=True)
class PlannedWrite:
    path: str
    content: bytes
    expected_sha256: str | None


@dataclass(frozen=True, slots=True)
class TransactionPlan:
    root: Path
    operation: str
    writes: tuple[PlannedWrite, ...]
    preview: dict[str, Any]

    def to_dict(self, *, applied: bool = False) -> dict[str, Any]:
        return {
            "operation": self.operation,
            "applied": applied,
            "root": str(self.root),
            "writes": [item.path for item in self.writes],
            **self.preview,
        }


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _planned_write(root: Path, relative: str, content: bytes) -> PlannedWrite:
    target = _resolve_relative(root, relative)
    expected = _sha256_bytes(target.read_bytes()) if target.is_file() else None
    return PlannedWrite(relative, content, expected)


def _resolve_relative(root: Path, value: str | Path) -> Path:
    raw = Path(value)
    target = raw if raw.is_absolute() else root / raw
    resolved = target.resolve()
    try:
        resolved.relative_to(root.resolve())
    except ValueError as exc:
        raise TransactionError(
            f"Path escapes the Cruthunas project root: {value}",
            exit_code=2,
        ) from exc
    return resolved


def _relative_text(root: Path, value: str | Path) -> str:
    return str(_resolve_relative(root, value).relative_to(root.resolve())).replace("\\", "/")


def _timestamp(value: str | None) -> str:
    if value is None:
        current = datetime.now(timezone.utc)
    else:
        try:
            current = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError as exc:
            raise TransactionError(
                f"Invalid RFC 3339 timestamp: {value}",
                exit_code=2,
            ) from exc
        if current.tzinfo is None:
            raise TransactionError("Timestamp must include a timezone", exit_code=2)
        current = current.astimezone(timezone.utc)
    timespec = "microseconds" if current.microsecond else "seconds"
    return current.isoformat(timespec=timespec).replace("+00:00", "Z")


def _filename_timestamp(value: str) -> str:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(timezone.utc)
    return parsed.strftime("%Y%m%dT%H%M%S%fZ")


def _parsed_timestamp(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(timezone.utc)


def _latest_transition_timestamp(root: Path, claim_id: str, axis: str) -> str | None:
    latest: tuple[datetime, str] | None = None
    for path in yaml_files(root, f"audit/transitions/{claim_id}"):
        try:
            record = read_yaml(path)
        except Exception:
            continue
        if not isinstance(record, dict) or record.get("axis") != axis:
            continue
        value = record.get("created_at")
        if not isinstance(value, str):
            continue
        try:
            parsed = _parsed_timestamp(value)
        except ValueError:
            continue
        if latest is None or parsed > latest[0]:
            latest = (parsed, value)
    return latest[1] if latest else None


def _source_revision(root: Path, override: str | None) -> str:
    if override is not None:
        if not FULL_SHA.fullmatch(override):
            raise TransactionError(
                "source_revision must be a full 40-character lowercase Git SHA",
                exit_code=2,
            )
        return override
    try:
        completed = subprocess.run(
            ["git", "-C", str(root), "rev-parse", "HEAD"],
            check=True,
            capture_output=True,
            text=True,
        )
    except (OSError, subprocess.CalledProcessError) as exc:
        raise TransactionError(
            "Could not determine source revision; pass --source-revision explicitly",
            exit_code=3,
        ) from exc
    revision = completed.stdout.strip()
    if not FULL_SHA.fullmatch(revision):
        raise TransactionError(
            "Git returned an invalid source revision; pass --source-revision explicitly",
            exit_code=3,
        )
    return revision


def _actor(actor_type: str, actor_id: str, *, approver: bool = False) -> dict[str, str]:
    allowed = APPROVER_TYPES if approver else ACTOR_TYPES
    if actor_type not in allowed:
        raise TransactionError(
            f"Invalid {'approver' if approver else 'actor'} type: {actor_type}",
            exit_code=2,
        )
    if not actor_id.strip():
        raise TransactionError("Actor ID must not be empty", exit_code=2)
    return {"type": actor_type, "id": actor_id.strip()}


def _load_ledger(root: Path) -> dict[str, Any]:
    path = root / "claims/claims.yaml"
    try:
        ledger = read_yaml(path)
    except Exception as exc:
        raise TransactionError(f"Could not read claims ledger: {exc}") from exc
    if not isinstance(ledger, dict) or not isinstance(ledger.get("claims"), list):
        raise TransactionError("claims/claims.yaml is not a valid claim ledger")
    return ledger


def _claim_map(ledger: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {
        item["id"]: item
        for item in ledger.get("claims", [])
        if isinstance(item, dict) and isinstance(item.get("id"), str)
    }


def _yaml_bytes(value: Any) -> bytes:
    return yaml.safe_dump(
        value,
        sort_keys=False,
        allow_unicode=True,
        width=1000,
    ).encode("utf-8")


def _ledger_bytes(root: Path, ledger: dict[str, Any]) -> bytes:
    path = root / "claims/claims.yaml"
    prefix = ""
    if path.is_file():
        lines = path.read_text(encoding="utf-8").splitlines(keepends=True)
        for index, line in enumerate(lines):
            if line.startswith("schema_version:"):
                prefix = "".join(lines[:index])
                break
    dumped = yaml.safe_dump(
        ledger,
        sort_keys=False,
        allow_unicode=True,
        width=1000,
    )
    return (prefix + dumped).encode("utf-8")


def _validate_instance(instance: Any, schema_path: Path, label: str) -> None:
    try:
        schema = read_json(schema_path)
    except Exception as exc:
        raise TransactionError(f"Could not read {label} schema: {exc}") from exc
    validator = Draft202012Validator(schema, format_checker=FormatChecker())
    errors = sorted(validator.iter_errors(instance), key=lambda item: list(item.absolute_path))
    if errors:
        rendered = []
        for error in errors:
            location = ".".join(str(part) for part in error.absolute_path)
            rendered.append(f"{error.message}{f' at {location}' if location else ''}")
        raise TransactionError(f"Invalid {label}: " + "; ".join(rendered))
