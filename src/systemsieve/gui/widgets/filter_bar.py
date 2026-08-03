"""A reusable search box + filter dropdown row used by list-style pages."""

from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QComboBox, QHBoxLayout, QLineEdit, QPushButton, QWidget


class FilterBar(QWidget):
    search_changed = Signal(str)
    filter_changed = Signal(str)
    refresh_requested = Signal()

    def __init__(self, filters: list[tuple[str, str]], parent=None) -> None:
        """filters: list of (value, label) pairs for the dropdown."""
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self.search_box = QLineEdit()
        self.search_box.setPlaceholderText("Search by name or publisher...")
        self.search_box.textChanged.connect(self.search_changed)

        self.filter_combo = QComboBox()
        for value, label in filters:
            self.filter_combo.addItem(label, value)
        self.filter_combo.currentIndexChanged.connect(
            lambda _i: self.filter_changed.emit(self.filter_combo.currentData())
        )

        self.refresh_button = QPushButton("Refresh")
        self.refresh_button.clicked.connect(self.refresh_requested)

        layout.addWidget(self.search_box, stretch=2)
        layout.addWidget(self.filter_combo, stretch=1)
        layout.addWidget(self.refresh_button)
