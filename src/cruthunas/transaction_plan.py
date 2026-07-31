from __future__ import annotations

import hashlib
import os
import shutil
import tempfile
from pathlib import Path
from typing import Any

from .policy import run_checks
from .transaction_types import (
    PlannedWrite,
    TransactionError,
    TransactionPlan,
    _planned_write,
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
            raise TransactionError(
                "Prospective transaction violates Cruthunas policy",
                details=result.to_dict(),
            )


def _plan(
    root: Path,
    operation: str,
    writes: list[tuple[str, bytes]],
    preview: dict[str, Any],
) -> TransactionPlan:
    seen: set[str] = set()
    planned: list[PlannedWrite] = []
    for relative, content in writes:
        normalized = _relative_text(root, relative)
        if normalized in seen:
            raise TransactionError(f"Transaction writes the same path twice: {normalized}", exit_code=5)
        seen.add(normalized)
        planned.append(_planned_write(root, normalized, content))
    plan = TransactionPlan(root.resolve(), operation, tuple(planned), preview)
    _validate_plan(plan)
    return plan

def _lock_path(root: Path) -> Path:
    digest = hashlib.sha256(str(root.resolve()).encode("utf-8")).hexdigest()[:20]
    return Path(tempfile.gettempdir()) / f"cruthunas-{digest}.lock"


def apply_plan(plan: TransactionPlan) -> dict[str, Any]:
    lock_path = _lock_path(plan.root)
    try:
        descriptor = os.open(lock_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    except FileExistsError as exc:
        raise TransactionError(f"Another Cruthunas transaction is active for {plan.root}") from exc
    try:
        os.write(descriptor, str(os.getpid()).encode("ascii"))
    finally:
        os.close(descriptor)

    with tempfile.TemporaryDirectory(prefix="cruthunas-commit-") as temporary:
        backup_root = Path(temporary) / "backups"
        prepared: list[tuple[PlannedWrite, Path, Path | None]] = []
        replaced: list[tuple[PlannedWrite, Path | None]] = []
        try:
            for item in plan.writes:
                target = _resolve_relative(plan.root, item.path)
                current = _sha256_bytes(target.read_bytes()) if target.is_file() else None
                if current != item.expected_sha256:
                    raise TransactionError(
                        f"Concurrent modification detected for {item.path}; rebuild the transaction preview"
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
        except Exception:
            for item, backup in reversed(replaced):
                target = _resolve_relative(plan.root, item.path)
                try:
                    if backup is None:
                        target.unlink(missing_ok=True)
                    else:
                        target.parent.mkdir(parents=True, exist_ok=True)
                        shutil.copy2(backup, target)
                except OSError:
                    pass
            raise
        finally:
            for _item, temp_path, _backup in prepared:
                temp_path.unlink(missing_ok=True)
            lock_path.unlink(missing_ok=True)
