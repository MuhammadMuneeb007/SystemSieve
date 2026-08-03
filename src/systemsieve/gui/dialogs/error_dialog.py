"""Shows actionable error messages to the user instead of raw tracebacks."""

from __future__ import annotations

from PySide6.QtWidgets import QMessageBox, QWidget


def show_error(
    parent: QWidget | None, title: str, message: str, *, detail: str | None = None
) -> None:
    box = QMessageBox(parent)
    box.setIcon(QMessageBox.Critical)
    box.setWindowTitle(title)
    box.setText(message)
    if detail:
        box.setDetailedText(detail)
    box.exec()


def show_warning(parent: QWidget | None, title: str, message: str) -> None:
    box = QMessageBox(parent)
    box.setIcon(QMessageBox.Warning)
    box.setWindowTitle(title)
    box.setText(message)
    box.exec()
