"""A generic yes/no confirmation dialog for destructive actions.

Used for actions that are simpler than a full uninstall/update plan preview
(starting a bulk run, moving files to the Recycle Bin, permanent deletion).
"""

from __future__ import annotations

from PySide6.QtWidgets import QCheckBox, QDialog, QDialogButtonBox, QLabel, QVBoxLayout


class ConfirmationDialog(QDialog):
    def __init__(
        self,
        title: str,
        message: str,
        *,
        require_checkbox_text: str | None = None,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setMinimumWidth(420)

        layout = QVBoxLayout(self)
        label = QLabel(message)
        label.setWordWrap(True)
        layout.addWidget(label)

        self._checkbox: QCheckBox | None = None
        if require_checkbox_text:
            self._checkbox = QCheckBox(require_checkbox_text)
            layout.addWidget(self._checkbox)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        self._ok_button = buttons.button(QDialogButtonBox.Ok)
        if self._checkbox is not None:
            self._ok_button.setEnabled(False)
            self._checkbox.toggled.connect(self._ok_button.setEnabled)

    @staticmethod
    def confirm(
        parent,
        title: str,
        message: str,
        *,
        require_checkbox_text: str | None = None,
    ) -> bool:
        dialog = ConfirmationDialog(
            title, message, require_checkbox_text=require_checkbox_text, parent=parent
        )
        return dialog.exec() == QDialog.Accepted
