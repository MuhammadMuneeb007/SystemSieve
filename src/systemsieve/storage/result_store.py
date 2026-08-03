"""Lightweight cache of the most recent scan result, for quick Dashboard lookups.

The authoritative, queryable scan history lives in the SQLite database (see
systemsieve.database and systemsieve.services.history_service); this module
only caches the single latest ScanSummary as JSON so the Dashboard can show
"Last disk scan" without re-querying the database or re-scanning.
"""

from __future__ import annotations

from systemsieve.logging_config import get_logger
from systemsieve.models.storage import ScanSummary
from systemsieve.paths import cache_dir

logger = get_logger("storage")

_LATEST_SCAN_FILENAME = "latest_scan.json"


def save_latest_scan(summary: ScanSummary) -> None:
    path = cache_dir() / _LATEST_SCAN_FILENAME
    try:
        path.write_text(summary.model_dump_json(), encoding="utf-8")
    except OSError as exc:
        logger.warning("Failed to cache latest scan result: %s", exc)


def load_latest_scan() -> ScanSummary | None:
    path = cache_dir() / _LATEST_SCAN_FILENAME
    if not path.exists():
        return None
    try:
        return ScanSummary.model_validate_json(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        logger.warning("Failed to load cached scan result: %s", exc)
        return None
