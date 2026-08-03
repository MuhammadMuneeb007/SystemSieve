"""Updates page: WinGet-backed update review and execution."""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QAbstractItemView,
    QCheckBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QPlainTextEdit,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from systemsieve.config import AppConfig
from systemsieve.gui.dialogs.confirmation_dialog import ConfirmationDialog
from systemsieve.gui.dialogs.error_dialog import show_error, show_warning
from systemsieve.gui.widgets.check_cell_delegate import CheckCellDelegate
from systemsieve.gui.workers import UpdateWorker
from systemsieve.models.application import InstalledApplication
from systemsieve.models.operation import OperationRecord, UpdatePlan
from systemsieve.package_management.operation_planner import plan_update

COLUMNS = ["", "Application", "Current", "Available", "Package ID", "Source"]


class UpdatesPage(QWidget):
    status_message = Signal(str)
    refresh_requested = Signal()
    operation_completed = Signal(list)

    def __init__(self, config: AppConfig, parent=None) -> None:
        super().__init__(parent)
        self._config = config
        self._outdated: list[InstalledApplication] = []
        self._worker: UpdateWorker | None = None

        layout = QVBoxLayout(self)

        title = QLabel("Updates")
        title.setObjectName("PageTitle")
        subtitle = QLabel("Review confirmed WinGet updates. Dry run remains enabled by default.")
        subtitle.setObjectName("PageSubtitle")
        layout.addWidget(title)
        layout.addWidget(subtitle)

        self.table = QTableWidget(0, len(COLUMNS))
        self.table.setHorizontalHeaderLabels(COLUMNS)
        self.table.setItemDelegateForColumn(0, CheckCellDelegate(self.table))
        self.table.setColumnWidth(0, 54)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.table.setAlternatingRowColors(True)
        self.table.setSortingEnabled(True)
        self.table.verticalHeader().setVisible(False)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        layout.addWidget(self.table)

        action_row = QHBoxLayout()
        self.dry_run_checkbox = QCheckBox("Dry run (preview only)")
        self.dry_run_checkbox.setChecked(config.dry_run_default)
        update_selected_btn = QPushButton("Update Selected")
        update_selected_btn.clicked.connect(self._update_selected)
        update_all_btn = QPushButton("Update All Eligible")
        update_all_btn.clicked.connect(self._update_all)
        refresh_btn = QPushButton("Refresh")
        refresh_btn.clicked.connect(self.refresh_requested)
        action_row.addWidget(self.dry_run_checkbox)
        action_row.addStretch()
        action_row.addWidget(update_selected_btn)
        action_row.addWidget(update_all_btn)
        action_row.addWidget(refresh_btn)
        layout.addLayout(action_row)

        self.output = QPlainTextEdit()
        self.output.setReadOnly(True)
        self.output.setMaximumHeight(150)
        layout.addWidget(self.output)

    def set_applications(self, applications: list[InstalledApplication]) -> None:
        self._outdated = [a for a in applications if a.update_available and a.winget_id]
        self.table.setSortingEnabled(False)
        self.table.setRowCount(len(self._outdated))
        for row, app_record in enumerate(self._outdated):
            check_item = QTableWidgetItem()
            check_item.setFlags(Qt.ItemIsUserCheckable | Qt.ItemIsEnabled)
            check_item.setCheckState(Qt.Unchecked)
            check_item.setData(Qt.UserRole, app_record.id)
            self.table.setItem(row, 0, check_item)
            name_item = QTableWidgetItem(app_record.display_name)
            name_item.setData(Qt.UserRole, app_record.id)
            name_item.setForeground(QColor("#2563eb"))
            self.table.setItem(row, 1, name_item)
            self.table.setItem(
                row,
                2,
                QTableWidgetItem(app_record.current_version or app_record.display_version or "-"),
            )
            self.table.setItem(row, 3, QTableWidgetItem(app_record.available_version or "-"))
            self.table.setItem(row, 4, QTableWidgetItem(app_record.winget_id or "-"))
            self.table.setItem(row, 5, QTableWidgetItem(app_record.update_source or "-"))
        self.table.setSortingEnabled(True)
        self.table.sortItems(1, Qt.AscendingOrder)

    def set_config(self, config: AppConfig) -> None:
        self._config = config
        self.dry_run_checkbox.setChecked(config.dry_run_default)

    def _checked_applications(self) -> list[InstalledApplication]:
        selected_ids: set[str] = set()
        for row in range(self.table.rowCount()):
            item = self.table.item(row, 0)
            check_state = self.table.model().index(row, 0).data(Qt.CheckStateRole)
            if item and check_state == Qt.Checked:
                selected_ids.add(str(item.data(Qt.UserRole)))
        if not selected_ids:
            selected_ids = {
                str(self.table.item(index.row(), 1).data(Qt.UserRole))
                for index in self.table.selectionModel().selectedRows()
                if self.table.item(index.row(), 1)
            }
        return [app for app in self._outdated if app.id in selected_ids]

    def _update_selected(self) -> None:
        apps = self._checked_applications()
        if not apps:
            show_warning(self, "No selection", "Check one or more applications to update.")
            return
        self._run_updates(apps)

    def _update_all(self) -> None:
        if not self._outdated:
            show_warning(self, "Nothing to update", "No eligible updates were found.")
            return
        self._run_updates(self._outdated)

    def _run_updates(self, applications: list[InstalledApplication]) -> None:
        plans: list[UpdatePlan] = []
        for a in applications:
            plan = plan_update(a)
            if plan is not None:
                plans.append(plan)
        if not plans:
            show_warning(
                self,
                "No confident update mapping",
                "No selected application has a confident WinGet update mapping.",
            )
            return

        dry_run = self.dry_run_checkbox.isChecked()
        mode = "preview (dry run)" if dry_run else "REAL update"
        names = "\n".join(
            f"- {p.application_name}: {p.current_version} -> {p.available_version}" for p in plans
        )
        if not ConfirmationDialog.confirm(
            self,
            "Confirm Update",
            f"This will perform a {mode} for:\n{names}",
            require_checkbox_text=None
            if dry_run
            else "I understand this will change installed software.",
        ):
            return

        self.output.clear()
        self._worker = UpdateWorker(
            plans, dry_run=dry_run, continue_on_failure=self._config.continue_bulk_on_failure
        )
        self._worker.progress.connect(
            lambda i, total, name: self.status_message.emit(f"Updating {i}/{total}: {name}")
        )
        self._worker.finished_ok.connect(self._on_finished)
        self._worker.failed.connect(lambda err: show_error(self, "Update failed", err))
        self._worker.start()

    def _on_finished(self, records: list[OperationRecord]) -> None:
        for record in records:
            self.output.appendPlainText(
                f"{record.target_name}: {record.status.value} — {record.details or ''}"
            )
        self.status_message.emit(f"Update run finished: {len(records)} operation(s) recorded.")
        self.operation_completed.emit(records)
        self.refresh_requested.emit()
