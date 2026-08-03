"""GUI entry point: creates the QApplication and MainWindow, and runs the event loop.

The GUI process itself is never launched elevated. Individual privileged
operations request UAC consent on demand via systemsieve.elevation.
"""

from __future__ import annotations

import sys
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication

from systemsieve.config import load_config
from systemsieve.logging_config import configure_logging, get_logger

STYLE_SHEET_PATH = Path(__file__).parent.parent / "resources" / "styles" / "app.qss"
APP_ICON_PATH = Path(__file__).parent.parent / "resources" / "icons" / "systemsieve.svg"


def run_gui() -> int:
    cfg = load_config()
    configure_logging(cfg.logging_level)
    logger = get_logger("app")

    if hasattr(Qt, "AA_EnableHighDpiScaling"):
        QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
    if hasattr(Qt, "AA_UseHighDpiPixmaps"):
        QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)

    application = QApplication(sys.argv)
    application.setApplicationName("SystemSieve")
    application.setOrganizationName("SystemSieve")
    if APP_ICON_PATH.exists():
        application.setWindowIcon(QIcon(str(APP_ICON_PATH)))

    if STYLE_SHEET_PATH.exists():
        try:
            application.setStyleSheet(STYLE_SHEET_PATH.read_text(encoding="utf-8"))
        except OSError as exc:
            logger.warning("Failed to load stylesheet: %s", exc)

    from systemsieve.gui.main_window import MainWindow

    window = MainWindow(cfg)
    window.show()

    logger.info("SystemSieve GUI started")
    return application.exec()
