"""Helpers for parsing registry size/date values and formatting byte counts."""

from __future__ import annotations

from datetime import datetime


def parse_estimated_size_kb(value: int | str | None) -> int | None:
    """Registry EstimatedSize is stored in KiB (DWORD). Returns bytes."""
    if value is None:
        return None
    try:
        kb = int(value)
    except (TypeError, ValueError):
        return None
    if kb <= 0:
        return None
    return kb * 1024


def parse_install_date(value: str | None) -> datetime | None:
    """Registry InstallDate is usually 'YYYYMMDD'. Be defensive about other formats."""
    if not value:
        return None
    value = value.strip()
    for fmt in ("%Y%m%d", "%m/%d/%Y", "%Y-%m-%d"):
        try:
            return datetime.strptime(value, fmt)
        except ValueError:
            continue
    return None


def format_bytes(num_bytes: int) -> str:
    if num_bytes < 0:
        return "Unknown"
    step = 1024.0
    units = ["B", "KB", "MB", "GB", "TB", "PB"]
    size = float(num_bytes)
    for unit in units:
        if size < step or unit == units[-1]:
            if unit == "B":
                return f"{int(size)} {unit}"
            return f"{size:.1f} {unit}"
        size /= step
    return f"{size:.1f} PB"
