"""Identifies filesystem paths that must never be deleted as whole directories.

Scanning these locations is always permitted; only whole-directory deletion is
blocked here. Individual files within them are still subject to normal
deletion rules and confirmation elsewhere.
"""

from __future__ import annotations

import os
import string
from pathlib import Path

from systemsieve.constants import PROTECTED_DIRECTORY_NAMES


def _drive_roots() -> list[Path]:
    roots = []
    for letter in string.ascii_uppercase:
        candidate = Path(f"{letter}:\\")
        if candidate.exists():
            roots.append(candidate)
    return roots


def _user_profile_root() -> Path | None:
    home = os.environ.get("USERPROFILE")
    return Path(home) if home else None


def _recovery_partition_markers() -> list[str]:
    return ["recovery", "\\windows re\\", "\\reagent\\"]


def is_protected_directory(path: Path) -> tuple[bool, str]:
    """Returns (is_protected, reason). Only meaningful for directories."""
    try:
        resolved = path.resolve()
    except OSError:
        resolved = path

    resolved_str = str(resolved).rstrip("\\").lower()

    for root in _drive_roots():
        if resolved_str == str(root).rstrip("\\").lower():
            return True, "This is the root of a drive and cannot be deleted as a whole directory."

    for name in PROTECTED_DIRECTORY_NAMES:
        # Match e.g. C:\Windows, C:\Program Files, C:\ProgramData at any drive letter.
        candidate_suffix = f":\\{name}"
        if resolved_str.endswith(candidate_suffix.lower()):
            return True, f"'{path}' is a protected Windows system directory and cannot be deleted."

    profile_root = _user_profile_root()
    if profile_root is not None:
        try:
            if resolved.resolve() == profile_root.resolve():
                return (
                    True,
                    "This is the current user's profile root and cannot be deleted as a whole directory.",
                )
        except OSError:
            pass

    for marker in _recovery_partition_markers():
        if marker in f"\\{resolved_str}\\":
            return True, "This appears to be a Windows recovery location and cannot be deleted."

    return False, ""


def is_protected_file(path: Path) -> tuple[bool, str]:
    """A conservative check for individual files that must never be deleted."""
    resolved_str = str(path).lower()
    windows_dir = os.environ.get("WINDIR", r"C:\Windows").lower()
    if resolved_str.startswith(windows_dir.lower() + "\\"):
        return (
            True,
            "Files inside the Windows system directory are not eligible for deletion through SystemSieve.",
        )
    return False, ""
