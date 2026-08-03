"""The safety-critical preview/confirmation dialog shown before any uninstall.

Always shows: application name, publisher, version, estimated size, uninstall
method, the exact command that will run, and whether administrator access is
required. When not in dry-run mode, the user must explicitly tick a checkbox
acknowledging the action may not be fully reversible before OK is enabled.
"""

from __future__ import annotations

from PySide6.QtWidgets import (
    QCheckBox,
    QDialog,
    QDialogButtonBox,
    QLabel,
    QListWidget,
    QVBoxLayout,
)

from systemsieve.inventory.size_parser import format_bytes
from systemsieve.models.operation import UninstallPlan
from systemsieve.restore.restore_point import RESTORE_POINT_DISCLAIMER


class OperationPreviewDialog(QDialog):
    def __init__(
        self,
        plans: list[UninstallPlan],
        *,
        dry_run: bool,
        restore_point_requested: bool,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self._plans = plans
        self.setWindowTitle("Confirm Uninstall")
        self.setMinimumWidth(560)

        layout = QVBoxLayout(self)

        mode_label = QLabel(
            "<b>DRY RUN — no changes will be made.</b>"
            if dry_run
            else "<b style='color:#b91c1c'>REAL REMOVAL — this will make changes.</b>"
        )
        layout.addWidget(mode_label)

        if len(plans) == 1:
            plan = plans[0]
            layout.addWidget(QLabel(f"Application: {plan.application_name}"))
            layout.addWidget(QLabel(f"Publisher: {plan.publisher or 'Unknown'}"))
            layout.addWidget(QLabel(f"Version: {plan.version or 'Unknown'}"))
            layout.addWidget(
                QLabel(
                    f"Estimated size: {format_bytes(plan.estimated_size_bytes) if plan.estimated_size_bytes else 'Unknown'}"
                )
            )
            layout.addWidget(QLabel(f"Uninstall method: {plan.method.value}"))
            command_label = QLabel(f"Command: {plan.display_command()}")
            command_label.setWordWrap(True)
            layout.addWidget(command_label)
            layout.addWidget(
                QLabel(
                    f"Administrator access: {'Required' if plan.requires_admin else 'Not required'}"
                )
            )
            for warning in plan.warnings:
                warning_label = QLabel(f"⚠ {warning}")
                warning_label.setWordWrap(True)
                layout.addWidget(warning_label)
        else:
            layout.addWidget(
                QLabel(f"{len(plans)} applications selected. They will be processed one at a time:")
            )
            listbox = QListWidget()
            for plan in plans:
                admin = "admin required" if plan.requires_admin else "no admin"
                listbox.addItem(f"{plan.application_name} — {plan.method.value} ({admin})")
            layout.addWidget(listbox)

        if restore_point_requested:
            rp_label = QLabel(
                f"A system restore point will be requested first. {RESTORE_POINT_DISCLAIMER}"
            )
            rp_label.setWordWrap(True)
            layout.addWidget(rp_label)

        disclaimer = QLabel(
            "Uninstalling software cannot always be fully reversed. Some applications leave behind "
            "files, settings, or registry entries after removal."
        )
        disclaimer.setWordWrap(True)
        layout.addWidget(disclaimer)

        self._checkbox: QCheckBox | None = None
        if not dry_run:
            self._checkbox = QCheckBox("I understand this action may not be fully reversible.")
            layout.addWidget(self._checkbox)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        ok_text = "Preview Only" if dry_run else "Uninstall Now"
        buttons.button(QDialogButtonBox.Ok).setText(ok_text)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        self._ok_button = buttons.button(QDialogButtonBox.Ok)
        if self._checkbox is not None:
            self._ok_button.setEnabled(False)
            self._checkbox.toggled.connect(self._ok_button.setEnabled)

    @staticmethod
    def confirm(
        parent, plans: list[UninstallPlan], *, dry_run: bool, restore_point_requested: bool
    ) -> bool:
        dialog = OperationPreviewDialog(
            plans, dry_run=dry_run, restore_point_requested=restore_point_requested, parent=parent
        )
        return dialog.exec() == QDialog.Accepted
