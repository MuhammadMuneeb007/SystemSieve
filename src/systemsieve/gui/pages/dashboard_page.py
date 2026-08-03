"""Dashboard page: at-a-glance summary and quick actions."""

from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from systemsieve.gui.widgets.stat_card import StatCard
from systemsieve.inventory.size_parser import format_bytes
from systemsieve.models.application import InstalledApplication
from systemsieve.models.operation import OperationRecord
from systemsieve.models.storage import ScanSummary


class DashboardPage(QWidget):
    scan_apps_requested = Signal()
    scan_storage_requested = Signal()
    review_updates_requested = Signal()

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        layout = QVBoxLayout(self)

        warning = QLabel(
            "⚠ Test SystemSieve in a virtual machine before using it on your main PC. "
            "Uninstalling software or deleting files cannot always be fully reversed."
        )
        warning.setWordWrap(True)
        warning.setStyleSheet("color: #b91c1c; font-weight: bold;")
        layout.addWidget(warning)

        grid = QGridLayout()
        self.apps_card = StatCard("Installed Applications")
        self.updates_card = StatCard("Available Updates")
        self.storage_card = StatCard("Estimated Application Storage")
        self.last_scan_card = StatCard("Last Disk Scan")
        self.largest_app_card = StatCard("Largest Detected Application")
        self.largest_folder_card = StatCard("Largest Detected Folder")
        for i, card in enumerate(
            [
                self.apps_card,
                self.updates_card,
                self.storage_card,
                self.last_scan_card,
                self.largest_app_card,
                self.largest_folder_card,
            ]
        ):
            grid.addWidget(card, i // 3, i % 3)
        layout.addLayout(grid)

        button_row = QHBoxLayout()
        scan_apps_btn = QPushButton("Scan Applications")
        scan_apps_btn.clicked.connect(self.scan_apps_requested)
        scan_storage_btn = QPushButton("Scan Storage")
        scan_storage_btn.clicked.connect(self.scan_storage_requested)
        review_updates_btn = QPushButton("Review Updates")
        review_updates_btn.clicked.connect(self.review_updates_requested)
        button_row.addWidget(scan_apps_btn)
        button_row.addWidget(scan_storage_btn)
        button_row.addWidget(review_updates_btn)
        layout.addLayout(button_row)

        recent_ops_box = QGroupBox("Recent Operations")
        recent_ops_layout = QVBoxLayout(recent_ops_box)
        self.recent_ops_list = QListWidget()
        recent_ops_layout.addWidget(self.recent_ops_list)
        layout.addWidget(recent_ops_box)

        warnings_box = QGroupBox("Safety Warnings")
        warnings_layout = QVBoxLayout(warnings_box)
        self.warnings_list = QListWidget()
        warnings_layout.addWidget(self.warnings_list)
        layout.addWidget(warnings_box)

    def set_applications(self, applications: list[InstalledApplication]) -> None:
        self.apps_card.set_value(str(len(applications)))
        updates = [a for a in applications if a.update_available]
        self.updates_card.set_value(str(len(updates)))
        total_size = sum(a.estimated_size_bytes or 0 for a in applications)
        self.storage_card.set_value(format_bytes(total_size))

        largest = max(applications, key=lambda a: a.estimated_size_bytes or 0, default=None)
        if largest and largest.estimated_size_bytes:
            self.largest_app_card.set_value(
                f"{largest.display_name} ({format_bytes(largest.estimated_size_bytes)})"
            )
        else:
            self.largest_app_card.set_value("Unknown")

        self.warnings_list.clear()
        protected = [a for a in applications if a.safety_level == "protected"]
        review = [a for a in applications if a.safety_level == "review"]
        if protected:
            self.warnings_list.addItem(
                f"{len(protected)} application(s) are protected and cannot be removed here."
            )
        if review:
            self.warnings_list.addItem(
                f"{len(review)} application(s) are flagged for review before removal."
            )
        if not protected and not review:
            self.warnings_list.addItem("No elevated-risk applications detected.")

    def set_latest_scan(self, summary: ScanSummary | None) -> None:
        if summary is None:
            self.last_scan_card.set_value("Never")
            self.largest_folder_card.set_value("Unknown")
            return
        when = (
            summary.completed_at.strftime("%Y-%m-%d %H:%M")
            if summary.completed_at
            else "In progress"
        )
        self.last_scan_card.set_value(when)
        if summary.largest_folders:
            top = summary.largest_folders[0]
            self.largest_folder_card.set_value(f"{top.path} ({format_bytes(top.total_size_bytes)})")
        else:
            self.largest_folder_card.set_value("Unknown")

    def set_recent_operations(self, records: list[OperationRecord]) -> None:
        self.recent_ops_list.clear()
        for record in records[:10]:
            mode = "dry run" if record.dry_run else "real"
            self.recent_ops_list.addItem(
                f"{record.timestamp.strftime('%Y-%m-%d %H:%M')} — {record.kind.value} — {record.target_name} "
                f"({mode}, {record.status.value})"
            )
