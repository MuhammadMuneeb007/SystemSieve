"""Cancellable, metadata-only disk scanner.

Implemented in pure Python/stdlib for the first release. The public surface
(`ScanOptions`, `ScanProgress`, and the `scan` function) is intentionally
narrow so that a future, faster (e.g. Rust) implementation can be substituted
behind the same interface without touching callers.

Design notes:
  * Traversal is an iterative, two-phase (explore / finalize) post-order walk
    using an explicit stack, so very deep directory trees cannot cause a
    Python recursion error, and recursive folder sizes are only recorded
    once every descendant has been fully accounted for.
  * Reparse points (symlinks/junctions) are not followed by default, and a
    visited-inode set provides defense-in-depth against loops even when they
    are.
  * Only file metadata (name, size, mtime) is read -- file contents are never
    opened.
  * Progress and cancellation are cooperative: the caller polls or reacts to
    callbacks between directory batches, never mid-syscall.
"""

from __future__ import annotations

import heapq
import os
import threading
import time
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path

from systemsieve.constants import DEFAULT_OLD_FILE_DAYS, DEFAULT_RECENT_FILE_DAYS
from systemsieve.logging_config import get_logger
from systemsieve.models.storage import FileItem, FolderItem, ScanError, ScanSummary
from systemsieve.storage.categories import categorize_file

logger = get_logger("storage")

FILE_ATTRIBUTE_REPARSE_POINT = 0x400

_TOP_N = 200


@dataclass
class ScanOptions:
    include_hidden: bool = False
    follow_reparse_points: bool = False
    old_file_days: int = DEFAULT_OLD_FILE_DAYS
    recent_file_days: int = DEFAULT_RECENT_FILE_DAYS
    top_n: int = _TOP_N


@dataclass
class ScanProgress:
    files_scanned: int = 0
    folders_scanned: int = 0
    bytes_scanned: int = 0
    current_path: str = ""


ProgressCallback = Callable[[ScanProgress], None]


@dataclass
class _DirNode:
    path: Path
    total_size: int = 0
    file_count: int = 0
    subfolder_count: int = 0
    latest_mtime: float = 0.0
    parent: _DirNode | None = None


def _is_reparse_point(entry_stat: os.stat_result) -> bool:
    attrs = getattr(entry_stat, "st_file_attributes", 0)
    return bool(attrs & FILE_ATTRIBUTE_REPARSE_POINT)


def _push_bounded_heap(heap: list, item: tuple, top_n: int) -> None:
    if len(heap) < top_n:
        heapq.heappush(heap, item)
    else:
        heapq.heappushpop(heap, item)


