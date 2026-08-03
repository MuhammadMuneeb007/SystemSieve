"""Storage page: cancellable disk scanning, largest files/folders, categories, deletion."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QSortFilterProxyModel, Qt, Signal
from PySide6.QtGui import QAction
from PySide6.QtWidgets import (
    QAbstractItemView,
    QFileDialog,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QListWidget,
    QMenu,
    QProgressBar,
    QPushButton,
    QTableView,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from systemsieve.config import AppConfig
from systemsieve.gui.dialogs.confirmation_dialog import ConfirmationDialog
from systemsieve.gui.dialogs.error_dialog import show_error, show_warning
from systemsieve.gui.models.storage_model import FileItemsTableModel, FolderItemsTableModel
from systemsieve.gui.shell_actions import reveal_in_explorer
from systemsieve.gui.widgets.check_cell_delegate import CheckCellDelegate
from systemsieve.inventory.size_parser import format_bytes
from systemsieve.models.storage import ScanSummary
from systemsieve.storage.scan_worker import ScanWorker
from systemsieve.storage.scanner import ScanOptions


class StoragePage(QWidget):
    status_message = Signal(str)
    scan_completed = Signal(object)  # ScanSummary

    def __init__(self, config: AppConfig, parent=None) -> None:
        super().__init__(parent)
        self._config = config
        self._worker: ScanWorker | None = None
        self._summary: ScanSummary | None = None

        layout = QVBoxLayout(self)

        title = QLabel("Storage")
        title.setObjectName("PageTitle")
        subtitle = QLabel(
            "Scan safely, sort results, reveal items in Explorer, and recycle reviewed files."
        )
        subtitle.setObjectName("PageSubtitle")
        layout.addWidget(title)
        layout.addWidget(subtitle)

        selector_row = QHBoxLayout()
        self.path_edit = QLineEdit()
        self.path_edit.setPlaceholderText(
            "Drive or folder to scan, e.g. C:\\ or C:\\Users\\you\\Downloads"
        )
        browse_btn = QPushButton("Browse...")
        browse_btn.clicked.connect(self._browse)
        self.start_btn = QPushButton("Start Scan")
        self.start_btn.clicked.connect(self._start_scan)
        self.cancel_btn = QPushButton("Cancel Scan")
        self.cancel_btn.clicked.connect(self._cancel_scan)
        self.cancel_btn.setEnabled(False)
        selector_row.addWidget(self.path_edit, stretch=1)
        selector_row.addWidget(browse_btn)
        selector_row.addWidget(self.start_btn)
        selector_row.addWidget(self.cancel_btn)
        layout.addLayout(selector_row)

        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 0)
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)
        self.progress_label = QLabel("")
        layout.addWidget(self.progress_label)

        self.tabs = QTabWidget()
        layout.addWidget(self.tabs)

        self._files_model = FileItemsTableModel()
        self.files_table = QTableView()
        self._files_proxy = self._configure_file_table(self.files_table, self._files_model)
        self._files_model.dataChanged.connect(self._update_selection_label)
        self.tabs.addTab(self.files_table, "Largest Files")

        self._old_files_model = FileItemsTableModel()
        self.old_files_table = QTableView()
        self._old_files_proxy = self._configure_file_table(
            self.old_files_table, self._old_files_model
        )
        self.tabs.addTab(self.old_files_table, "Old Files")

        self._recent_files_model = FileItemsTableModel()
        self.recent_files_table = QTableView()
        self._recent_files_proxy = self._configure_file_table(
            self.recent_files_table, self._recent_files_model
        )
        self.tabs.addTab(self.recent_files_table, "Recently Modified")

        self._folders_model = FolderItemsTableModel()
        self.folders_table = QTableView()
        self._folders_proxy = QSortFilterProxyModel(self)
        self._folders_proxy.setSourceModel(self._folders_model)
        self._folders_proxy.setSortRole(Qt.UserRole)
        self.folders_table.setModel(self._folders_proxy)
        self._configure_common_table(self.folders_table)
        self.folders_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.folders_table.doubleClicked.connect(lambda index: self._reveal_folder_index(index))
        self.tabs.addTab(self.folders_table, "Largest Folders")

        self.categories_list = QListWidget()
        self.tabs.addTab(self.categories_list, "Categories")

        self.errors_list = QListWidget()
        self.tabs.addTab(self.errors_list, "Errors")

        bottom_row = QHBoxLayout()
        self.selection_label = QLabel("0 selected (0 B)")
        recycle_btn = QPushButton("Recycle Selected")
        recycle_btn.clicked.connect(self._recycle_selected)
        select_all_btn = QPushButton("Select All")
        select_all_btn.clicked.connect(self._select_all_current)
        clear_btn = QPushButton("Clear")
        clear_btn.clicked.connect(self._clear_current)
        reveal_btn = QPushButton("Show in Explorer")
        reveal_btn.clicked.connect(self._reveal_current)
        export_btn = QPushButton("Export Results")
        export_btn.clicked.connect(self._export)
        bottom_row.addWidget(self.selection_label)
        bottom_row.addStretch()
        bottom_row.addWidget(select_all_btn)
        bottom_row.addWidget(clear_btn)
        bottom_row.addWidget(reveal_btn)
        bottom_row.addWidget(recycle_btn)
        bottom_row.addWidget(export_btn)
        layout.addLayout(bottom_row)

    def _configure_common_table(self, table: QTableView) -> None:
        table.setSortingEnabled(True)
        table.setSelectionBehavior(QAbstractItemView.SelectRows)
        table.setSelectionMode(QAbstractItemView.ExtendedSelection)
        table.setAlternatingRowColors(True)
        table.verticalHeader().setVisible(False)

    def _configure_file_table(
        self, table: QTableView, model: FileItemsTableModel
    ) -> QSortFilterProxyModel:
        proxy = QSortFilterProxyModel(self)
        proxy.setSourceModel(model)
        proxy.setSortRole(Qt.UserRole)
        table.setModel(proxy)
        table.setItemDelegateForColumn(0, CheckCellDelegate(table))
        table.setColumnWidth(0, 54)
        self._configure_common_table(table)
        table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        table.setContextMenuPolicy(Qt.CustomContextMenu)
        table.customContextMenuRequested.connect(
            lambda position, target=table: self._show_file_context_menu(target, position)
        )
        table.doubleClicked.connect(lambda _index, target=table: self._reveal_table(target))
        model.dataChanged.connect(self._update_selection_label)
        model.modelReset.connect(self._update_selection_label)
        return proxy

    def set_config(self, config: AppConfig) -> None:
        self._config = config

    def _browse(self) -> None:
        directory = QFileDialog.getExistingDirectory(self, "Select folder to scan")
        if directory:
            self.path_edit.setText(directory)

    def _start_scan(self) -> None:
        path_text = self.path_edit.text().strip()
        if not path_text:
            show_warning(self, "No path", "Enter or browse to a drive or folder to scan.")
            return
        path = Path(path_text)
        if not path.exists():
            show_warning(self, "Path not found", f"'{path}' does not exist.")
            return

        options = ScanOptions(
            include_hidden=self._config.include_hidden_files_in_scans,
            follow_reparse_points=self._config.follow_reparse_points,
        )
        self.start_btn.setEnabled(False)
        self.cancel_btn.setEnabled(True)
        self.progress_bar.setVisible(True)
        self.progress_label.setText("Starting scan...")

        self._worker = ScanWorker(str(path), options)
        self._worker.progress.connect(self._on_progress)
        self._worker.finished_scan.connect(self._on_finished)
        self._worker.failed.connect(self._on_failed)
        self._worker.start()

    def _cancel_scan(self) -> None:
        if self._worker is not None:
            self._worker.cancel()
            self.status_message.emit("Cancelling scan...")

    def _on_progress(self, progress) -> None:
        self.progress_label.setText(
            f"Scanned {progress.files_scanned} files, {progress.folders_scanned} folders "
            f"({format_bytes(progress.bytes_scanned)}) — {progress.current_path}"
        )

    def _on_finished(self, summary: ScanSummary) -> None:
        self._summary = summary
        self.start_btn.setEnabled(True)
        self.cancel_btn.setEnabled(False)
        self.progress_bar.setVisible(False)

        status = "cancelled" if summary.cancelled else "complete"
        self.progress_label.setText(
            f"Scan {status}: {summary.total_files} files, {summary.total_folders} folders, "
            f"{format_bytes(summary.total_size_bytes)}, {summary.error_count} errors"
        )

        self._files_model.set_items(summary.largest_files)
        self._old_files_model.set_items(summary.old_files)
        self._recent_files_model.set_items(summary.recent_files)
        self._folders_model.set_items(summary.largest_folders)

        self.categories_list.clear()
        for category, total in sorted(summary.category_totals.items(), key=lambda kv: -kv[1]):
            self.categories_list.addItem(f"{category}: {format_bytes(total)}")

        self.errors_list.clear()
        for error in summary.errors[:500]:
            self.errors_list.addItem(f"{error.path}: {error.reason}")

        from systemsieve.services.history_service import record_scan
        from systemsieve.storage.result_store import save_latest_scan

        record_scan(summary)
        save_latest_scan(summary)

        self.scan_completed.emit(summary)
        self.status_message.emit("Storage scan finished.")

    def _on_failed(self, message: str) -> None:
        self.start_btn.setEnabled(True)
        self.cancel_btn.setEnabled(False)
        self.progress_bar.setVisible(False)
        show_error(self, "Scan failed", message)

    def _update_selection_label(self, *_args) -> None:
        model, _table, _proxy = self._current_file_context()
        selected = model.checked_items()
        self.selection_label.setText(
            f"{len(selected)} checked ({format_bytes(model.selected_total_size())})"
        )

    def _current_file_context(self):
        contexts = {
            self.files_table: (self._files_model, self.files_table, self._files_proxy),
            self.old_files_table: (
                self._old_files_model,
                self.old_files_table,
                self._old_files_proxy,
            ),
            self.recent_files_table: (
                self._recent_files_model,
                self.recent_files_table,
                self._recent_files_proxy,
            ),
        }
        return contexts.get(self.tabs.currentWidget(), contexts[self.files_table])

    def _selected_current_items(self):
        model, table, proxy = self._current_file_context()
        checked = model.checked_items()
        if checked:
            return checked
        items = []
        for index in table.selectionModel().selectedRows():
            items.append(model.item_at(proxy.mapToSource(index).row()))
        return items

    def _select_all_current(self) -> None:
        model, _table, _proxy = self._current_file_context()
        model.select_all()

    def _clear_current(self) -> None:
        model, table, _proxy = self._current_file_context()
        model.clear_selection()
        table.clearSelection()

    def _reveal_current(self) -> None:
        items = self._selected_current_items()
        if not items:
            show_warning(self, "No selection", "Select one or more file rows first.")
            return
        failures: list[str] = []
        for item in items:
            try:
                reveal_in_explorer(Path(item.path))
            except OSError:
                failures.append(item.path)
        opened = len(items) - len(failures)
        self.status_message.emit(f"Revealed {opened}/{len(items)} item(s) in Explorer.")
        if failures:
            show_warning(
                self,
                "Could not open some locations",
                "These paths no longer exist or Windows could not open them:\n"
                + "\n".join(failures),
            )

    def _reveal_table(self, table: QTableView) -> None:
        self.tabs.setCurrentWidget(table)
        self._reveal_current()

    def _reveal_folder_index(self, index) -> None:
        source_index = self._folders_proxy.mapToSource(index)
        path = Path(self._folders_model.item_at(source_index.row()).path)
        try:
            reveal_in_explorer(path)
        except OSError as exc:
            show_warning(self, "Could not open Explorer", str(exc))

    def _show_file_context_menu(self, table: QTableView, position) -> None:
        self.tabs.setCurrentWidget(table)
        index = table.indexAt(position)
        if index.isValid() and not table.selectionModel().isSelected(index):
            table.selectRow(index.row())
        menu = QMenu(self)
        reveal_action = QAction("Show in Explorer", self)
        reveal_action.triggered.connect(self._reveal_current)
        menu.addAction(reveal_action)
        recycle_action = QAction("Move checked/highlighted files to Recycle Bin…", self)
        recycle_action.triggered.connect(self._recycle_selected)
        menu.addAction(recycle_action)
        menu.exec(table.viewport().mapToGlobal(position))

    def _recycle_selected(self) -> None:
        selected = self._selected_current_items()
        if not selected:
            show_warning(self, "No selection", "Check or highlight one or more files first.")
            return

        from systemsieve.storage.deletion import delete_files, validate_deletion_targets

        paths = [Path(item.path) for item in selected]
        allowed, rejected = validate_deletion_targets(paths)
        if rejected:
            names = "\n".join(f"- {r.path}: {r.message}" for r in rejected)
            show_warning(
                self, "Some files cannot be deleted", f"The following will be skipped:\n{names}"
            )
        if not allowed:
            return

        total = sum(item.size_bytes for item in selected if Path(item.path) in allowed)
        if not ConfirmationDialog.confirm(
            self,
            "Move to Recycle Bin",
            f"Move {len(allowed)} file(s) totalling {format_bytes(total)} to the Recycle Bin?",
        ):
            return

        results = delete_files(allowed, permanent=False)
        succeeded = sum(1 for r in results if r.success)
        self.status_message.emit(f"Moved {succeeded}/{len(allowed)} file(s) to the Recycle Bin.")

        if self._summary is not None:
            deleted_paths = {r.path for r in results if r.success}
            self._summary.largest_files = [
                f for f in self._summary.largest_files if f.path not in deleted_paths
            ]
            self._summary.old_files = [
                f for f in self._summary.old_files if f.path not in deleted_paths
            ]
            self._summary.recent_files = [
                f for f in self._summary.recent_files if f.path not in deleted_paths
            ]
            self._files_model.set_items(self._summary.largest_files)
            self._old_files_model.set_items(self._summary.old_files)
            self._recent_files_model.set_items(self._summary.recent_files)

    def _export(self) -> None:
        if self._summary is None:
            show_warning(self, "No scan results", "Run a scan first.")
            return
        path, _filter = QFileDialog.getSaveFileName(
            self, "Export Scan Results", "scan_results.csv", "CSV (*.csv);;JSON (*.json)"
        )
        if not path:
            return
        from systemsieve.services.export_service import (
            export_scan_summary_csv,
            export_scan_summary_json,
        )

        if path.lower().endswith(".json"):
            result = export_scan_summary_json(self._summary, Path(path))
        else:
            result = export_scan_summary_csv(self._summary, Path(path))
        self.status_message.emit(f"Exported scan results to {result.path}")
