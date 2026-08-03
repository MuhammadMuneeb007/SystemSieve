"""File categorisation by extension and, for special directories, by context."""

from __future__ import annotations

from pathlib import Path

from systemsieve.constants import (
    CACHE_DIRECTORY_NAMES,
    FILE_CATEGORY_EXTENSIONS,
    VENV_DIRECTORY_NAMES,
)
from systemsieve.models.storage import FileCategory

_EXTENSION_TO_CATEGORY: dict[str, FileCategory] = {}
for _category_name, _extensions in FILE_CATEGORY_EXTENSIONS.items():
    try:
        _category_enum = FileCategory(_category_name)
    except ValueError:
        continue
    for _ext in _extensions:
        _EXTENSION_TO_CATEGORY[_ext.lower()] = _category_enum


def category_for_directory_context(parts_lower: list[str]) -> FileCategory | None:
    """If any path component matches a venv/cache directory name, categorise accordingly."""
    for part in parts_lower:
        if part in VENV_DIRECTORY_NAMES:
            return FileCategory.VIRTUAL_ENVIRONMENTS
    for part in parts_lower:
        if part in CACHE_DIRECTORY_NAMES:
            return FileCategory.APPLICATION_CACHES
    return None


def categorize_file(path: Path) -> FileCategory:
    parts_lower = [p.lower() for p in path.parts]
    context_category = category_for_directory_context(parts_lower)
    if context_category is not None:
        return context_category

    suffix = path.suffix.lower()
    if path.name.lower().endswith(".fastq.gz") or path.name.lower().endswith(".vcf.gz"):
        suffix = "." + ".".join(path.name.lower().split(".")[-2:])

    return _EXTENSION_TO_CATEGORY.get(suffix, FileCategory.UNKNOWN)
