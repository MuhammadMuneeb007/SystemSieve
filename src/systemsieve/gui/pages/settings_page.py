"""Settings page: user preferences, persisted as JSON via systemsieve.config."""

from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from systemsieve.config import AppConfig, save_config


class SettingsPage(QWidget):
    status_message = Signal(str)
    config_changed = Signal(object)  # AppConfig

    def __init__(self, config: AppConfig, parent=None) -> None:
        super().__init__(parent)
        self._config = config

        layout = QVBoxLayout(self)
        form = QFormLayout()

        self.dry_run_checkbox = QCheckBox(
            "Default to dry-run mode for uninstall and update actions"
        )
        form.addRow(self.dry_run_checkbox)

        self.restore_point_checkbox = QCheckBox(
            "Attempt to create a restore point before bulk uninstall"
        )
        form.addRow(self.restore_point_checkbox)

        self.recycle_bin_checkbox = QCheckBox("Send deleted files to the Recycle Bin by default")
        form.addRow(self.recycle_bin_checkbox)

        self.show_system_checkbox = QCheckBox(
            "Show Windows system components in the Applications list"
        )
        form.addRow(self.show_system_checkbox)

        self.hidden_files_checkbox = QCheckBox("Include hidden files in disk scans")
        form.addRow(self.hidden_files_checkbox)

        self.reparse_checkbox = QCheckBox(
            "Follow reparse points (symlinks/junctions) during disk scans"
        )
        form.addRow(self.reparse_checkbox)

        self.continue_on_failure_checkbox = QCheckBox("Continue bulk operations after a failure")
        form.addRow(self.continue_on_failure_checkbox)

        self.logging_level_combo = QComboBox()
        self.logging_level_combo.addItems(["DEBUG", "INFO", "WARNING", "ERROR"])
        form.addRow("Logging level:", self.logging_level_combo)

        self.theme_combo = QComboBox()
        self.theme_combo.addItems(["system", "light", "dark"])
        form.addRow("Theme:", self.theme_combo)

        db_row = QHBoxLayout()
        self.db_path_edit = QLineEdit()
        self.db_path_edit.setReadOnly(True)
        db_row.addWidget(self.db_path_edit)
        form.addRow("Database location:", db_row)

        export_row = QHBoxLayout()
        self.export_path_edit = QLineEdit()
        browse_export_btn = QPushButton("Browse...")
        browse_export_btn.clicked.connect(self._browse_export)
        export_row.addWidget(self.export_path_edit)
        export_row.addWidget(browse_export_btn)
        form.addRow("Export location:", export_row)

        self.winget_status_label = QLabel("Unknown")
        form.addRow("WinGet detection status:", self.winget_status_label)

        self.developer_mode_checkbox = QCheckBox("Developer mode")
        form.addRow(self.developer_mode_checkbox)

        layout.addLayout(form)

        save_btn = QPushButton("Save Settings")
        save_btn.clicked.connect(self._save)
        layout.addWidget(save_btn)
        layout.addStretch()

        self._load_from_config(config)
        self._check_winget()

    def _load_from_config(self, config: AppConfig) -> None:
        self.dry_run_checkbox.setChecked(config.dry_run_default)
        self.restore_point_checkbox.setChecked(config.create_restore_point_default)
        self.recycle_bin_checkbox.setChecked(config.recycle_bin_default)
        self.show_system_checkbox.setChecked(config.show_system_components)
        self.hidden_files_checkbox.setChecked(config.include_hidden_files_in_scans)
        self.reparse_checkbox.setChecked(config.follow_reparse_points)
        self.continue_on_failure_checkbox.setChecked(config.continue_bulk_on_failure)
        self.logging_level_combo.setCurrentText(config.logging_level)
        self.theme_combo.setCurrentText(config.theme)
        self.db_path_edit.setText(config.database_path)
        self.export_path_edit.setText(config.export_location)
        self.developer_mode_checkbox.setChecked(config.developer_mode)

    def _browse_export(self) -> None:
        directory = QFileDialog.getExistingDirectory(self, "Select export location")
        if directory:
            self.export_path_edit.setText(directory)

    def _check_winget(self) -> None:
        from systemsieve.package_management.winget import is_winget_available

        try:
            available = is_winget_available()
        except Exception:  # noqa: BLE001
            available = False
        self.winget_status_label.setText("Available" if available else "Not detected")

    def _save(self) -> None:
        self._config.dry_run_default = self.dry_run_checkbox.isChecked()
        self._config.create_restore_point_default = self.restore_point_checkbox.isChecked()
        self._config.recycle_bin_default = self.recycle_bin_checkbox.isChecked()
        self._config.show_system_components = self.show_system_checkbox.isChecked()
        self._config.include_hidden_files_in_scans = self.hidden_files_checkbox.isChecked()
        self._config.follow_reparse_points = self.reparse_checkbox.isChecked()
        self._config.continue_bulk_on_failure = self.continue_on_failure_checkbox.isChecked()
        self._config.logging_level = self.logging_level_combo.currentText()
        self._config.theme = self.theme_combo.currentText()
        self._config.export_location = self.export_path_edit.text()
        self._config.developer_mode = self.developer_mode_checkbox.isChecked()

        save_config(self._config)
        self.status_message.emit("Settings saved.")
        self.config_changed.emit(self._config)
