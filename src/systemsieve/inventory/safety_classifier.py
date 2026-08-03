"""Heuristic safety classification for installed applications.

Produces a safety_level ('normal' | 'review' | 'protected' | 'unknown') plus
human-readable reasons. This is advisory: a 'normal' classification is never a
guarantee that removal is harmless, and callers must not present it as one.
"""

from __future__ import annotations

import re

from systemsieve.constants import (
    PROTECTED_HARD_BLOCK_KEYWORDS,
    SAFETY_NORMAL,
    SAFETY_PROTECTED,
    SAFETY_REVIEW,
    SAFETY_UNKNOWN,
    WARN_BEFORE_REMOVAL_CATEGORIES,
)
from systemsieve.models.application import InstalledApplication


def _text_matches_any(text: str, patterns: list[str]) -> bool:
    return any(re.search(p, text, re.IGNORECASE) for p in patterns)


def classify(app: InstalledApplication) -> tuple[str, list[str]]:
    """Returns (safety_level, reasons)."""
    haystack = " ".join(
        filter(None, [app.display_name, app.publisher, str(app.install_location or "")])
    ).lower()

    reasons: list[str] = []

    if _text_matches_any(haystack, PROTECTED_HARD_BLOCK_KEYWORDS):
        return SAFETY_PROTECTED, [
            "Protected because this appears to be a core Windows OS component."
        ]

    if app.system_component:
        reasons.append("Protected because the registry marks this as a Windows system component.")
        return SAFETY_PROTECTED, reasons

    if app.install_location:
        loc = str(app.install_location).lower()
        if re.search(r"^[a-z]:\\windows(\\|$)", loc) or "system32" in loc or "syswow64" in loc:
            reasons.append("Protected because it is installed inside the Windows system directory.")
            return SAFETY_PROTECTED, reasons

    for category, keywords in WARN_BEFORE_REMOVAL_CATEGORIES.items():
        if _text_matches_any(haystack, keywords):
            if category == "Hardware Driver":
                reasons.append(f"Protected because this appears to be a {category.lower()}.")
                return SAFETY_PROTECTED, reasons
            reasons.append(f"Review recommended because this is a {category.lower()}.")

    if reasons:
        return SAFETY_REVIEW, reasons

    if not app.publisher and not app.uninstall_command and not app.quiet_uninstall_command:
        reasons.append("Unknown because the publisher and uninstall method could not be verified.")
        return SAFETY_UNKNOWN, reasons

    if app.uninstall_confidence == "low":
        reasons.append(
            "Review recommended because the uninstall command could not be confidently validated."
        )
        return SAFETY_REVIEW, reasons

    reasons.append(
        "No known risk indicators were found, but removal is not guaranteed to be harmless."
    )
    return SAFETY_NORMAL, reasons