def scan(
    root: str | Path,
    options: ScanOptions | None = None,
    *,
    on_progress: ProgressCallback | None = None,
    cancel_event: threading.Event | None = None,
    progress_interval_files: int = 250,
) -> ScanSummary:
    options = options or ScanOptions()
    root_path = Path(root)
    summary = ScanSummary(root_path=str(root_path))

    if not root_path.exists():
        summary.errors.append(ScanError(path=str(root_path), reason="Path does not exist."))
        summary.error_count = 1
        summary.completed_at = datetime.now()
        return summary

    largest_files_heap: list[tuple[int, str, FileItem]] = []
    largest_folders_heap: list[tuple[int, str, FolderItem]] = []
    old_files_heap: list[tuple[float, str, FileItem]] = []
    recent_files: list[FileItem] = []
    category_totals: dict[str, int] = {}
    extension_totals: dict[str, int] = {}

    now = datetime.now()
    old_threshold = (now - timedelta(days=options.old_file_days)).timestamp()
    recent_threshold = (now - timedelta(days=options.recent_file_days)).timestamp()

    visited_ids: set[tuple[int, int]] = set()
    progress = ScanProgress()
    last_progress_emit = time.monotonic()

    # Stack of (node, state), state in {"explore", "finalize"}.
    stack: list[tuple[_DirNode, str]] = [(_DirNode(path=root_path), "explore")]

    def emit_progress(force: bool = False) -> None:
        nonlocal last_progress_emit
        if not on_progress:
            return
        now_mono = time.monotonic()
        if force or now_mono - last_progress_emit > 0.05:
            on_progress(progress)
            last_progress_emit = now_mono

    cancelled = False

    while stack:
        if cancel_event is not None and cancel_event.is_set():
            cancelled = True
            break

        node, state = stack.pop()

        if state == "finalize":
            folder_item = FolderItem(
                path=str(node.path),
                total_size_bytes=node.total_size,
                file_count=node.file_count,
                subfolder_count=node.subfolder_count,
                modified=datetime.fromtimestamp(node.latest_mtime) if node.latest_mtime else None,
            )
            _push_bounded_heap(
                largest_folders_heap, (node.total_size, str(node.path), folder_item), options.top_n
            )
            if node.parent is not None:
                node.parent.total_size += node.total_size
                node.parent.file_count += node.file_count
                node.parent.latest_mtime = max(node.parent.latest_mtime, node.latest_mtime)
            continue

        # state == "explore"
        progress.folders_scanned += 1
        progress.current_path = str(node.path)

        try:
            dir_stat = node.path.stat()
        except OSError as exc:
            summary.errors.append(ScanError(path=str(node.path), reason=str(exc)))
            summary.error_count += 1
            continue

        dir_id = (getattr(dir_stat, "st_dev", 0), getattr(dir_stat, "st_ino", 0))
        if dir_id != (0, 0) and dir_id in visited_ids:
            continue
        visited_ids.add(dir_id)

        try:
            with os.scandir(node.path) as it:
                entries = list(it)
        except (PermissionError, OSError) as exc:
            summary.errors.append(ScanError(path=str(node.path), reason=str(exc)))
            summary.error_count += 1
            continue

        stack.append((node, "finalize"))

        for entry in entries:
            if cancel_event is not None and cancel_event.is_set():
                cancelled = True
                break

            name = entry.name
            if not options.include_hidden and name.startswith("."):
                continue

            try:
                is_dir = entry.is_dir(follow_symlinks=False)
                is_symlink = entry.is_symlink()
                entry_stat = entry.stat(follow_symlinks=False)
            except OSError as exc:
                summary.errors.append(ScanError(path=entry.path, reason=str(exc)))
                summary.error_count += 1
                continue

            is_reparse = is_symlink or _is_reparse_point(entry_stat)

            if is_dir:
                node.subfolder_count += 1
                if is_reparse and not options.follow_reparse_points:
                    continue
                child = _DirNode(path=Path(entry.path), parent=node)
                stack.append((child, "explore"))
                continue

            if is_reparse and not options.follow_reparse_points:
                continue

            size = entry_stat.st_size
            mtime = entry_stat.st_mtime

            node.total_size += size
            node.file_count += 1
            node.latest_mtime = max(node.latest_mtime, mtime)

            progress.files_scanned += 1
            progress.bytes_scanned += size

            file_path = Path(entry.path)
            category = categorize_file(file_path)
            extension = file_path.suffix.lower()

            category_totals[category.value] = category_totals.get(category.value, 0) + size
            if extension:
                extension_totals[extension] = extension_totals.get(extension, 0) + size

            file_item = FileItem(
                path=str(file_path),
                size_bytes=size,
                modified=datetime.fromtimestamp(mtime),
                category=category,
                extension=extension,
            )

            _push_bounded_heap(largest_files_heap, (size, str(file_path), file_item), options.top_n)
            if mtime < old_threshold:
                _push_bounded_heap(
                    old_files_heap, (-mtime, str(file_path), file_item), options.top_n
                )
            if mtime >= recent_threshold:
                recent_files.append(file_item)

            if progress.files_scanned % progress_interval_files == 0:
                emit_progress()

        if cancelled:
            break

    emit_progress(force=True)

    summary.cancelled = cancelled
    summary.total_files = progress.files_scanned
    summary.total_folders = progress.folders_scanned
    summary.total_size_bytes = progress.bytes_scanned
    summary.category_totals = category_totals
    summary.extension_totals = extension_totals
    summary.largest_files = [item for _, _, item in sorted(largest_files_heap, key=lambda t: -t[0])]
    summary.largest_folders = [
        item for _, _, item in sorted(largest_folders_heap, key=lambda t: -t[0])
    ]
    summary.old_files = [item for _, _, item in sorted(old_files_heap, key=lambda t: t[0])]
    recent_files.sort(key=lambda f: f.modified or datetime.min, reverse=True)
    summary.recent_files = recent_files[: options.top_n]
    summary.completed_at = datetime.now()

    logger.info(
        "Scan of %s complete: %d files, %d folders, %d bytes, %d errors, cancelled=%s",
        root_path,
        summary.total_files,
        summary.total_folders,
        summary.total_size_bytes,
        summary.error_count,
        summary.cancelled,
    )
    return summary
