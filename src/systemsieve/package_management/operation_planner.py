"""Builds UninstallPlan/UpdatePlan objects from InstalledApplication records.

Planning never executes anything. It only decides *what would happen*, in the
preferred order: WinGet exact package ID > MSI product code > validated quiet
uninstall command > validated standard uninstall command. Protected
applications are always planned as unsupported.
"""

from __future__ import annotations

from systemsieve.constants import SAFETY_PROTECTED
from systemsieve.models.application import InstalledApplication
from systemsieve.models.operation import UninstallMethod, UninstallPlan, UninstallStep, UpdatePlan
from systemsieve.package_management.winget import build_uninstall_command


def plan_uninstall(app: InstalledApplication) -> UninstallPlan:
    base_kwargs = {
        "application_id": app.id,
        "application_name": app.display_name,
        "publisher": app.publisher,
        "version": app.display_version,
        "estimated_size_bytes": app.estimated_size_bytes,
        "safety_level": app.safety_level,
        "safety_reasons": list(app.safety_reasons),
    }

    if app.safety_level == SAFETY_PROTECTED:
        return UninstallPlan(
            **base_kwargs,
            method=UninstallMethod.UNSUPPORTED,
            steps=[],
            requires_admin=False,
            is_supported=False,
            unsupported_reason="This application is classified as protected and cannot be removed through SystemSieve.",
            warnings=list(app.safety_reasons),
        )

    warnings = list(app.safety_reasons) if app.safety_level == "review" else []

    if app.winget_id:
        command = build_uninstall_command(app.winget_id)
        return UninstallPlan(
            **base_kwargs,
            method=UninstallMethod.WINGET,
            steps=[
                UninstallStep(
                    description=f"Uninstall {app.display_name} via WinGet",
                    command=command,
                    requires_admin=True,
                )
            ],
            requires_admin=True,
            warnings=warnings,
        )

    if app.product_code:
        command = ["msiexec.exe", "/X", app.product_code, "/norestart"]
        return UninstallPlan(
            **base_kwargs,
            method=UninstallMethod.MSI_PRODUCT_CODE,
            steps=[
                UninstallStep(
                    description=f"Uninstall {app.display_name} via Windows Installer",
                    command=command,
                    requires_admin=True,
                )
            ],
            requires_admin=True,
            warnings=warnings,
        )

    if app.quiet_uninstall_command:
        return UninstallPlan(
            **base_kwargs,
            method=UninstallMethod.QUIET_UNINSTALL_COMMAND,
            steps=[
                UninstallStep(
                    description=f"Uninstall {app.display_name} (quiet)",
                    command=app.quiet_uninstall_command,
                    requires_admin=bool(app.requires_admin),
                )
            ],
            requires_admin=bool(app.requires_admin),
            warnings=warnings,
        )

    if app.uninstall_command:
        return UninstallPlan(
            **base_kwargs,
            method=UninstallMethod.STANDARD_UNINSTALL_COMMAND,
            steps=[
                UninstallStep(
                    description=f"Uninstall {app.display_name}",
                    command=app.uninstall_command,
                    requires_admin=bool(app.requires_admin),
                )
            ],
            requires_admin=bool(app.requires_admin),
            warnings=[
                *warnings,
                "This uninstaller may open its own window and require manual interaction.",
            ],
        )

    return UninstallPlan(
        **base_kwargs,
        method=UninstallMethod.UNSUPPORTED,
        steps=[],
        requires_admin=False,
        is_supported=False,
        unsupported_reason="No safe, validated uninstall method could be found for this application.",
        warnings=warnings,
    )


def plan_update(app: InstalledApplication) -> UpdatePlan | None:
    if not app.update_available or not app.winget_id:
        return None
    from systemsieve.package_management.winget import build_upgrade_command

    return UpdatePlan(
        application_id=app.id,
        application_name=app.display_name,
        winget_id=app.winget_id,
        current_version=app.current_version or app.display_version,
        available_version=app.available_version,
        command=build_upgrade_command(app.winget_id),
        requires_admin=True,
    )
