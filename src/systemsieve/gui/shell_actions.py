"""Safe, user-initiated Windows Explorer actions used by GUI pages."""

from __future__ import annotations

import os
import subprocess
from pathlib import Path


def open_path(path: Path) -> None:
    """Open a file or directory with its registered Windows application."""
    os.startfile(str(path))  # noqa: S606 - explicit user action, no shell command


def reveal_in_explorer(path: Path) -> None:
    """Select a file in Explorer, or open a directory directly."""
    target = path.expanduser().resolve()
    if target.is_dir():
        open_path(target)
        return
    subprocess.Popen(["explorer.exe", f"/select,{target}"], shell=False)  # noqa: S603


def existing_location(*candidates: Path | str | None) -> Path | None:
    """Return the first existing candidate, tolerating quoted registry paths."""
    for candidate in candidates:
        if not candidate:
            continue
        raw = str(candidate).strip().strip('"')
        path = Path(raw)
        if path.exists():
            return path
    return None
