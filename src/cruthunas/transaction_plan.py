from __future__ import annotations

import hashlib
import os
import shutil
import tempfile
from pathlib import Path
from typing import Any

from .policy import run_checks
from .transaction_types import (
    FileSnapshot,
    PlannedRead,
    PlannedWrite,
    TransactionError,
    TransactionPlan,
    _git_head,
    _git_status,
    _planned_read,
    _planned_write,
    _snapshot_read,
    _snapshot_write,
    _relative_text,
    _resolve_relative,
    _sha256_bytes,
)


def _ignore_shadow(_directory: str, names: list[str]) -> set[str]:
    ignored = {".git", ".venv", "venv", "node_modules", "__pycache__", ".pytest_cache"}
    return ignored.intersection(names)


def _apply_writes_to(root: Path, writes: tuple[PlannedWrite, ...]) -> None:
    for item in writes:
        target = _resolve_relative(root, item.path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(item.content)


def _validate_plan(plan: TransactionPlan) -> None:
    with tempfile.TemporaryDirectory(prefix="cruthunas-preview-") as temporary:
        shadow = Path(temporary) / "repo"
        shutil.copytree(
            plan.root,
            shadow,
            symlinks=True,
            ignore=_ignore_shadow,
        )
        _apply_writes_to(shadow, plan.writes)
        result = run_checks(shadow)
        if not result.ok:
            message = "Prospective transaction violates Cruthunas policy"
            if result.findings:
                first = result.findings[0]
                message = f"{message}: {first.message} [{first.code}]"
            raise TransactionError(
                message,
                details=result.to_dict(),
            )


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
) -> TransactionPlan:
    normalized_write_snapshots = {
        _relative_text(root, path): snapshot
        for path, snapshot in (write_snapshots or {}).items()
    }
    seen_writes: set[str] = set()
    planned_writes: list[PlannedWrite] = []
    for relative, content in writes:
        normalized = _relative_text(root, relative)
        if normalized in seen_writes:
            raise TransactionError(
                f"Transaction writes the same path twice: {normalized}",
                exit_code=5,
            )
        seen_writes.add(normalized)
        snapshot = normalized_write_snapshots.get(normalized)
        if snapshot is not None:
            if snapshot.path != normalized:
                raise TransactionError(
                    f"Write snapshot path mismatch: {snapshot.path} != {normalized}",
                    exit_code=5,
                )
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
            raise TransactionError(
                f"Read snapshot path mismatch: {snapshot.path} != {normalized}",
                exit_code=5,
            )
        seen_reads.add(normalized)
        planned_reads.append(_snapshot_read(snapshot))
    for value in reads or []:
        normalized = _relative_text(root, value)
        if normalized in seen_writes or normalized in seen_reads:
            continue
        seen_reads.add(normalized)
        planned_reads.append(_planned_read(root, normalized))

    plan = TransactionPlan(
        root.resolve(),
        operation,
        tuple(planned_reads),
        tuple(planned_writes),
        expected_git_head,
        preview,
    )
    _validate_plan(plan)
    return plan


def _lock_path(root: Path) -> Path:
    digest = hashlib.sha256(str(root.resolve()).encode("utf-8")).hexdigest()[:20]
    return Path(tempfile.gettempdir()) / f"cruthunas-{digest}.lock"


def _created_parent_directories(root: Path, parent: Path) -> list[Path]:
    created: list[Path] = []
    current = parent
    root = root.resolve()
    while current != root and not current.exists():
        created.append(current)
        current = current.parent
    return created


def _check_preconditions(plan: TransactionPlan) -> None:
    if plan.expected_git_head is not None:
        current_head = _git_head(plan.root)
        if current_head != plan.expected_git_head:
            raise TransactionError(
                "Git HEAD changed after the transaction preview; rebuild the transaction",
                details={
                    "expected_git_head": plan.expected_git_head,
                    "current_git_head": current_head,
                },
            )
        dirty = _git_status(plan.root)
        if dirty:
            raise TransactionError(
                "Working tree changed after the transaction preview; rebuild the transaction",
                details={"dirty_paths": dirty.splitlines()},
            )
    for item in plan.reads:
        target = _resolve_relative(plan.root, item.path)
        current = _sha256_bytes(target.read_bytes()) if target.is_file() else None
        if current != item.expected_sha256:
            raise TransactionError(
                f"Transaction input changed after preview: {item.path}; rebuild the transaction"
            )
    for item in plan.writes:
        target = _resolve_relative(plan.root, item.path)
        current = _sha256_bytes(target.read_bytes()) if target.is_file() else None
        if current != item.expected_sha256:
            raise TransactionError(
                f"Concurrent modification detected for {item.path}; rebuild the transaction preview"
            )


def apply_plan(plan: TransactionPlan) -> dict[str, Any]:
    lock_path = _lock_path(plan.root)
    try:
        descriptor = os.open(lock_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    except FileExistsError as exc:
        raise TransactionError(f"Another Cruthunas transaction is active for {plan.root}") from exc
    try:
        try:
            os.write(descriptor, str(os.getpid()).encode("ascii"))
        finally:
            os.close(descriptor)

        _check_preconditions(plan)
        with tempfile.TemporaryDirectory(prefix="cruthunas-commit-") as temporary:
            backup_root = Path(temporary) / "backups"
            prepared: list[tuple[PlannedWrite, Path, Path | None]] = []
            replaced: list[tuple[PlannedWrite, Path | None]] = []
            created_directories: list[Path] = []
            try:
                for item in plan.writes:
                    target = _resolve_relative(plan.root, item.path)
                    created_directories.extend(
                        path
                        for path in _created_parent_directories(plan.root, target.parent)
                        if path not in created_directories
                    )
                    target.parent.mkdir(parents=True, exist_ok=True)
                    backup: Path | None = None
                    if target.is_file():
                        backup = backup_root / item.path
                        backup.parent.mkdir(parents=True, exist_ok=True)
                        shutil.copy2(target, backup)
                    handle = tempfile.NamedTemporaryFile(
                        prefix=f".{target.name}.",
                        suffix=".tmp",
                        dir=target.parent,
                        delete=False,
                    )
                    try:
                        handle.write(item.content)
                        handle.flush()
                        os.fsync(handle.fileno())
                        temp_path = Path(handle.name)
                    finally:
                        handle.close()
                    prepared.append((item, temp_path, backup))

                for item, temp_path, backup in prepared:
                    target = _resolve_relative(plan.root, item.path)
                    os.replace(temp_path, target)
                    replaced.append((item, backup))

                result = run_checks(plan.root)
                if not result.ok:
                    raise TransactionError(
                        "Applied transaction failed post-write validation",
                        exit_code=5,
                        details=result.to_dict(),
                    )
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
                    raise TransactionError(
                        "Transaction failed and rollback was incomplete",
                        exit_code=5,
                        details={
                            "original_error": str(exc),
                            "rollback_errors": rollback_errors,
                        },
                    ) from exc
                raise
            finally:
                for _item, temp_path, _backup in prepared:
                    temp_path.unlink(missing_ok=True)
    finally:
        lock_path.unlink(missing_ok=True)
