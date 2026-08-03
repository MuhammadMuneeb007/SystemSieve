"""Safe, user-initiated Windows Explorer actions used by GUI pages."""

from __future__ import annotations

import ctypes
import os
import re
from pathlib import Path


def open_path(path: Path) -> None:
    """Open an existing path through the Windows Shell."""
    target = _validated_target(path)
    _shell_execute(str(target))


def reveal_in_explorer(path: Path) -> None:
    """Select a file in Explorer, or open a directory directly."""
    target = _validated_target(path)
    if target.is_dir():
        open_path(target)
        return
    explorer = Path(os.environ.get("WINDIR", r"C:\Windows")) / "explorer.exe"
    if not explorer.is_file():
        raise FileNotFoundError("Windows Explorer could not be found.")
    _shell_execute(str(explorer), f'/select,"{target}"')


def existing_location(*candidates: Path | str | None) -> Path | None:
    """Return the first existing candidate from common Windows registry formats."""
    for candidate in candidates:
        if not candidate:
            continue
        raw = os.path.expandvars(str(candidate).strip())
        quoted = re.match(r'^"([^"]+)"', raw)
        raw = quoted.group(1) if quoted else re.sub(r",\s*-?\d+\s*$", "", raw).strip().strip('"')
        path = Path(raw).expanduser()
        if path.exists():
            return path.resolve()
    return None


def _validated_target(path: Path) -> Path:
    target = path.expanduser().resolve()
    if not target.exists():
        raise FileNotFoundError(f"Path does not exist: {target}")
    return target


def _shell_execute(target: str, parameters: str | None = None) -> None:
    result = ctypes.windll.shell32.ShellExecuteW(None, "open", target, parameters, None, 1)
    if result <= 32:
        raise OSError(f"Windows could not open the requested location (ShellExecuteW {result}).")
