"""High-level orchestration for building the installed-application inventory.

This is the single entry point used by both the CLI and the GUI. It performs
only read-only discovery: registry enumeration, optional WinGet enumeration,
deduplication, safety classification, update matching, and activity evidence
attachment. No destructive action is ever taken here.
"""

from __future__ import annotations

import sys
from dataclasses import dataclass

from systemsieve.activity.service import attach_activity_evidence
from systemsieve.inventory.deduplicator import deduplicate
from systemsieve.inventory.registry_scanner import scan_uninstall_registry
from systemsieve.inventory.safety_classifier import classify
from systemsieve.inventory.winget_scanner import scan_winget_packages
from systemsieve.logging_config import get_logger
from systemsieve.models.application import InstalledApplication
from systemsieve.package_management.command_runner import CommandRunner, SubprocessCommandRunner
from systemsieve.package_management.winget import is_winget_available, list_available_upgrades

logger = get_logger("inventory")


@dataclass
class InventoryResult:
    applications: list[InstalledApplication]
    winget_available: bool
    errors: list[str]


def build_inventory(
    runner: CommandRunner | None = None,
    *,
    include_winget: bool = True,
    include_activity: bool = True,
) -> InventoryResult:
    runner = runner or SubprocessCommandRunner()
    errors: list[str] = []

    if sys.platform != "win32":
        errors.append("Registry scanning is only supported on Windows.")
        registry_apps: list[InstalledApplication] = []
    else:
        try:
            registry_apps = scan_uninstall_registry()
        except Exception as exc:  # noqa: BLE001 - top-level scan boundary
            logger.exception("Registry scan failed")
            errors.append(f"Registry scan failed: {exc}")
            registry_apps = []

    winget_available = False
    winget_apps: list[InstalledApplication] = []
    if include_winget:
        try:
            winget_available = is_winget_available(runner)
        except Exception as exc:  # noqa: BLE001
            logger.warning("WinGet availability check failed: %s", exc)
        if winget_available:
            try:
                winget_apps = scan_winget_packages(runner)
            except Exception as exc:  # noqa: BLE001
                logger.exception("WinGet scan failed")
                errors.append(f"WinGet scan failed: {exc}")

    merged = deduplicate(registry_apps, winget_apps)

    if winget_available:
        try:
            merged = _apply_update_info(merged, runner)
        except Exception as exc:  # noqa: BLE001
            logger.warning("Update detection failed: %s", exc)
            errors.append(f"Update detection failed: {exc}")

    classified: list[InstalledApplication] = []
    for app in merged:
        level, reasons = classify(app)
        classified.append(app.model_copy(update={"safety_level": level, "safety_reasons": reasons}))

    if include_activity:
        try:
            classified = attach_activity_evidence(classified)
        except Exception as exc:  # noqa: BLE001
            logger.warning("Activity detection failed: %s", exc)
            errors.append(f"Activity detection failed: {exc}")

    logger.info(
        "Inventory build complete: %d applications, %d errors", len(classified), len(errors)
    )
    return InventoryResult(
        applications=classified, winget_available=winget_available, errors=errors
    )


def _apply_update_info(
    apps: list[InstalledApplication], runner: CommandRunner
) -> list[InstalledApplication]:
    upgrades = {pkg.id: pkg for pkg in list_available_upgrades(runner)}
    updated: list[InstalledApplication] = []
    for app in apps:
        if app.winget_id and app.winget_id in upgrades:
            pkg = upgrades[app.winget_id]
            updated.append(
                app.model_copy(
                    update={
                        "update_available": True,
                        "current_version": app.display_version,
                        "available_version": pkg.available_version,
                        "update_source": "winget",
                    }
                )
            )
        else:
            updated.append(app)
    return updated


def filter_visible(
    apps: list[InstalledApplication], *, show_system_components: bool
) -> list[InstalledApplication]:
    if show_system_components:
        return apps
    return [app for app in apps if not app.system_component]
