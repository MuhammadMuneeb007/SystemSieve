"""Windows System Restore point support.

Creating a restore point requires administrator privileges, so
create_restore_point is only ever invoked from within the elevated helper
process (see systemsieve.elevation.helper). Status checks are read-only and
can run unelevated, but System Protection status cannot always be determined
reliably -- when unknown, callers must say so rather than guessing.
"""

from __future__ import annotations

import re
from datetime import datetime

from pydantic import BaseModel

from systemsieve.logging_config import get_logger
from systemsieve.package_management.command_runner import CommandRunner, SubprocessCommandRunner

logger = get_logger("app")

RESTORE_POINT_DISCLAIMER = (
    "A restore point does not guarantee recovery of every removed application or file, "
    "and some applications cannot be fully restored by System Restore alone."
)

_SAFE_DESCRIPTION_RE = re.compile(r"[^A-Za-z0-9 :._\-]")


class RestorePointResult(BaseModel):
    attempted: bool
    success: bool
    description: str
    message: str
    created_at: datetime | None = None


def sanitize_description(description: str) -> str:
    return _SAFE_DESCRIPTION_RE.sub("", description)[:120]


def build_default_description(prefix: str = "SystemSieve before uninstall") -> str:
    timestamp = datetime.now().strftime("%Y-%m-%d %H-%M")
    return f"{prefix} - {timestamp}"


def check_system_protection_status(
    runner: CommandRunner | None = None,
) -> tuple[bool | None, str]:
    """Best-effort check. Returns (enabled_or_none, explanation).

    None means "could not be determined" -- callers must present this
    honestly rather than assuming either state.
    """
    runner = runner or SubprocessCommandRunner()
    result = runner.run(
        [
            "powershell.exe",
            "-NoProfile",
            "-NonInteractive",
            "-Command",
            "(Get-CimInstance -Namespace root/default -ClassName SystemRestoreConfig "
            "-ErrorAction Stop | Select-Object -First 1).RPSessionInterval -ne 0",
        ],
        timeout=20,
    )
    output = result.stdout.strip().lower()
    if result.exit_code == 0 and output in ("true", "false"):
        return output == "true", "Determined via SystemRestoreConfig WMI class."
    return None, "System Protection status could not be determined on this system."


def create_restore_point(
    description: str, runner: CommandRunner | None = None
) -> RestorePointResult:
    """Attempts to create a restore point. Requires administrator privileges.

    Must only be called from the elevated helper process.
    """
    runner = runner or SubprocessCommandRunner()
    safe_description = sanitize_description(description)

    script = (
        f"Checkpoint-Computer -Description '{safe_description}' "
        "-RestorePointType 'MODIFY_SETTINGS'; exit $LASTEXITCODE"
    )
    result = runner.run(
        ["powershell.exe", "-NoProfile", "-NonInteractive", "-Command", script],
        timeout=180,
    )

    if result.exit_code == 0:
        return RestorePointResult(
            attempted=True,
            success=True,
            description=safe_description,
            message="Restore point created successfully.",
            created_at=datetime.now(),
        )

    logger.warning(
        "Restore point creation failed: exit=%d stderr=%s", result.exit_code, result.stderr[:500]
    )
    return RestorePointResult(
        attempted=True,
        success=False,
        description=safe_description,
        message=(
            "Restore point creation failed. This can happen if System Protection is disabled, "
            "if a restore point was already created recently (Windows limits frequency), or due "
            f"to a system error. Details: {result.stderr.strip()[:300] or 'no additional details'}"
        ),
    )
