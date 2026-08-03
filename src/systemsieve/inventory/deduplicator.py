"""Merges registry-derived and WinGet-derived application records.

Matching strategy: normalize display names (lowercase, strip punctuation and
common suffixes) and compare for equality or high similarity. This is a
heuristic -- when in doubt we keep records separate rather than risk merging
two unrelated applications.
"""

from __future__ import annotations

import re
from difflib import SequenceMatcher

from systemsieve.logging_config import get_logger
from systemsieve.models.application import InstalledApplication

logger = get_logger("inventory")

_SIMILARITY_THRESHOLD = 0.86


def _normalize(name: str) -> str:
    name = name.lower()
    name = re.sub(r"\(.*?\)", "", name)
    name = re.sub(r"[^a-z0-9]+", " ", name)
    name = re.sub(r"\bx(64|86)\b", "", name)
    return name.strip()


def _similar(a: str, b: str) -> bool:
    if not a or not b:
        return False
    if a == b:
        return True
    if a in b or b in a:
        return True
    return SequenceMatcher(None, a, b).ratio() >= _SIMILARITY_THRESHOLD


def deduplicate(
    registry_apps: list[InstalledApplication],
    winget_apps: list[InstalledApplication],
) -> list[InstalledApplication]:
    merged: list[InstalledApplication] = []
    matched_winget_ids: set[str] = set()

    normalized_registry = [(app, _normalize(app.display_name)) for app in registry_apps]
    normalized_winget = [(app, _normalize(app.display_name)) for app in winget_apps]

    for reg_app, reg_norm in normalized_registry:
        match: InstalledApplication | None = None
        for wg_app, wg_norm in normalized_winget:
            if wg_app.id in matched_winget_ids:
                continue
            if _similar(reg_norm, wg_norm):
                match = wg_app
                break

        if match is not None:
            matched_winget_ids.add(match.id)
            merged_app = reg_app.model_copy(
                update={
                    "source": "registry+winget",
                    "winget_id": match.winget_id,
                    "uninstall_confidence": "high",
                }
            )
            merged.append(merged_app)
        else:
            merged.append(reg_app)

    for wg_app, _norm in normalized_winget:
        if wg_app.id not in matched_winget_ids:
            merged.append(wg_app)

    logger.info(
        "Deduplication merged %d registry + %d winget entries into %d records",
        len(registry_apps),
        len(winget_apps),
        len(merged),
    )
    return merged
