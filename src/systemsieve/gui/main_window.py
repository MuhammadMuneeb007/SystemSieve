"""The main application window: sidebar navigation over a stacked set of pages."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QByteArray, QSize, QTimer
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QStackedWidget,
    QStatusBar,
    QVBoxLayout,
    QWidget,
)

from systemsieve.config import AppConfig, save_config
from systemsieve.gui.dialogs.error_dialog import show_error
from systemsieve.gui.pages.about_page import AboutPage
from systemsieve.gui.pages.applications_page import ApplicationsPage
from systemsieve.gui.pages.dashboard_page import DashboardPage
from systemsieve.gui.pages.history_page import HistoryPage
from systemsieve.gui.pages.operations_page import OperationsPage
from systemsieve.gui.pages.settings_page import SettingsPage
from systemsieve.gui.pages.storage_page import StoragePage
from systemsieve.gui.pages.updates_page import UpdatesPage
from systemsieve.gui.workers import InventoryWorker
from systemsieve.models.application import InstalledApplication

ICON_PATH = Path(__file__).parent.parent / "resources" / "icons" / "systemsieve.svg"

NAV_ITEMS = [
    "Dashboard",
    "Applications",
    "Updates",
    "Storage",
    "Scan History",
    "Operations",
    "Settings",
    "About",
]


class MainWindow(QMainWindow):
    def __init__(self, config: AppConfig) -> None:
        super().__init__()
        self._config = config
        self._applications: list[InstalledApplication] = []
        self._inventory_worker: InventoryWorker | None = None

        self.setWindowTitle("SystemSieve")
        self.resize(1200, 780)

        central = QWidget()
        self.setCentralWidget(central)
        root_layout = QHBoxLayout(central)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        sidebar = QWidget()
        sidebar.setObjectName("Sidebar")
        sidebar.setFixedWidth(216)
        sidebar_layout = QVBoxLayout(sidebar)
        sidebar_layout.setContentsMargins(14, 18, 14, 14)

        brand_row = QHBoxLayout()
        if ICON_PATH.exists():
            brand_icon = QLabel()
            brand_icon.setPixmap(QIcon(str(ICON_PATH)).pixmap(QSize(42, 42)))
            brand_row.addWidget(brand_icon)
        brand = QLabel("SystemSieve")
        brand.setObjectName("Brand")
        brand.setToolTip("SystemSieve — understand your system before changing it")
        brand_row.addWidget(brand, stretch=1)
        sidebar_layout.addLayout(brand_row)

        self.nav_list = QListWidget()
        self.nav_list.setObjectName("Navigation")
        for name in NAV_ITEMS:
            QListWidgetItem(name, self.nav_list)
        self.nav_list.currentRowChanged.connect(self._on_nav_changed)
        sidebar_layout.addWidget(self.nav_list, stretch=1)
        version_label = QLabel("SAFE SYSTEM MAINTENANCE")
        version_label.setObjectName("SidebarCaption")
        sidebar_layout.addWidget(version_label)
        root_layout.addWidget(sidebar)

        self.stack = QStackedWidget()
        root_layout.addWidget(self.stack, stretch=1)

        self.dashboard_page = DashboardPage()
        self.applications_page = ApplicationsPage(config)
        self.updates_page = UpdatesPage(config)
        self.storage_page = StoragePage(config)
        self.history_page = HistoryPage()
        self.operations_page = OperationsPage()
        self.settings_page = SettingsPage(config)
        self.about_page = AboutPage()

        for page in [
            self.dashboard_page,
            self.applications_page,
            self.updates_page,
            self.storage_page,
            self.history_page,
            self.operations_page,
            self.settings_page,
            self.about_page,
        ]:
            self.stack.addWidget(page)

        self.setStatusBar(QStatusBar())
        if ICON_PATH.exists():
            self.setWindowIcon(QIcon(str(ICON_PATH)))

        self._wire_signals()
        self._restore_geometry()
        self.nav_list.setCurrentRow(0)

        QTimer.singleShot(200, self.refresh_inventory)
        QTimer.singleShot(200, self._load_dashboard_extras)

    # --- wiring ------------------------------------------------------------------

    def _wire_signals(self) -> None:
        self.dashboard_page.scan_apps_requested.connect(self.refresh_inventory)
        self.dashboard_page.scan_storage_requested.connect(lambda: self.nav_list.setCurrentRow(3))
        self.dashboard_page.review_updates_requested.connect(lambda: self.nav_list.setCurrentRow(2))

        self.applications_page.status_message.connect(self._show_status)
        self.applications_page.refresh_requested.connect(self.refresh_inventory)
        self.applications_page.operation_completed.connect(self._on_operations_recorded)

        self.updates_page.status_message.connect(self._show_status)
        self.updates_page.refresh_requested.connect(self.refresh_inventory)
        self.updates_page.operation_completed.connect(self._on_operations_recorded)

        self.storage_page.status_message.connect(self._show_status)
        self.storage_page.scan_completed.connect(
            lambda summary: self.dashboard_page.set_latest_scan(summary)
        )

        self.history_page.status_message.connect(self._show_status)
        self.operations_page.status_message.connect(self._show_status)

        self.settings_page.status_message.connect(self._show_status)
        self.settings_page.config_changed.connect(self._on_config_changed)

    def _on_nav_changed(self, row: int) -> None:
        self.stack.setCurrentIndex(row)
        if row == 4:
            self.history_page.refresh()
        elif row == 5:
            self.operations_page.refresh()

    def _show_status(self, message: str) -> None:
        self.statusBar().showMessage(message, 8000)

    def _load_dashboard_extras(self) -> None:
        try:
            from systemsieve.services.history_service import latest_scan, list_operations

            self.dashboard_page.set_latest_scan(latest_scan())
            self.dashboard_page.set_recent_operations(list_operations(10))
        except Exception as exc:  # noqa: BLE001
            self._show_status(f"Could not load history: {exc}")

    def _on_operations_recorded(self, records: list) -> None:
        from systemsieve.services.history_service import record_operation

        for record in records:
            try:
                record_operation(record)
            except Exception as exc:  # noqa: BLE001
                self._show_status(f"Failed to record operation history: {exc}")
        self.dashboard_page.set_recent_operations(list(records))
        if self.stack.currentWidget() is self.operations_page:
            self.operations_page.refresh()

    def _on_config_changed(self, config: AppConfig) -> None:
        self._config = config
        self.applications_page.set_config(config)
        self.updates_page.set_config(config)
        self.storage_page.set_config(config)
        self.applications_page.set_applications(self._applications)

    # --- inventory -----------------------------------------------------------------

    def refresh_inventory(self) -> None:
        if self._inventory_worker is not None and self._inventory_worker.isRunning():
            return
        self._show_status("Scanning installed applications...")
        self.applications_page.filter_bar.refresh_button.setEnabled(False)

        self._inventory_worker = InventoryWorker()
        self._inventory_worker.finished_ok.connect(self._on_inventory_ready)
        self._inventory_worker.failed.connect(self._on_inventory_failed)
        self._inventory_worker.start()

    def _on_inventory_ready(self, applications: list, winget_available: bool, errors: list) -> None:
        self.applications_page.filter_bar.refresh_button.setEnabled(True)
        self._applications = applications
        self.applications_page.set_applications(applications)
        self.updates_page.set_applications(applications)
        self.dashboard_page.set_applications(applications)

        for error in errors:
            self._show_status(error)

        try:
            from systemsieve.services.history_service import record_inventory_snapshot

            record_inventory_snapshot(applications)
        except Exception as exc:  # noqa: BLE001
            self._show_status(f"Failed to save inventory snapshot: {exc}")

        self._show_status(
            f"Found {len(applications)} applications."
            + ("" if winget_available else " WinGet not detected.")
        )

    def _on_inventory_failed(self, message: str) -> None:
        self.applications_page.filter_bar.refresh_button.setEnabled(True)
        show_error(self, "Inventory scan failed", message)

    # --- window state -----------------------------------------------------------------

    def _restore_geometry(self) -> None:
        if self._config.window_geometry:
            self.restoreGeometry(QByteArray.fromBase64(self._config.window_geometry.encode()))
        if self._config.window_state:
            self.restoreState(QByteArray.fromBase64(self._config.window_state.encode()))

    def closeEvent(self, event) -> None:  # noqa: N802
        self._config.window_geometry = bytes(self.saveGeometry().toBase64()).decode()
        self._config.window_state = bytes(self.saveState().toBase64()).decode()
        save_config(self._config)
        super().closeEvent(event)
