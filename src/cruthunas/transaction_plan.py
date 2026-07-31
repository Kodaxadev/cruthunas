from __future__ import annotations

import ctypes
import hashlib
import json
import os
import shutil
import tempfile
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .models import CheckResult, Finding
from .policy import run_checks
from .transaction_types import (
    FileSnapshot, PlannedRead, PlannedWrite, TransactionError, TransactionPlan,
    _git_head, _git_status, _planned_read, _planned_write, _relative_text,
    _resolve_relative, _sha256_bytes, _snapshot_read, _snapshot_write,
)

_MALFORMED_LOCK_GRACE_SECONDS = 5.0
_VALIDATION_PROFILES = frozenset({"full", "bootstrap"})
_BOOTSTRAP_BLOCKING_PREFIXES = (
    "project.", "ledger.", "schema.", "claim.", "proposal.",
    "evidence.", "transition.", "exemption.",
)


def _ignore_shadow(_directory: str, names: list[str]) -> set[str]:
    ignored = {".git", ".venv", "venv", "node_modules", "__pycache__", ".pytest_cache"}
    return ignored.intersection(names)


def _apply_writes_to(root: Path, writes: tuple[PlannedWrite, ...]) -> None:
    for item in writes:
        target = _resolve_relative(root, item.path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(item.content)


def _validation_profile(plan: TransactionPlan) -> str:
    value = plan.preview.get("validation_profile", "full")
    if value not in _VALIDATION_PROFILES:
        raise TransactionError(f"Unknown transaction validation profile: {value}", exit_code=5)
    return str(value)


def _blocking_findings(result: CheckResult, profile: str) -> tuple[Finding, ...]:
    errors = tuple(item for item in result.findings if item.severity == "error")
    if profile == "full":
        return errors
    return tuple(item for item in errors if item.code.startswith(_BOOTSTRAP_BLOCKING_PREFIXES))


def _validate_result(plan: TransactionPlan, result: CheckResult, *, phase: str) -> None:
    profile = _validation_profile(plan)
    blocking = _blocking_findings(result, profile)
    if not blocking:
        return
    first = blocking[0]
    prefix = "Prospective transaction violates Cruthunas policy" if phase == "preview" else "Applied transaction failed post-write validation"
    raise TransactionError(
        f"{prefix}: {first.message} [{first.code}]",
        exit_code=5 if phase == "apply" else 1,
        details={
            **result.to_dict(),
            "validation_profile": profile,
            "blocking_findings": [item.to_dict() for item in blocking],
        },
    )


def _validate_plan(plan: TransactionPlan) -> None:
    with tempfile.TemporaryDirectory(prefix="cruthunas-preview-") as temporary:
        shadow = Path(temporary) / "repo"
        shutil.copytree(plan.root, shadow, symlinks=True, ignore=_ignore_shadow)
        _apply_writes_to(shadow, plan.writes)
        _validate_result(plan, run_checks(shadow), phase="preview")


def _plan(
    root: Path,
    operation: str,
    writes: list[tuple[str, bytes]],
    preview: dict[str, Any],
    *,
    reads: list[str | Path] | None = None,
    read_snapshots: list[FileSnapshot] | None = None,
    write_snapshots: dict[str, FileSnapshot] | None = None,
    expected_git_head: str | None = None,
    validation_profile: str = "full",
) -> TransactionPlan:
    if validation_profile not in _VALIDATION_PROFILES:
        raise TransactionError(f"Unknown transaction validation profile: {validation_profile}", exit_code=5)
    normalized_write_snapshots = {_relative_text(root, path): snapshot for path, snapshot in (write_snapshots or {}).items()}
    seen_writes: set[str] = set()
    planned_writes: list[PlannedWrite] = []
    for relative, content in writes:
        normalized = _relative_text(root, relative)
        if normalized in seen_writes:
            raise TransactionError(f"Transaction writes the same path twice: {normalized}", exit_code=5)
        seen_writes.add(normalized)
        snapshot = normalized_write_snapshots.get(normalized)
        if snapshot is not None:
            if snapshot.path != normalized:
                raise TransactionError(f"Write snapshot path mismatch: {snapshot.path} != {normalized}", exit_code=5)
            planned_writes.append(_snapshot_write(snapshot, content))
        else:
            planned_writes.append(_planned_write(root, normalized, content))
    seen_reads: set[str] = set()
    planned_reads: list[PlannedRead] = []
    for snapshot in read_snapshots or []:
        normalized = _relative_text(root, snapshot.path)
        if normalized in seen_writes or normalized in seen_reads:
            continue
        if snapshot.path != normalized:
            raise TransactionError(f"Read snapshot path mismatch: {snapshot.path} != {normalized}", exit_code=5)
        seen_reads.add(normalized)
        planned_reads.append(_snapshot_read(snapshot))
    for value in reads or []:
        normalized = _relative_text(root, value)
        if normalized in seen_writes or normalized in seen_reads:
            continue
        seen_reads.add(normalized)
        planned_reads.append(_planned_read(root, normalized))
    plan_preview = dict(preview)
    if validation_profile != "full":
        plan_preview["validation_profile"] = validation_profile
    plan = TransactionPlan(root.resolve(), operation, tuple(planned_reads), tuple(planned_writes), expected_git_head, plan_preview)
    _validate_plan(plan)
    return plan


def _lock_path(root: Path) -> Path:
    digest = hashlib.sha256(str(root.resolve()).encode("utf-8")).hexdigest()[:20]
    return Path(tempfile.gettempdir()) / f"cruthunas-{digest}.lock"


def _process_exists(pid: int) -> bool:
    if pid <= 0:
        return False
    if os.name == "nt":
        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        handle = kernel32.OpenProcess(0x1000, False, pid)
        if handle:
            kernel32.CloseHandle(handle)
            return True
        return ctypes.get_last_error() == 5
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    except OSError:
        return False
    return True


def _read_lock(lock_path: Path) -> dict[str, Any] | None:
    try:
        value = json.loads(lock_path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    return value if isinstance(value, dict) else None


def _lock_age_seconds(lock_path: Path) -> float:
    return max(0.0, time.time() - lock_path.stat().st_mtime)


def _remove_stale_lock(lock_path: Path, root: Path) -> bool:
    record = _read_lock(lock_path)
    if record is not None:
        pid = record.get("pid")
        if isinstance(pid, int) and _process_exists(pid):
            return False
        if not isinstance(pid, int):
            try:
                if _lock_age_seconds(lock_path) < _MALFORMED_LOCK_GRACE_SECONDS:
                    return False
            except FileNotFoundError:
                return True
            except OSError:
                return False
    else:
        try:
            if _lock_age_seconds(lock_path) < _MALFORMED_LOCK_GRACE_SECONDS:
                return False
        except FileNotFoundError:
            return True
        except OSError:
            return False
    try:
        lock_path.unlink()
    except FileNotFoundError:
        pass
    except OSError:
        return False
    return True


def _acquire_lock(root: Path) -> tuple[Path, str]:
    lock_path = _lock_path(root)
    token = uuid.uuid4().hex
    payload = json.dumps({
        "pid": os.getpid(), "root": str(root.resolve()),
        "created_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "token": token,
    }, sort_keys=True).encode("utf-8")
    for attempt in range(2):
        try:
            descriptor = os.open(lock_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
        except FileExistsError as exc:
            if attempt == 0 and _remove_stale_lock(lock_path, root):
                continue
            raise TransactionError(f"Another Cruthunas transaction is active for {root}") from exc
        try:
            os.write(descriptor, payload)
            os.fsync(descriptor)
        finally:
            os.close(descriptor)
        return lock_path, token
    raise TransactionError(f"Could not acquire Cruthunas transaction lock for {root}")


def _release_lock(lock_path: Path, token: str) -> None:
    record = _read_lock(lock_path)
    if record is not None and record.get("token") != token:
        return
    lock_path.unlink(missing_ok=True)


def _created_parent_directories(root: Path, parent: Path) -> list[Path]:
    created: list[Path] = []
    current = parent
    root = root.resolve()
    while current != root and not current.exists():
        created.append(current)
        current = current.parent
    return created


def _current_hash(path: Path) -> str | None:
    return _sha256_bytes(path.read_bytes()) if path.is_file() else None


def _assert_write_target_unchanged(plan: TransactionPlan, item: PlannedWrite) -> None:
    target = _resolve_relative(plan.root, item.path)
    current = _current_hash(target)
    if current != item.expected_sha256:
        raise TransactionError(f"Concurrent modification detected for {item.path}; rebuild the transaction preview")


def _check_preconditions(plan: TransactionPlan) -> None:
    if plan.expected_git_head is not None:
        current_head = _git_head(plan.root)
        if current_head != plan.expected_git_head:
            raise TransactionError("Git HEAD changed after the transaction preview; rebuild the transaction", details={"expected_git_head": plan.expected_git_head, "current_git_head": current_head})
        dirty = _git_status(plan.root)
        if dirty:
            raise TransactionError("Working tree changed after the transaction preview; rebuild the transaction", details={"dirty_paths": dirty.splitlines()})
    for item in plan.reads:
        target = _resolve_relative(plan.root, item.path)
        current = _current_hash(target)
        if current != item.expected_sha256:
            raise TransactionError(f"Transaction input changed after preview: {item.path}; rebuild the transaction")
    for item in plan.writes:
        _assert_write_target_unchanged(plan, item)


def apply_plan(plan: TransactionPlan) -> dict[str, Any]:
    lock_path, lock_token = _acquire_lock(plan.root)
    try:
        _check_preconditions(plan)
        with tempfile.TemporaryDirectory(prefix="cruthunas-commit-") as temporary:
            backup_root = Path(temporary) / "backups"
            prepared: list[tuple[PlannedWrite, Path]] = []
            replaced: list[tuple[PlannedWrite, Path | None]] = []
            created_directories: list[Path] = []
            try:
                for item in plan.writes:
                    target = _resolve_relative(plan.root, item.path)
                    created_directories.extend(path for path in _created_parent_directories(plan.root, target.parent) if path not in created_directories)
                    target.parent.mkdir(parents=True, exist_ok=True)
                    handle = tempfile.NamedTemporaryFile(prefix=f".{target.name}.", suffix=".tmp", dir=target.parent, delete=False)
                    try:
                        handle.write(item.content)
                        handle.flush()
                        os.fsync(handle.fileno())
                        temp_path = Path(handle.name)
                    finally:
                        handle.close()
                    prepared.append((item, temp_path))
                for item, temp_path in prepared:
                    target = _resolve_relative(plan.root, item.path)
                    _assert_write_target_unchanged(plan, item)
                    backup: Path | None = None
                    if target.is_file():
                        backup = backup_root / item.path
                        backup.parent.mkdir(parents=True, exist_ok=True)
                        shutil.copy2(target, backup)
                    _assert_write_target_unchanged(plan, item)
                    os.replace(temp_path, target)
                    replaced.append((item, backup))
                _validate_result(plan, run_checks(plan.root), phase="apply")
                return plan.to_dict(applied=True)
            except Exception as exc:
                rollback_errors: list[str] = []
                for item, backup in reversed(replaced):
                    target = _resolve_relative(plan.root, item.path)
                    try:
                        if backup is None:
                            target.unlink(missing_ok=True)
                        else:
                            target.parent.mkdir(parents=True, exist_ok=True)
                            shutil.copy2(backup, target)
                    except OSError as rollback_exc:
                        rollback_errors.append(f"{item.path}: {rollback_exc}")
                for directory in created_directories:
                    try:
                        directory.rmdir()
                    except OSError:
                        pass
                if rollback_errors:
                    raise TransactionError("Transaction failed and rollback was incomplete", exit_code=5, details={"original_error": str(exc), "rollback_errors": rollback_errors}) from exc
                raise
            finally:
                for _item, temp_path in prepared:
                    temp_path.unlink(missing_ok=True)
    finally:
        _release_lock(lock_path, lock_token)
