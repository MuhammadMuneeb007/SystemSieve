"""Scans the Windows uninstall registry keys and produces InstalledApplication records.

Read-only. Never writes to the registry. Uses winreg (Windows stdlib) directly;
on non-Windows platforms this module raises RuntimeError on use so the rest of
the codebase can still be imported/tested cross-platform.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

from systemsieve.constants import SAFETY_UNKNOWN, UNINSTALL_KEY_PATHS
from systemsieve.inventory.size_parser import parse_estimated_size_kb, parse_install_date
from systemsieve.logging_config import get_logger
from systemsieve.models.application import InstalledApplication
from systemsieve.package_management.command_validator import (
    CommandValidationResult,
    validate_command,
)

logger = get_logger("inventory")

_GUID_SUBKEY_RE = re.compile(
    r"^\{[0-9A-Fa-f]{8}-[0-9A-Fa-f]{4}-[0-9A-Fa-f]{4}-[0-9A-Fa-f]{4}-[0-9A-Fa-f]{12}\}$"
)

_HIVE_MAP: dict[str, int] | None = None


def _hive_map() -> dict[str, int]:
    global _HIVE_MAP
    if _HIVE_MAP is None:
        import winreg

        _HIVE_MAP = {
            "HKEY_LOCAL_MACHINE": winreg.HKEY_LOCAL_MACHINE,
            "HKEY_CURRENT_USER": winreg.HKEY_CURRENT_USER,
        }
    return _HIVE_MAP


def _read_value(key, name: str):
    import winreg

    try:
        value, _type = winreg.QueryValueEx(key, name)
        return value
    except FileNotFoundError:
        return None
    except OSError:
        return None


def _requires_admin_heuristic(hive_name: str, install_location: Path | None) -> bool:
    if hive_name == "HKEY_CURRENT_USER":
        return False
    if install_location:
        loc = str(install_location).lower()
        if "\\appdata\\local\\" in loc or "\\appdata\\roaming\\" in loc:
            return False
    return True


def _build_application(
    hive_name: str, key_path: str, subkey_name: str, key
) -> InstalledApplication | None:
    display_name = _read_value(key, "DisplayName")
    if not display_name or not str(display_name).strip():
        return None

    display_version = _read_value(key, "DisplayVersion")
    publisher = _read_value(key, "Publisher")
    install_date_raw = _read_value(key, "InstallDate")
    estimated_size_raw = _read_value(key, "EstimatedSize")
    install_location_raw = _read_value(key, "InstallLocation")
    display_icon = _read_value(key, "DisplayIcon")
    uninstall_string = _read_value(key, "UninstallString")
    quiet_uninstall_string = _read_value(key, "QuietUninstallString")
    modify_path = _read_value(key, "ModifyPath")
    system_component_raw = _read_value(key, "SystemComponent")
    no_modify = _read_value(key, "NoModify")

    install_location = Path(install_location_raw) if install_location_raw else None
    system_component = bool(system_component_raw) if system_component_raw is not None else False

    product_code = subkey_name if _GUID_SUBKEY_RE.match(subkey_name) else None

    uninstall_validated = validate_command(uninstall_string, context="uninstall")
    quiet_validated = validate_command(quiet_uninstall_string, context="quiet_uninstall")
    modify_validated = validate_command(modify_path, context="modify") if modify_path else None

    uninstall_confidence = "unknown"
    if quiet_validated.result == CommandValidationResult.VALID:
        uninstall_confidence = "high"
    elif uninstall_validated.result == CommandValidationResult.VALID or product_code:
        uninstall_confidence = "medium"
    else:
        uninstall_confidence = "low"

    app_id = f"{hive_name}\\{key_path}\\{subkey_name}"

    app = InstalledApplication(
        id=app_id,
        display_name=str(display_name).strip(),
        display_version=str(display_version) if display_version else None,
        publisher=str(publisher) if publisher else None,
        install_date=parse_install_date(str(install_date_raw)) if install_date_raw else None,
        estimated_size_bytes=parse_estimated_size_kb(estimated_size_raw),
        install_location=install_location,
        display_icon=str(display_icon) if display_icon else None,
        registry_path=f"{key_path}\\{subkey_name}",
        registry_hive=hive_name,
        source="registry",
        uninstall_command=uninstall_validated.argv
        if uninstall_validated.result == CommandValidationResult.VALID
        else None,
        quiet_uninstall_command=quiet_validated.argv
        if quiet_validated.result == CommandValidationResult.VALID
        else None,
        modify_command=modify_validated.argv
        if modify_validated and modify_validated.result == CommandValidationResult.VALID
        else None,
        raw_uninstall_string=str(uninstall_string) if uninstall_string else None,
        raw_quiet_uninstall_string=str(quiet_uninstall_string) if quiet_uninstall_string else None,
        product_code=product_code
        or uninstall_validated.product_code
        or quiet_validated.product_code,
        system_component=system_component,
        requires_admin=_requires_admin_heuristic(hive_name, install_location),
        uninstall_confidence=uninstall_confidence,
        safety_level=SAFETY_UNKNOWN,
    )

    if no_modify:
        pass  # informational only; not currently surfaced separately

    return app


def scan_uninstall_registry() -> list[InstalledApplication]:
    """Enumerates all configured uninstall registry locations. Read-only."""
    if sys.platform != "win32":
        raise RuntimeError("Registry scanning is only supported on Windows.")

    import winreg

    apps: list[InstalledApplication] = []
    hives = _hive_map()

    for hive_name, key_path in UNINSTALL_KEY_PATHS:
        hive = hives.get(hive_name)
        if hive is None:
            continue
        try:
            root_key = winreg.OpenKey(hive, key_path, 0, winreg.KEY_READ)
        except OSError as exc:
            logger.debug("Could not open %s\\%s: %s", hive_name, key_path, exc)
            continue

        with root_key:
            index = 0
            while True:
                try:
                    subkey_name = winreg.EnumKey(root_key, index)
                except OSError:
                    break
                index += 1
                try:
                    with winreg.OpenKey(root_key, subkey_name, 0, winreg.KEY_READ) as subkey:
                        app = _build_application(hive_name, key_path, subkey_name, subkey)
                        if app is not None:
                            apps.append(app)
                except OSError as exc:
                    logger.debug("Failed to read subkey %s\\%s: %s", key_path, subkey_name, exc)
                    continue

    logger.info("Registry scan found %d application entries", len(apps))
    return apps
