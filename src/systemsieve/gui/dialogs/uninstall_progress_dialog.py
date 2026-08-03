"""Persistent progress and results dialog for uninstall operations."""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QLabel,
    QPlainTextEdit,
    QProgressBar,
    QPushButton,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
)

from systemsieve.models.operation import OperationRecord, OperationStatus, UninstallPlan


class UninstallProgressDialog(QDialog):
    cancel_requested = Signal()

    def __init__(self, plans: list[UninstallPlan], *, dry_run: bool, parent=None) -> None:
        super().__init__(parent)
        self._running = True
        self._dry_run = dry_run
        self.setWindowTitle("Uninstall Preview" if dry_run else "Uninstall Progress")
        self.setWindowModality(Qt.WindowModal)
        self.setMinimumSize(720, 500)

        layout = QVBoxLayout(self)
        self.mode_label = QLabel(
            "PREVIEW ONLY — no software will be removed."
            if dry_run
            else "REAL REMOVAL — selected software will be uninstalled."
        )
        self.mode_label.setObjectName("OperationModePreview" if dry_run else "OperationModeReal")
        layout.addWidget(self.mode_label)

        self.stage_label = QLabel("Preparing operation…")
        self.stage_label.setObjectName("OperationStage")
        layout.addWidget(self.stage_label)

        self.progress = QProgressBar()
        self.progress.setRange(0, len(plans))
        self.progress.setValue(0)
        self.progress.setFormat(f"0 of {len(plans)} completed")
        layout.addWidget(self.progress)

        self.items = QTreeWidget()
        self.items.setHeaderLabels(["Application", "Method", "Status"])
        self.items.setRootIsDecorated(False)
        self.items.setAlternatingRowColors(True)
        self.items.header().setStretchLastSection(False)
        self.items.header().resizeSection(0, 330)
        self.items.header().resizeSection(1, 190)
        self._rows: list[QTreeWidgetItem] = []
        for plan in plans:
            row = QTreeWidgetItem([plan.application_name, plan.method.value, "Queued"])
            self.items.addTopLevelItem(row)
            self._rows.append(row)
        layout.addWidget(self.items, stretch=1)

        details_label = QLabel("Operation details")
        details_label.setObjectName("SectionTitle")
        layout.addWidget(details_label)
        self.details = QPlainTextEdit()
        self.details.setReadOnly(True)
        self.details.setMaximumHeight(140)
        self.details.setPlaceholderText("Progress and installer results will appear here.")
        layout.addWidget(self.details)

        button_row = QHBoxLayout()
        button_row.addStretch()
        self.cancel_button = QPushButton("Cancel Remaining")
        self.cancel_button.clicked.connect(self._request_cancel)
        self.close_button = QPushButton("Close")
        self.close_button.setEnabled(False)
        self.close_button.clicked.connect(self.accept)
        button_row.addWidget(self.cancel_button)
        button_row.addWidget(self.close_button)
        layout.addLayout(button_row)

    def set_restore_point_stage(self) -> None:
        self.stage_label.setText("Requesting a Windows restore point before removal…")
        self.details.appendPlainText("Preparing restore point. A UAC prompt may appear.")

    def set_restore_point_result(self, success: bool, message: str) -> None:
        outcome = "created" if success else "failed"
        self.details.appendPlainText(f"Restore point {outcome}: {message}")

    def operation_started(self, index: int, total: int, name: str) -> None:
        row_index = max(0, min(index - 1, len(self._rows) - 1))
        self._set_row_status(row_index, "Running", "#2563eb")
        self.items.setCurrentItem(self._rows[row_index])
        action = "Previewing" if self._dry_run else "Uninstalling"
        self.stage_label.setText(f"{action} {index} of {total}: {name}")
        self.details.appendPlainText(f"[{index}/{total}] {action}: {name}")

    def operation_finished(self, index: int, total: int, record: OperationRecord) -> None:
        colors = {
            OperationStatus.SUCCESS: "#059669",
            OperationStatus.DRY_RUN: "#2563eb",
            OperationStatus.FAILURE: "#dc2626",
            OperationStatus.CANCELLED: "#64748b",
        }
        labels = {
            OperationStatus.SUCCESS: "Completed",
            OperationStatus.DRY_RUN: "Previewed",
            OperationStatus.FAILURE: "Failed",
            OperationStatus.CANCELLED: "Cancelled",
        }
        self._set_row_status(
            index - 1,
            labels.get(record.status, record.status.value),
            colors.get(record.status, "#d97706"),
        )
        self.progress.setValue(index)
        self.progress.setFormat(f"{index} of {total} completed")

        result_line = f"{record.target_name}: {labels.get(record.status, record.status.value)}"
        if record.exit_code is not None:
            result_line += f" (exit code {record.exit_code})"
        self.details.appendPlainText(result_line)
        for text in (record.details, record.stdout, record.stderr):
            if text and text.strip():
                self.details.appendPlainText(text.strip())

    def complete(self, records: list[OperationRecord]) -> None:
        self._running = False
        successes = sum(r.status == OperationStatus.SUCCESS for r in records)
        previews = sum(r.status == OperationStatus.DRY_RUN for r in records)
        failures = sum(r.status == OperationStatus.FAILURE for r in records)
        cancelled = sum(r.status == OperationStatus.CANCELLED for r in records)
        if self._dry_run:
            summary = (
                f"Preview complete: {previews} operation(s) reviewed; no software was removed."
            )
        else:
            summary = f"Finished: {successes} completed, {failures} failed, {cancelled} cancelled."
        self.stage_label.setText(summary)
        self.details.appendPlainText("\n" + summary)
        self.cancel_button.setEnabled(False)
        self.close_button.setEnabled(True)
        self.close_button.setDefault(True)

    def fail(self, message: str) -> None:
        self._running = False
        self.stage_label.setText("The uninstall operation could not continue.")
        self.details.appendPlainText(f"ERROR: {message}")
        self.cancel_button.setEnabled(False)
        self.close_button.setEnabled(True)

    def _set_row_status(self, index: int, label: str, color: str) -> None:
        if not 0 <= index < len(self._rows):
            return
        row = self._rows[index]
        row.setText(2, label)
        row.setForeground(2, QColor(color))

    def _request_cancel(self) -> None:
        self.cancel_button.setEnabled(False)
        self.cancel_button.setText("Cancellation requested")
        self.stage_label.setText("Will stop after the current installer finishes…")
        self.details.appendPlainText(
            "Cancellation requested; the active installer cannot be interrupted safely."
        )
        self.cancel_requested.emit()

    def reject(self) -> None:
        if self._running:
            self._request_cancel()
            return
        super().reject()
