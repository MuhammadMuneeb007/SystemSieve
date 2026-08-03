"""Produces InstalledApplication stubs from WinGet's package list.

These are merged with registry-derived records by the deduplicator. WinGet-only
records (no matching registry entry) are still surfaced, since some packages
(e.g. MSIX/Store apps) may not appear in the classic uninstall registry keys.
"""

from __future__ import annotations

from systemsieve.constants import SAFETY_UNKNOWN
from systemsieve.logging_config import get_logger
from systemsieve.models.application import InstalledApplication
from systemsieve.package_management.command_runner import CommandRunner
from systemsieve.package_management.winget import build_uninstall_command, list_installed_packages

logger = get_logger("inventory")


def scan_winget_packages(runner: CommandRunner | None = None) -> list[InstalledApplication]:
    packages = list_installed_packages(runner)
    apps: list[InstalledApplication] = []
    for pkg in packages:
        if not pkg.id or not pkg.name:
            continue
        apps.append(
            InstalledApplication(
                id=f"winget:{pkg.id}",
                display_name=pkg.name,
                display_version=pkg.version or None,
                publisher=None,
                source="winget",
                winget_id=pkg.id,
                uninstall_command=build_uninstall_command(pkg.id),
                uninstall_confidence="high",
                requires_admin=True,
                safety_level=SAFETY_UNKNOWN,
            )
        )
    logger.info("WinGet scan found %d packages", len(apps))
    return apps
