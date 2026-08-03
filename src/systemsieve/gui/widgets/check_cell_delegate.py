"""Accessible checkbox delegate with a full-cell mouse target."""

from __future__ import annotations

from PySide6.QtCore import QEvent, Qt
from PySide6.QtWidgets import QStyledItemDelegate


class CheckCellDelegate(QStyledItemDelegate):
    """Toggle check state anywhere in the cell, or with Space/Select."""

    def editorEvent(self, event, model, option, index):  # noqa: N802
        activate = event.type() == QEvent.MouseButtonRelease and event.button() == Qt.LeftButton
        activate = activate or (
            event.type() == QEvent.KeyPress and event.key() in (Qt.Key_Space, Qt.Key_Select)
        )
        if not activate:
            return super().editorEvent(event, model, option, index)
        current = index.data(Qt.CheckStateRole)
        next_state = Qt.Unchecked if current == Qt.Checked else Qt.Checked
        return bool(model.setData(index, next_state, Qt.CheckStateRole))
