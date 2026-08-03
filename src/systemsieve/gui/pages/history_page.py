"""Scan History page: browse past disk scans recorded in the local database."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QAbstractItemView,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from systemsieve.gui.shell_actions import open_path
from systemsieve.inventory.size_parser import format_bytes

COLUMNS = ["Started", "Completed", "Root Path", "Files", "Folders", "Size", "Errors", "Cancelled"]


class HistoryPage(QWidget):
    status_message = Signal(str)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        layout = QVBoxLayout(self)

        title = QLabel("Scan History")
        title.setObjectName("PageTitle")
        subtitle = QLabel("Compare previous scans and reopen their root locations.")
        subtitle.setObjectName("PageSubtitle")
        layout.addWidget(title)
        layout.addWidget(subtitle)

        top_row = QHBoxLayout()
        refresh_btn = QPushButton("Refresh")
        refresh_btn.clicked.connect(self.refresh)
        open_btn = QPushButton("Open Selected Root")
        open_btn.clicked.connect(self._open_selected_root)
        top_row.addStretch()
        top_row.addWidget(refresh_btn)
        top_row.addWidget(open_btn)
        layout.addLayout(top_row)

        self.table = QTableWidget(0, len(COLUMNS))
        self.table.setHorizontalHeaderLabels(COLUMNS)
        self.table.setSortingEnabled(True)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.table.setAlternatingRowColors(True)
        self.table.verticalHeader().setVisible(False)
        self.table.doubleClicked.connect(lambda _index: self._open_selected_root())
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)
        layout.addWidget(self.table)

    def refresh(self) -> None:
        from systemsieve.services.history_service import list_scans

        try:
            scans = list_scans()
        except Exception as exc:  # noqa: BLE001
            self.status_message.emit(f"Failed to load scan history: {exc}")
            return

        self.table.setSortingEnabled(False)
        self.table.setRowCount(len(scans))
        for row, summary in enumerate(scans):
            self.table.setItem(
                row, 0, QTableWidgetItem(summary.started_at.strftime("%Y-%m-%d %H:%M"))
            )
            self.table.setItem(
                row,
                1,
                QTableWidgetItem(
                    summary.completed_at.strftime("%Y-%m-%d %H:%M") if summary.completed_at else "-"
                ),
            )
            root_item = QTableWidgetItem(summary.root_path)
            root_item.setData(Qt.UserRole, summary.root_path)
            self.table.setItem(row, 2, root_item)
            self.table.setItem(row, 3, QTableWidgetItem(str(summary.total_files)))
            self.table.setItem(row, 4, QTableWidgetItem(str(summary.total_folders)))
            self.table.setItem(row, 5, QTableWidgetItem(format_bytes(summary.total_size_bytes)))
            self.table.setItem(row, 6, QTableWidgetItem(str(summary.error_count)))
            self.table.setItem(row, 7, QTableWidgetItem("Yes" if summary.cancelled else "No"))
        self.table.setSortingEnabled(True)
        self.table.sortItems(0, Qt.DescendingOrder)

    def _open_selected_root(self) -> None:
        row = self.table.currentRow()
        if row < 0:
            self.status_message.emit("Select a scan first.")
            return
        item = self.table.item(row, 2)
        path = Path(str(item.data(Qt.UserRole) or item.text()))
        if path.exists():
            open_path(path)
        else:
            self.status_message.emit(f"Scan root no longer exists: {path}")
