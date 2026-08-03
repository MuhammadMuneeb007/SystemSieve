"""Applications page: search, filter, select, inspect, update, uninstall, export."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QAction
from PySide6.QtWidgets import (
    QAbstractItemView,
    QCheckBox,
    QFileDialog,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QMenu,
    QMessageBox,
    QPushButton,
    QTableView,
    QVBoxLayout,
    QWidget,
)

from systemsieve.config import AppConfig
from systemsieve.gui.dialogs.error_dialog import show_error, show_warning
from systemsieve.gui.dialogs.operation_preview_dialog import OperationPreviewDialog
from systemsieve.gui.dialogs.uninstall_progress_dialog import UninstallProgressDialog
from systemsieve.gui.models.applications_model import (
    ApplicationsFilterProxyModel,
    ApplicationsTableModel,
)
from systemsieve.gui.shell_actions import existing_location, open_path, reveal_in_explorer
from systemsieve.gui.widgets.check_cell_delegate import CheckCellDelegate
from systemsieve.gui.widgets.filter_bar import FilterBar
from systemsieve.gui.workers import RestorePointWorker, UninstallWorker
from systemsieve.inventory.size_parser import format_bytes
from systemsieve.models.application import InstalledApplication
from systemsieve.models.operation import OperationRecord, UninstallPlan
from systemsieve.package_management.operation_planner import plan_uninstall
from systemsieve.restore.restore_point import build_default_description

FILTERS = [
    ("all", "All applications"),
    ("updates_available", "Updates available"),
    ("large", "Large applications"),
    ("recently_installed", "Recently installed"),
    ("possibly_unused", "Possibly unused"),
    ("winget_managed", "WinGet-managed"),
    ("registry_only", "Registry-only"),
    ("user_applications", "User applications"),
    ("system_components", "System components"),
    ("safe_to_review", "Safe to review"),
    ("protected", "Protected"),
    ("unknown_size", "Unknown size"),
]


class ApplicationsPage(QWidget):
    status_message = Signal(str)
    refresh_requested = Signal()
    operation_completed = Signal(list)  # list[OperationRecord]

    def __init__(self, config: AppConfig, parent=None) -> None:
        super().__init__(parent)
        self._config = config
        self._applications: list[InstalledApplication] = []
        self._uninstall_worker: UninstallWorker | None = None
        self._restore_worker: RestorePointWorker | None = None
        self._progress_dialog: UninstallProgressDialog | None = None
        self._uninstall_cancel_requested = False

        layout = QVBoxLayout(self)

        title = QLabel("Applications")
        title.setObjectName("PageTitle")
        subtitle = QLabel(
            "Review installed software by safety, activity, size, source, or update status."
        )
        subtitle.setObjectName("PageSubtitle")
        layout.addWidget(title)
        layout.addWidget(subtitle)

        self.filter_bar = FilterBar(FILTERS)
        self.filter_bar.search_changed.connect(self._on_search_changed)
        self.filter_bar.filter_changed.connect(self._on_filter_changed)
        self.filter_bar.refresh_requested.connect(self.refresh_requested)
        layout.addWidget(self.filter_bar)

        self._model = ApplicationsTableModel()
        self._proxy = ApplicationsFilterProxyModel()
        self._proxy.setSourceModel(self._model)

        self.table = QTableView()
        self.table.setModel(self._proxy)
        self.table.setItemDelegateForColumn(0, CheckCellDelegate(self.table))
        self.table.setSortingEnabled(True)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.table.setAlternatingRowColors(True)
        self.table.setContextMenuPolicy(Qt.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self._show_context_menu)
        self.table.doubleClicked.connect(lambda _index: self._inspect_selected())
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.table.verticalHeader().setVisible(False)
        self.table.setColumnWidth(0, 54)
        self.table.sortByColumn(1, Qt.AscendingOrder)
        layout.addWidget(self.table)

        selection_row = QHBoxLayout()
        self.selection_label = QLabel("0 selected (0 B)")
        select_all_btn = QPushButton("Select All Visible")
        select_all_btn.clicked.connect(self._select_all_visible)
        clear_btn = QPushButton("Clear Selection")
        clear_btn.clicked.connect(self._model.clear_selection)
        invert_btn = QPushButton("Invert Selection")
        invert_btn.clicked.connect(self._model.invert_selection)
        selection_row.addWidget(self.selection_label)
        selection_row.addStretch()
        selection_row.addWidget(select_all_btn)
        selection_row.addWidget(clear_btn)
        selection_row.addWidget(invert_btn)
        layout.addLayout(selection_row)

        self._model.dataChanged.connect(self._update_selection_label)
        self._model.modelReset.connect(self._update_selection_label)
        self.table.selectionModel().selectionChanged.connect(self._update_selection_label)

        action_row = QHBoxLayout()
        self.dry_run_checkbox = QCheckBox("Preview only — no software will be removed")
        self.dry_run_checkbox.setChecked(config.dry_run_default)
        self.restore_point_checkbox = QCheckBox("Create restore point before uninstalling")
        self.restore_point_checkbox.setChecked(config.create_restore_point_default)

        inspect_btn = QPushButton("Inspect")
        inspect_btn.clicked.connect(self._inspect_selected)
        update_btn = QPushButton("Update Selected")
        update_btn.clicked.connect(self._update_selected)
        location_btn = QPushButton("Open Location")
        location_btn.clicked.connect(self._open_selected_locations)
        self.uninstall_btn = QPushButton()
        self.uninstall_btn.clicked.connect(self._uninstall_selected)
        self.dry_run_checkbox.toggled.connect(self._update_uninstall_mode)
        export_btn = QPushButton("Export")
        export_btn.clicked.connect(self._export)

        action_row.addWidget(self.dry_run_checkbox)
        action_row.addWidget(self.restore_point_checkbox)
        action_row.addStretch()
        action_row.addWidget(inspect_btn)
        action_row.addWidget(location_btn)
        action_row.addWidget(update_btn)
        action_row.addWidget(self.uninstall_btn)
        action_row.addWidget(export_btn)
        layout.addLayout(action_row)
        self._update_uninstall_mode(self.dry_run_checkbox.isChecked())

    # --- data -----------------------------------------------------------------

    def set_applications(self, applications: list[InstalledApplication]) -> None:
        self._applications = applications
        visible = [
            a for a in applications if self._config.show_system_components or not a.system_component
        ]
        self._model.set_applications(visible)
        self._update_selection_label()

    def set_config(self, config: AppConfig) -> None:
        self._config = config
        self.dry_run_checkbox.setChecked(config.dry_run_default)
        self.restore_point_checkbox.setChecked(config.create_restore_point_default)

    def _update_uninstall_mode(self, preview_only: bool) -> None:
        self.uninstall_btn.setText("Preview Uninstall" if preview_only else "Uninstall Selected")
        self.uninstall_btn.setObjectName("PreviewButton" if preview_only else "DangerButton")
        self.uninstall_btn.style().unpolish(self.uninstall_btn)
        self.uninstall_btn.style().polish(self.uninstall_btn)
        self.restore_point_checkbox.setEnabled(not preview_only)
        mode_help = (
            "No commands will be executed. Uncheck Preview only to remove software."
            if preview_only
            else "REAL REMOVAL is enabled. A confirmation and progress window will be shown."
        )
        self.dry_run_checkbox.setToolTip(mode_help)
        self.uninstall_btn.setToolTip(mode_help)

    def _on_search_changed(self, text: str) -> None:
        self._proxy.set_search_text(text)

    def _on_filter_changed(self, category: str) -> None:
        self._proxy.set_category(category)

    def _select_all_visible(self) -> None:
        ids = []
        for row in range(self._proxy.rowCount()):
            source_index = self._proxy.mapToSource(self._proxy.index(row, 0))
            ids.append(self._model.application_at(source_index.row()).id)
        self._model.select_all(ids)

    def _update_selection_label(self, *_args) -> None:
        checked = self._model.checked_applications()
        highlighted = self._highlighted_applications()
        self.selection_label.setText(
            f"{len(checked)} checked ({format_bytes(self._model.selected_total_size())})"
            f"  •  {len(highlighted)} row(s) highlighted"
        )

    def _highlighted_applications(self) -> list[InstalledApplication]:
        applications: list[InstalledApplication] = []
        seen: set[str] = set()
        for index in self.table.selectionModel().selectedRows():
            source_index = self._proxy.mapToSource(index)
            app_record = self._model.application_at(source_index.row())
            if app_record.id not in seen:
                applications.append(app_record)
                seen.add(app_record.id)
        return applications

    def _action_applications(self) -> list[InstalledApplication]:
        """Checkboxes take precedence; highlighted rows remain valid selections."""
        return self._model.checked_applications() or self._highlighted_applications()

    def _selected_row_application(self) -> InstalledApplication | None:
        index = self.table.currentIndex()
        if not index.isValid():
            return None
        source_index = self._proxy.mapToSource(index)
        return self._model.application_at(source_index.row())

    # --- actions ----------------------------------------------------------------

    def _inspect_selected(self) -> None:
        selected = self._action_applications()
        app_record = selected[0] if selected else self._selected_row_application()
        if app_record is None:
            show_warning(self, "No selection", "Select an application row first.")
            return
        text = (
            f"<b>{app_record.display_name}</b><br>"
            f"Version: {app_record.display_version or 'Unknown'}<br>"
            f"Publisher: {app_record.publisher or 'Unknown'}<br>"
            f"Estimated size: {app_record.estimated_size_display}<br>"
            f"Install location: {app_record.install_location or 'Unknown'}<br>"
            f"Source: {app_record.source}<br>"
            f"WinGet ID: {app_record.winget_id or 'N/A'}<br>"
            f"Registry path: {app_record.registry_path or 'N/A'}<br>"
            f"Uninstall command: {' '.join(app_record.uninstall_command) if app_record.uninstall_command else 'None available'}<br>"
            f"Quiet uninstall command: {' '.join(app_record.quiet_uninstall_command) if app_record.quiet_uninstall_command else 'None available'}<br>"
            f"Update available: {app_record.update_available} ({app_record.available_version or 'N/A'})<br>"
            f"<b>Safety level: {app_record.safety_level}</b><br>"
            + "<br>".join(f"- {r}" for r in app_record.safety_reasons)
            + f"<br><br>Activity confidence: {app_record.activity_confidence.value}<br>"
            f"{app_record.activity_explanation}"
        )
        QMessageBox.information(self, "Application Details", text)

    def _update_selected(self) -> None:
        selected = self._action_applications()
        if not selected:
            show_warning(self, "No selection", "Select one or more applications to update.")
            return
        show_warning(
            self,
            "Use the Updates page",
            "Updating applications is handled on the Updates page, which lists confirmed WinGet mappings.",
        )

    def _uninstall_selected(self) -> None:
        selected = self._action_applications()
        if not selected:
            show_warning(self, "No selection", "Select one or more applications to uninstall.")
            return

        plans: list[UninstallPlan] = [plan_uninstall(a) for a in selected]
        unsupported = [p for p in plans if not p.is_supported]
        supported = [p for p in plans if p.is_supported]

        if unsupported:
            names = ", ".join(p.application_name for p in unsupported)
            show_warning(
                self,
                "Some applications cannot be removed",
                f"The following cannot be uninstalled through SystemSieve and will be skipped: {names}",
            )
        if not supported:
            return

        dry_run = self.dry_run_checkbox.isChecked()
        restore_point = self.restore_point_checkbox.isChecked() and not dry_run

        if not OperationPreviewDialog.confirm(
            self, supported, dry_run=dry_run, restore_point_requested=restore_point
        ):
            return

        self._progress_dialog = UninstallProgressDialog(supported, dry_run=dry_run, parent=self)
        self._uninstall_cancel_requested = False
        self._progress_dialog.cancel_requested.connect(self._request_uninstall_cancel)
        self._progress_dialog.show()

        self._begin_uninstall(supported, dry_run=dry_run, restore_point=restore_point)

    def _begin_uninstall(
        self, plans: list[UninstallPlan], *, dry_run: bool, restore_point: bool
    ) -> None:
        if restore_point:
            self.status_message.emit("Creating restore point...")
            if self._progress_dialog:
                self._progress_dialog.set_restore_point_stage()
            self._restore_worker = RestorePointWorker(build_default_description())
            self._restore_worker.finished_ok.connect(
                lambda success, message: self._on_restore_point_done(
                    success, message, plans, dry_run
                )
            )
            self._restore_worker.failed.connect(
                lambda err: self._on_restore_point_done(False, err, plans, dry_run)
            )
            self._restore_worker.start()
        else:
            self._run_uninstall_worker(plans, dry_run)

    def _on_restore_point_done(
        self, success: bool, message: str, plans: list[UninstallPlan], dry_run: bool
    ) -> None:
        if self._progress_dialog:
            self._progress_dialog.set_restore_point_result(success, message)
        if not success:
            proceed = QMessageBox.question(
                self._progress_dialog or self,
                "Restore point failed",
                f"Restore point creation failed: {message}\n\nContinue without a restore point?",
            )
            if proceed != QMessageBox.Yes:
                self.status_message.emit("Uninstall cancelled: restore point failed.")
                if self._progress_dialog:
                    self._progress_dialog.fail("Cancelled because the restore point failed.")
                return
        self._run_uninstall_worker(plans, dry_run)

    def _run_uninstall_worker(self, plans: list[UninstallPlan], dry_run: bool) -> None:
        self.status_message.emit("Uninstalling...")
        self._uninstall_worker = UninstallWorker(plans, dry_run=dry_run, continue_on_failure=False)
        self._uninstall_worker.progress.connect(self._on_uninstall_progress)
        self._uninstall_worker.item_finished.connect(self._on_uninstall_item_finished)
        self._uninstall_worker.finished_ok.connect(self._on_uninstall_finished)
        self._uninstall_worker.failed.connect(self._on_uninstall_failed)
        if self._uninstall_cancel_requested:
            self._uninstall_worker.cancel()
        self._uninstall_worker.start()

    def _request_uninstall_cancel(self) -> None:
        self._uninstall_cancel_requested = True
        if self._uninstall_worker and self._uninstall_worker.isRunning():
            self._uninstall_worker.cancel()

    def _on_uninstall_progress(self, index: int, total: int, name: str) -> None:
        mode = "Previewing" if self.dry_run_checkbox.isChecked() else "Uninstalling"
        self.status_message.emit(f"{mode} {index}/{total}: {name}")
        if self._progress_dialog:
            self._progress_dialog.operation_started(index, total, name)

    def _on_uninstall_item_finished(self, index: int, total: int, record: OperationRecord) -> None:
        if self._progress_dialog:
            self._progress_dialog.operation_finished(index, total, record)

    def _on_uninstall_failed(self, message: str) -> None:
        if self._progress_dialog:
            self._progress_dialog.fail(message)
        show_error(self._progress_dialog or self, "Uninstall failed", message)

    def _on_uninstall_finished(self, records: list[OperationRecord]) -> None:
        self.status_message.emit(f"Uninstall finished: {len(records)} operation(s) recorded.")
        if self._progress_dialog:
            self._progress_dialog.complete(records)
        self.operation_completed.emit(records)
        if not self.dry_run_checkbox.isChecked():
            self.refresh_requested.emit()

    def _export(self) -> None:
        path, selected_filter = QFileDialog.getSaveFileName(
            self, "Export Applications", "applications.csv", "CSV (*.csv);;JSON (*.json)"
        )
        if not path:
            return
        from pathlib import Path

        from systemsieve.services.export_service import (
            export_applications_csv,
            export_applications_json,
        )

        if path.lower().endswith(".json"):
            result = export_applications_json(self._applications, Path(path))
        else:
            result = export_applications_csv(self._applications, Path(path))
        self.status_message.emit(f"Exported {result.record_count} applications to {result.path}")

    def _application_location(self, app_record: InstalledApplication) -> Path | None:
        command_path = app_record.uninstall_command[0] if app_record.uninstall_command else None
        location = existing_location(app_record.install_location, command_path)
        if location and location.is_file():
            return location.parent
        return location

    def _open_selected_locations(self) -> None:
        selected = self._action_applications()
        if not selected:
            show_warning(self, "No selection", "Select one or more application rows first.")
            return
        opened = 0
        missing: list[str] = []
        for app_record in selected:
            location = self._application_location(app_record)
            if location:
                open_path(location)
                opened += 1
            else:
                missing.append(app_record.display_name)
        self.status_message.emit(f"Opened {opened} application location(s).")
        if missing:
            show_warning(
                self,
                "Location unavailable",
                "Windows did not report an existing location for:\n" + "\n".join(missing),
            )

    def _reveal_selected_executable(self) -> None:
        selected = self._action_applications()
        if not selected:
            return
        app_record = selected[0]
        command_path = app_record.uninstall_command[0] if app_record.uninstall_command else None
        target = existing_location(command_path, app_record.install_location)
        if target:
            reveal_in_explorer(target)
        else:
            show_warning(
                self, "Location unavailable", "No existing executable or folder was reported."
            )

    def _show_context_menu(self, position) -> None:
        index = self.table.indexAt(position)
        if index.isValid() and not self.table.selectionModel().isSelected(index):
            self.table.selectRow(index.row())
        menu = QMenu(self)
        inspect_action = QAction("Inspect details", self)
        inspect_action.triggered.connect(self._inspect_selected)
        menu.addAction(inspect_action)
        open_action = QAction("Open install location", self)
        open_action.triggered.connect(self._open_selected_locations)
        menu.addAction(open_action)
        reveal_action = QAction("Show executable in Explorer", self)
        reveal_action.triggered.connect(self._reveal_selected_executable)
        menu.addAction(reveal_action)
        menu.addSeparator()
        uninstall_action = QAction("Preview uninstall", self)
        uninstall_action.triggered.connect(self._uninstall_selected)
        menu.addAction(uninstall_action)
        menu.exec(self.table.viewport().mapToGlobal(position))
