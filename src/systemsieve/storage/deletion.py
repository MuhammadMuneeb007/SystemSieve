"""Safe file deletion: Recycle Bin by default, permanent only with explicit opt-in.

Whole protected directories can never be passed through here as deletion
targets -- callers are expected to operate on individual FileItem paths, and
this module additionally refuses any path that resolves to a protected
directory itself (as opposed to a file within one).
"""

from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel
from send2trash import send2trash

from systemsieve.logging_config import get_logger
from systemsieve.storage.protected_paths import is_protected_directory, is_protected_file

logger = get_logger("storage")


class DeletionResult(BaseModel):
    path: str
    success: bool
    permanent: bool
    message: str


def validate_deletion_targets(paths: list[Path]) -> tuple[list[Path], list[DeletionResult]]:
    """Splits paths into (allowed, rejected-with-reason)."""
    allowed: list[Path] = []
    rejected: list[DeletionResult] = []

    for path in paths:
        if path.is_dir():
            blocked, reason = is_protected_directory(path)
            if blocked:
                rejected.append(
                    DeletionResult(path=str(path), success=False, permanent=False, message=reason)
                )
                continue

        blocked, reason = is_protected_file(path)
        if blocked:
            rejected.append(
                DeletionResult(path=str(path), success=False, permanent=False, message=reason)
            )
            continue

        if not path.exists():
            rejected.append(
                DeletionResult(
                    path=str(path), success=False, permanent=False, message="Path no longer exists."
                )
            )
            continue

        allowed.append(path)

    return allowed, rejected


def delete_files(paths: list[Path], *, permanent: bool = False) -> list[DeletionResult]:
    """Deletes files. Sends to Recycle Bin unless permanent=True.

    Callers (GUI/CLI) are responsible for obtaining user confirmation --
    including a second, explicit confirmation for permanent=True -- before
    calling this function.
    """
    allowed, results = validate_deletion_targets(paths)

    for path in allowed:
        try:
            if permanent:
                path.unlink()
                results.append(
                    DeletionResult(
                        path=str(path), success=True, permanent=True, message="Permanently deleted."
                    )
                )
            else:
                send2trash(str(path))
                results.append(
                    DeletionResult(
                        path=str(path),
                        success=True,
                        permanent=False,
                        message="Moved to Recycle Bin.",
                    )
                )
        except OSError as exc:
            logger.warning("Failed to delete %s: %s", path, exc)
            results.append(
                DeletionResult(path=str(path), success=False, permanent=permanent, message=str(exc))
            )

    return results


def total_size(paths: list[Path]) -> int:
    total = 0
    for path in paths:
        try:
            total += path.stat().st_size
        except OSError:
            continue
    return total
