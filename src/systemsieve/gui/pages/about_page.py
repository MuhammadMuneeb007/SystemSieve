"""About page: static application, licence, and privacy information."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QLabel, QVBoxLayout, QWidget

from systemsieve import __app_name__, __version__

ABOUT_HTML = f"""
<h2>{__app_name__} {__version__}</h2>
<p>SystemSieve helps you discover installed Windows software, safely uninstall or update it,
and find large files and folders taking up disk space.</p>

<p><b style="color:#b91c1c">Test SystemSieve in a virtual machine before using it on your main PC.
Uninstalling software or deleting files is not always fully reversible.</b></p>

<p><b>Project:</b> https://github.com/systemsieve/systemsieve<br>
<b>Licence:</b> MIT<br>
<b>Security:</b> See SECURITY.md in the repository for how to report vulnerabilities responsibly.</p>

<p><b>Privacy:</b> SystemSieve works entirely offline except when checking for updates via WinGet.
It does not send telemetry or analytics of any kind. All data (inventory snapshots, scan history,
operation history) is stored locally in a SQLite database on your machine.</p>

<p><b>Dependencies:</b> PySide6, Typer, Rich, send2trash, platformdirs, psutil, packaging, pydantic.</p>
"""


class AboutPage(QWidget):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        layout = QVBoxLayout(self)
        label = QLabel(ABOUT_HTML)
        label.setWordWrap(True)
        label.setTextFormat(Qt.RichText)
        layout.addWidget(label)
        layout.addStretch()
