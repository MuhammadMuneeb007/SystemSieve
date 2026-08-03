"""Operations page: SystemSieve's own record of uninstall/update actions."""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor
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

from systemsieve.paths import log_dir

COLUMNS = ["Timestamp", "Operation", "Target", "Dry Run", "Admin", "Exit Code", "Result", "Details"]


class OperationsPage(QWidget):
    status_message = Signal(str)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        layout = QVBoxLayout(self)

        title = QLabel("Operations")
        title.setObjectName("PageTitle")
        subtitle = QLabel("Auditable previews and execution results recorded by SystemSieve.")
        subtitle.setObjectName("PageSubtitle")
        layout.addWidget(title)
        layout.addWidget(subtitle)

        top_row = QHBoxLayout()
        refresh_btn = QPushButton("Refresh")
        refresh_btn.clicked.connect(self.refresh)
        open_logs_btn = QPushButton("Open Log Folder")
        open_logs_btn.clicked.connect(self._open_log_folder)
        top_row.addStretch()
        top_row.addWidget(refresh_btn)
        top_row.addWidget(open_logs_btn)
        layout.addLayout(top_row)

        self.table = QTableWidget(0, len(COLUMNS))
        self.table.setHorizontalHeaderLabels(COLUMNS)
        self.table.setSortingEnabled(True)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.table.setAlternatingRowColors(True)
        self.table.verticalHeader().setVisible(False)
        self.table.horizontalHeader().setSectionResizeMode(7, QHeaderView.Stretch)
        layout.addWidget(self.table)

    def refresh(self) -> None:
        from systemsieve.services.history_service import list_operations

        try:
            records = list_operations()
        except Exception as exc:  # noqa: BLE001
            self.status_message.emit(f"Failed to load operation history: {exc}")
            return

        self.table.setSortingEnabled(False)
        self.table.setRowCount(len(records))
        for row, record in enumerate(records):
            self.table.setItem(
                row, 0, QTableWidgetItem(record.timestamp.strftime("%Y-%m-%d %H:%M:%S"))
            )
            self.table.setItem(row, 1, QTableWidgetItem(record.kind.value))
            self.table.setItem(row, 2, QTableWidgetItem(record.target_name))
            self.table.setItem(row, 3, QTableWidgetItem("Yes" if record.dry_run else "No"))
            self.table.setItem(row, 4, QTableWidgetItem("Yes" if record.administrator else "No"))
            self.table.setItem(
                row,
                5,
                QTableWidgetItem(str(record.exit_code) if record.exit_code is not None else "-"),
            )
            status_item = QTableWidgetItem(record.status.value)
            status_colors = {
                "success": "#059669",
                "failed": "#dc2626",
                "dry_run": "#2563eb",
                "cancelled": "#64748b",
            }
            status_item.setForeground(QColor(status_colors.get(record.status.value, "#d97706")))
            self.table.setItem(row, 6, status_item)
            self.table.setItem(row, 7, QTableWidgetItem(record.details or ""))
        self.table.setSortingEnabled(True)
        self.table.sortItems(0, Qt.DescendingOrder)

    def add_records(self, records: list) -> None:
        self.refresh()

    def _open_log_folder(self) -> None:
        import os

        os.startfile(str(log_dir()))  # noqa: S606 - user-initiated, opens Explorer only
