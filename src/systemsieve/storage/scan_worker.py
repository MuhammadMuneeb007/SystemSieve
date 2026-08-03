"""Qt background-thread wrapper around the pure-Python disk scanner.

Keeps the GUI responsive: the scan runs entirely off the UI thread and reports
progress/completion via signals. Cancellation is cooperative through a
threading.Event checked between directory batches by the scanner itself.
"""

from __future__ import annotations

import threading

from PySide6.QtCore import QThread, Signal

from systemsieve.models.storage import ScanSummary
from systemsieve.storage.scanner import ScanOptions, ScanProgress, scan


class ScanWorker(QThread):
    progress = Signal(object)  # ScanProgress
    finished_scan = Signal(object)  # ScanSummary
    failed = Signal(str)

    def __init__(self, root_path: str, options: ScanOptions | None = None, parent=None) -> None:
        super().__init__(parent)
        self._root_path = root_path
        self._options = options or ScanOptions()
        self._cancel_event = threading.Event()

    def cancel(self) -> None:
        self._cancel_event.set()

    def _on_progress(self, progress: ScanProgress) -> None:
        self.progress.emit(progress)

    def run(self) -> None:
        try:
            summary: ScanSummary = scan(
                self._root_path,
                self._options,
                on_progress=self._on_progress,
                cancel_event=self._cancel_event,
            )
            self.finished_scan.emit(summary)
        except Exception as exc:  # noqa: BLE001 - worker thread boundary must not crash silently
            self.failed.emit(str(exc))
