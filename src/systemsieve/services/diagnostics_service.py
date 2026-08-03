"""Builds a troubleshooting export ZIP for bug reports.

Deliberately excludes the full software inventory and personal file paths
unless the caller passes include_inventory=True (an explicit, opt-in choice
made by the user in the GUI/CLI, never a default).
"""

from __future__ import annotations

import json
import platform
import re
import zipfile
from datetime import datetime
from pathlib import Path

from systemsieve import __version__
from systemsieve.config import load_config
from systemsieve.paths import log_dir

_PATH_REDACT_RE = re.compile(r"([A-Za-z]:\\Users\\)([^\\]+)(\\)")


def _redact_line(line: str) -> str:
    return _PATH_REDACT_RE.sub(r"\1<redacted-user>\3", line)


def _sanitized_log_contents(max_lines_per_file: int = 2000) -> dict[str, str]:
    contents: dict[str, str] = {}
    for log_file in sorted(log_dir().glob("*.log")):
        try:
            lines = log_file.read_text(encoding="utf-8", errors="replace").splitlines()[
                -max_lines_per_file:
            ]
        except OSError:
            continue
        contents[log_file.name] = "\n".join(_redact_line(line) for line in lines)
    return contents


def _recent_error_summary(sanitized_logs: dict[str, str], max_errors: int = 50) -> list[str]:
    errors: list[str] = []
    for name, content in sanitized_logs.items():
        for line in content.splitlines():
            if " ERROR " in line or " CRITICAL " in line:
                errors.append(f"[{name}] {line}")
    return errors[-max_errors:]


def build_troubleshooting_export(output_path: Path, *, include_inventory: bool = False) -> Path:
    sanitized_logs = _sanitized_log_contents()
    cfg = load_config()

    manifest = {
        "application": "SystemSieve",
        "version": __version__,
        "generated_at": datetime.now().isoformat(),
        "os": {
            "system": platform.system(),
            "release": platform.release(),
            "version": platform.version(),
            "machine": platform.machine(),
        },
        "configuration": cfg.to_dict(),
        "recent_errors": _recent_error_summary(sanitized_logs),
        "includes_inventory": include_inventory,
    }

    with zipfile.ZipFile(output_path, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("manifest.json", json.dumps(manifest, indent=2))
        for name, content in sanitized_logs.items():
            zf.writestr(f"logs/{name}", content)

        if include_inventory:
            zf.writestr("inventory.json", _latest_inventory_json())

    return output_path


def _latest_inventory_json() -> str:
    from systemsieve.database.connection import get_connection
    from systemsieve.database.repositories import InventorySnapshotRepository

    conn = get_connection()
    try:
        apps = InventorySnapshotRepository(conn).get_latest() or []
    finally:
        conn.close()
    return json.dumps([app.model_dump(mode="json") for app in apps], indent=2)
