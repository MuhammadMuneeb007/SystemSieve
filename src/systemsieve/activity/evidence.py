"""Read-only, conservative sources of "was this application recently used" evidence.

Every function here returns an ActivityEvidence with an honest confidence level
and explanation. None of these sources prove usage on an exact date -- they are
signals, and the explanation text must make that clear to the end user.
"""

from __future__ import annotations

import sys
from datetime import datetime
from pathlib import Path

from systemsieve.models.activity import ActivityConfidence, ActivityEvidence

_PREFETCH_DIR = Path(r"C:\Windows\Prefetch")


def _find_candidate_executables(install_location: Path | None) -> list[Path]:
    if not install_location or not install_location.exists():
        return []
    try:
        return [p for p in install_location.iterdir() if p.is_file() and p.suffix.lower() == ".exe"]
    except (PermissionError, OSError):
        return []


def evidence_from_prefetch(install_location: Path | None) -> ActivityEvidence:
    if sys.platform != "win32":
        return ActivityEvidence(source="prefetch", confidence=ActivityConfidence.UNAVAILABLE)

    executables = _find_candidate_executables(install_location)
    if not executables:
        return ActivityEvidence(
            source="prefetch",
            confidence=ActivityConfidence.UNAVAILABLE,
            explanation="No reliable activity evidence available (installed executable could not be identified).",
        )

    try:
        prefetch_files = list(_PREFETCH_DIR.iterdir())
    except PermissionError:
        return ActivityEvidence(
            source="prefetch",
            confidence=ActivityConfidence.UNAVAILABLE,
            explanation="No reliable activity evidence available (Prefetch data requires elevated access on this system).",
        )
    except OSError:
        return ActivityEvidence(
            source="prefetch",
            confidence=ActivityConfidence.UNAVAILABLE,
            explanation="No reliable activity evidence available (Prefetch folder is unavailable).",
        )

    best_mtime: float | None = None
    for exe in executables:
        exe_stub = exe.stem.upper()
        for pf in prefetch_files:
            if pf.suffix.lower() != ".pf":
                continue
            if pf.name.upper().startswith(f"{exe_stub}-"):
                try:
                    mtime = pf.stat().st_mtime
                except OSError:
                    continue
                if best_mtime is None or mtime > best_mtime:
                    best_mtime = mtime

    if best_mtime is None:
        return ActivityEvidence(
            source="prefetch",
            confidence=ActivityConfidence.UNAVAILABLE,
            explanation="No reliable activity evidence available (no matching Prefetch entry was found).",
        )

    return ActivityEvidence(
        source="prefetch",
        detected_date=datetime.fromtimestamp(best_mtime),
        confidence=ActivityConfidence.MEDIUM,
        explanation=(
            "Medium confidence: derived from the last-modified time of a Windows Prefetch file "
            "matching this application's executable. Prefetch entries are updated on execution, "
            "but may be missing, cleared, or disabled, and this is not a guaranteed last-used date."
        ),
    )


def evidence_from_executable_mtime(install_location: Path | None) -> ActivityEvidence:
    executables = _find_candidate_executables(install_location)
    if not executables:
        return ActivityEvidence(
            source="executable_mtime",
            confidence=ActivityConfidence.UNAVAILABLE,
            explanation="No reliable activity evidence available (installation folder could not be inspected).",
        )
    latest: float | None = None
    for exe in executables:
        try:
            mtime = exe.stat().st_mtime
        except OSError:
            continue
        if latest is None or mtime > latest:
            latest = mtime
    if latest is None:
        return ActivityEvidence(
            source="executable_mtime", confidence=ActivityConfidence.UNAVAILABLE
        )

    return ActivityEvidence(
        source="executable_mtime",
        detected_date=datetime.fromtimestamp(latest),
        confidence=ActivityConfidence.LOW,
        explanation=(
            "Low confidence: this is the file-modification time of the application's executable, "
            "which typically reflects installation or update time, not actual usage."
        ),
    )


def evidence_from_install_record(install_date: datetime | None) -> ActivityEvidence:
    if install_date is None:
        return ActivityEvidence(source="install_record", confidence=ActivityConfidence.UNAVAILABLE)
    return ActivityEvidence(
        source="install_record",
        detected_date=install_date,
        confidence=ActivityConfidence.LOW,
        explanation="Low confidence: this is the recorded installation date only, not evidence of usage.",
    )
