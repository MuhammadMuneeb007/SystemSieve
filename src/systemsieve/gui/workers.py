"""QThread-based background workers.

Every long-running operation (inventory scans, WinGet calls, disk scans,
uninstall/update execution) must run off the UI thread. These workers are the
single place that boundary is enforced for the GUI.
"""

from __future__ import annotations

from collections.abc import Callable

from PySide6.QtCore import QThread, Signal

from systemsieve.models.operation import OperationRecord, UninstallPlan, UpdatePlan


class InventoryWorker(QThread):
    finished_ok = Signal(list, bool, list)  # applications, winget_available, errors
    failed = Signal(str)

    def run(self) -> None:
        try:
            from systemsieve.inventory.service import build_inventory

            result = build_inventory()
            self.finished_ok.emit(result.applications, result.winget_available, result.errors)
        except Exception as exc:  # noqa: BLE001
            self.failed.emit(str(exc))


class UninstallWorker(QThread):
    progress = Signal(int, int, str)  # index, total, current_name
    item_finished = Signal(int, int, object)  # index, total, OperationRecord
    finished_ok = Signal(list)  # list[OperationRecord]
    failed = Signal(str)

    def __init__(
        self,
        plans: list[UninstallPlan],
        *,
        dry_run: bool,
        continue_on_failure: bool,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self._plans = plans
        self._dry_run = dry_run
        self._continue_on_failure = continue_on_failure
        self._cancelled = False

    def cancel(self) -> None:
        self._cancelled = True

    def run(self) -> None:
        try:
            from systemsieve.package_management.uninstall import execute_bulk_uninstall

            def on_progress(index: int, total: int, plan: UninstallPlan) -> None:
                self.progress.emit(index, total, plan.application_name)

            records: list[OperationRecord] = execute_bulk_uninstall(
                self._plans,
                dry_run=self._dry_run,
                continue_on_failure=self._continue_on_failure,
                on_progress=on_progress,
                should_cancel=lambda: self._cancelled,
                on_result=lambda index, total, record: self.item_finished.emit(
                    index, total, record
                ),
            )
            self.finished_ok.emit(records)
        except Exception as exc:  # noqa: BLE001
            self.failed.emit(str(exc))


class UpdateWorker(QThread):
    progress = Signal(int, int, str)
    finished_ok = Signal(list)
    failed = Signal(str)

    def __init__(
        self,
        plans: list[UpdatePlan],
        *,
        dry_run: bool,
        continue_on_failure: bool,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self._plans = plans
        self._dry_run = dry_run
        self._continue_on_failure = continue_on_failure
        self._cancelled = False

    def cancel(self) -> None:
        self._cancelled = True

    def run(self) -> None:
        try:
            from systemsieve.package_management.updates import execute_bulk_update

            def on_progress(index: int, total: int, plan: UpdatePlan) -> None:
                self.progress.emit(index, total, plan.application_name)

            records: list[OperationRecord] = execute_bulk_update(
                self._plans,
                dry_run=self._dry_run,
                continue_on_failure=self._continue_on_failure,
                on_progress=on_progress,
                should_cancel=lambda: self._cancelled,
            )
            self.finished_ok.emit(records)
        except Exception as exc:  # noqa: BLE001
            self.failed.emit(str(exc))


class RestorePointWorker(QThread):
    finished_ok = Signal(bool, str)  # success, message
    failed = Signal(str)

    def __init__(self, description: str, parent=None) -> None:
        super().__init__(parent)
        self._description = description

    def run(self) -> None:
        try:
            from systemsieve.elevation.manager import (
                ElevationDeclinedError,
                build_restore_point_request,
                run_elevated,
            )

            try:
                response = run_elevated(build_restore_point_request(self._description))
                self.finished_ok.emit(response.success, response.error or response.stdout or "Done")
            except ElevationDeclinedError as exc:
                self.finished_ok.emit(False, str(exc))
        except Exception as exc:  # noqa: BLE001
            self.failed.emit(str(exc))


class CallableWorker(QThread):
    """Generic one-off worker for simple background calls (e.g. export)."""

    finished_ok = Signal(object)
    failed = Signal(str)

    def __init__(self, func: Callable[[], object], parent=None) -> None:
        super().__init__(parent)
        self._func = func

    def run(self) -> None:
        try:
            result = self._func()
            self.finished_ok.emit(result)
        except Exception as exc:  # noqa: BLE001
            self.failed.emit(str(exc))
