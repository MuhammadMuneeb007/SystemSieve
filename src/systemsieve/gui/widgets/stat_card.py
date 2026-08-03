"""A small labelled statistic tile used on the Dashboard."""

from __future__ import annotations

from PySide6.QtWidgets import QFrame, QLabel, QVBoxLayout


class StatCard(QFrame):
    def __init__(self, title: str, value: str = "-", parent=None) -> None:
        super().__init__(parent)
        self.setFrameShape(QFrame.StyledPanel)
        self.setObjectName("StatCard")

        layout = QVBoxLayout(self)
        self._value_label = QLabel(value)
        self._value_label.setObjectName("StatCardValue")
        font = self._value_label.font()
        font.setPointSize(font.pointSize() + 8)
        font.setBold(True)
        self._value_label.setFont(font)

        self._title_label = QLabel(title)
        self._title_label.setObjectName("StatCardTitle")

        layout.addWidget(self._value_label)
        layout.addWidget(self._title_label)

    def set_value(self, value: str) -> None:
        self._value_label.setText(value)
