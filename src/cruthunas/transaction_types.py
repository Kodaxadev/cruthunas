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

from .models import CruthunasLoader, read_json, yaml_files

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
    "DERIVATION",
    "PROOF",
    "COMPUTATION",
    "REPRODUCTION",
    "FORMALIZATION",
    "REVIEW_INTERNAL",
    "REVIEW_EXTERNAL",
    "MANUSCRIPT_AUDIT",
    "GATE_DISPOSITION",
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
class FileSnapshot:
    path: str
    content: bytes | None
    sha256: str | None


@dataclass(frozen=True, slots=True)
class PlannedRead:
    path: str
    expected_sha256: str


@dataclass(frozen=True, slots=True)
class PlannedWrite:
    path: str
    content: bytes
    expected_sha256: str | None


@dataclass(frozen=True, slots=True)
class TransactionPlan:
    root: Path
    operation: str
    reads: tuple[PlannedRead, ...]
    writes: tuple[PlannedWrite, ...]
    expected_git_head: str | None
    preview: dict[str, Any]

    def to_dict(self, *, applied: bool = False) -> dict[str, Any]:
        return {
            "operation": self.operation,
            "applied": applied,
            "root": str(self.root),
            "reads": [item.path for item in self.reads],
            "writes": [item.path for item in self.writes],
            **self.preview,
        }


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _nonempty_text(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise TransactionError(f"{label} must not be empty", exit_code=2)
    return value.strip()


def _identity(value: Any, label: str = "Actor ID") -> str:
    return _nonempty_text(value, label)


def _identity_key(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    normalized = value.strip()
    return normalized.casefold() if normalized else None


def _capture_file(root: Path, value: str | Path, *, required: bool = False) -> FileSnapshot:
    relative = _relative_text(root, value)
    target = _resolve_relative(root, relative)
    try:
        with target.open("rb") as handle:
            content = handle.read()
    except FileNotFoundError:
        if required:
            raise TransactionError(f"Transaction input is not a file: {relative}")
        return FileSnapshot(relative, None, None)
    except IsADirectoryError as exc:
        raise TransactionError(f"Transaction path is not a file: {relative}") from exc
    return FileSnapshot(relative, content, _sha256_bytes(content))


def _snapshot_read(snapshot: FileSnapshot) -> PlannedRead:
    if snapshot.content is None or snapshot.sha256 is None:
        raise TransactionError(f"Transaction input is not a file: {snapshot.path}")
    return PlannedRead(snapshot.path, snapshot.sha256)


def _snapshot_write(snapshot: FileSnapshot, content: bytes) -> PlannedWrite:
    return PlannedWrite(snapshot.path, content, snapshot.sha256)


def _planned_read(root: Path, relative: str) -> PlannedRead:
    return _snapshot_read(_capture_file(root, relative, required=True))


def _planned_write(root: Path, relative: str, content: bytes) -> PlannedWrite:
    return _snapshot_write(_capture_file(root, relative), content)


def _yaml_from_snapshot(snapshot: FileSnapshot) -> Any:
    if snapshot.content is None:
        raise TransactionError(f"Transaction input is not a file: {snapshot.path}")
    try:
        return yaml.load(snapshot.content.decode("utf-8"), Loader=CruthunasLoader)
    except (UnicodeDecodeError, yaml.YAMLError) as exc:
        raise TransactionError(f"Could not parse {snapshot.path}: {exc}") from exc


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
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise ValueError("timestamp must include timezone")
    return parsed.astimezone(timezone.utc)


def _require_later(candidate: str, previous: Any, label: str) -> None:
    if not isinstance(previous, str):
        raise TransactionError(f"{label} has no valid prior timestamp", exit_code=2)
    try:
        is_later = _parsed_timestamp(candidate) > _parsed_timestamp(previous)
    except ValueError as exc:
        raise TransactionError(f"{label} contains an invalid timestamp", exit_code=2) from exc
    if not is_later:
        raise TransactionError(f"{label} timestamp must be later than {previous}", exit_code=2)


def _transition_history(
    root: Path,
    claim_id: str,
    axis: str,
) -> tuple[str | None, tuple[FileSnapshot, ...]]:
    latest: tuple[datetime, str] | None = None
    snapshots: list[FileSnapshot] = []
    for path in yaml_files(root, f"audit/transitions/{claim_id}"):
        try:
            snapshot = _capture_file(root, path, required=True)
            record = _yaml_from_snapshot(snapshot)
        except TransactionError:
            continue
        if not isinstance(record, dict) or record.get("axis") != axis:
            continue
        snapshots.append(snapshot)
        value = record.get("created_at")
        if not isinstance(value, str):
            continue
        try:
            parsed = _parsed_timestamp(value)
        except ValueError:
            continue
        if latest is None or parsed > latest[0]:
            latest = (parsed, value)
    return (latest[1] if latest else None, tuple(snapshots))


def _latest_transition_timestamp(root: Path, claim_id: str, axis: str) -> str | None:
    return _transition_history(root, claim_id, axis)[0]


def _run_git(root: Path, *arguments: str) -> str:
    try:
        completed = subprocess.run(
            ["git", "-C", str(root), *arguments],
            check=True,
            capture_output=True,
            text=True,
        )
    except (OSError, subprocess.CalledProcessError) as exc:
        raise TransactionError(
            "Could not inspect Git state; pass --source-revision explicitly when using a non-Git source tree",
            exit_code=3,
        ) from exc
    return completed.stdout.strip()


def _git_head(root: Path) -> str:
    revision = _run_git(root, "rev-parse", "HEAD")
    if not FULL_SHA.fullmatch(revision):
        raise TransactionError(
            "Git returned an invalid source revision",
            exit_code=3,
        )
    return revision


def _git_status(root: Path) -> str:
    return _run_git(root, "status", "--porcelain=v1", "--untracked-files=all")


def _source_revision(root: Path, override: str | None) -> str:
    if override is not None:
        if not FULL_SHA.fullmatch(override):
            raise TransactionError(
                "source_revision must be a full 40-character lowercase Git SHA",
                exit_code=2,
            )
        return override
    revision = _git_head(root)
    dirty = _git_status(root)
    if dirty:
        raise TransactionError(
            "Working tree is dirty; commit the source state before recording evidence or pass --source-revision explicitly",
            exit_code=3,
            details={"dirty_paths": dirty.splitlines()},
        )
    return revision


def _actor(actor_type: str, actor_id: str, *, approver: bool = False) -> dict[str, str]:
    allowed = APPROVER_TYPES if approver else ACTOR_TYPES
    if actor_type not in allowed:
        raise TransactionError(
            f"Invalid {'approver' if approver else 'actor'} type: {actor_type}",
            exit_code=2,
        )
    return {"type": actor_type, "id": _identity(actor_id)}


def _load_ledger_snapshot(root: Path) -> tuple[dict[str, Any], FileSnapshot]:
    snapshot = _capture_file(root, "claims/claims.yaml", required=True)
    ledger = _yaml_from_snapshot(snapshot)
    if not isinstance(ledger, dict) or not isinstance(ledger.get("claims"), list):
        raise TransactionError("claims/claims.yaml is not a valid claim ledger")
    return ledger, snapshot


def _load_ledger(root: Path) -> dict[str, Any]:
    return _load_ledger_snapshot(root)[0]


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


def _ledger_bytes(
    root: Path,
    ledger: dict[str, Any],
    snapshot: FileSnapshot | None = None,
) -> bytes:
    prefix = ""
    source = snapshot.content if snapshot is not None else _capture_file(
        root,
        "claims/claims.yaml",
        required=True,
    ).content
    if source is not None:
        lines = source.decode("utf-8").splitlines(keepends=True)
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
