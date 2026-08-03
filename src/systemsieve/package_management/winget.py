"""WinGet CLI integration: detection, list, and upgrade discovery.

WinGet's stable-channel text output is a fixed-width table rather than
reliable structured JSON across all installed versions, so we parse it
defensively by locating header column offsets. If parsing fails we return an
empty result rather than guessing.
"""

from __future__ import annotations

import shutil
from dataclasses import dataclass

from systemsieve.logging_config import get_logger
from systemsieve.package_management.command_runner import CommandRunner, SubprocessCommandRunner

logger = get_logger("inventory")

WINGET_UPGRADE_ARGS_SUFFIX = ["--accept-source-agreements", "--accept-package-agreements"]


@dataclass
class WinGetPackage:
    name: str
    id: str
    version: str
    available_version: str | None
    source: str | None


def is_winget_available(runner: CommandRunner | None = None) -> bool:
    if shutil.which("winget") is None:
        return False
    runner = runner or SubprocessCommandRunner()
    result = runner.run(["winget.exe", "--version"], timeout=10)
    return result.exit_code == 0


def _parse_table(output: str, columns: list[str]) -> list[dict[str, str]]:
    lines = [line for line in output.splitlines() if line.strip()]
    header_index = None
    for i, line in enumerate(lines):
        if all(col.lower() in line.lower() for col in columns[:2]):
            header_index = i
            break
    if header_index is None:
        return []

    header_line = lines[header_index]
    offsets: list[tuple[str, int]] = []
    for col in columns:
        pos = header_line.lower().find(col.lower())
        if pos == -1:
            continue
        offsets.append((col, pos))
    if not offsets:
        return []
    offsets.sort(key=lambda x: x[1])

    separator_index = header_index + 1
    data_start = (
        separator_index + 1
        if separator_index < len(lines) and set(lines[separator_index].strip()) <= {"-"}
        else header_index + 1
    )

    rows: list[dict[str, str]] = []
    for line in lines[data_start:]:
        if set(line.strip()) <= {"-"}:
            continue
        row: dict[str, str] = {}
        for idx, (col, start) in enumerate(offsets):
            end = offsets[idx + 1][1] if idx + 1 < len(offsets) else len(line)
            row[col] = line[start:end].strip()
        if row.get(columns[0]):
            rows.append(row)
    return rows


def list_installed_packages(runner: CommandRunner | None = None) -> list[WinGetPackage]:
    runner = runner or SubprocessCommandRunner()
    result = runner.run(
        ["winget.exe", "list", "--accept-source-agreements"],
        timeout=60,
    )
    if result.exit_code != 0:
        logger.warning(
            "winget list failed with exit code %d: %s", result.exit_code, result.stderr[:500]
        )
        return []

    rows = _parse_table(result.stdout, ["Name", "Id", "Version", "Available", "Source"])
    packages: list[WinGetPackage] = []
    for row in rows:
        pkg_id = row.get("Id", "").strip()
        if not pkg_id:
            continue
        packages.append(
            WinGetPackage(
                name=row.get("Name", "").strip(),
                id=pkg_id,
                version=row.get("Version", "").strip(),
                available_version=(row.get("Available", "").strip() or None),
                source=(row.get("Source", "").strip() or None),
            )
        )
    return packages


def list_available_upgrades(runner: CommandRunner | None = None) -> list[WinGetPackage]:
    runner = runner or SubprocessCommandRunner()
    result = runner.run(
        ["winget.exe", "upgrade", "--accept-source-agreements"],
        timeout=60,
    )
    if result.exit_code != 0:
        logger.warning(
            "winget upgrade (list) failed with exit code %d: %s",
            result.exit_code,
            result.stderr[:500],
        )
        return []

    rows = _parse_table(result.stdout, ["Name", "Id", "Version", "Available", "Source"])
    packages: list[WinGetPackage] = []
    for row in rows:
        pkg_id = row.get("Id", "").strip()
        if not pkg_id:
            continue
        packages.append(
            WinGetPackage(
                name=row.get("Name", "").strip(),
                id=pkg_id,
                version=row.get("Version", "").strip(),
                available_version=(row.get("Available", "").strip() or None),
                source=(row.get("Source", "").strip() or None),
            )
        )
    return packages


def build_upgrade_command(package_id: str) -> list[str]:
    return ["winget.exe", "upgrade", "--id", package_id, "--exact", *WINGET_UPGRADE_ARGS_SUFFIX]


def build_uninstall_command(package_id: str) -> list[str]:
    return [
        "winget.exe",
        "uninstall",
        "--id",
        package_id,
        "--exact",
        "--accept-source-agreements",
    ]
