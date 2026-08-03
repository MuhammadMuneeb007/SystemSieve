"""Structured logging setup with separate log files per subsystem.

Each subsystem logger writes to its own rotating file under the user's log
directory, in addition to a combined ``systemsieve.log``. Nothing here logs
file contents, credentials, or tokens.
"""

from __future__ import annotations

import logging
import logging.handlers

from systemsieve.paths import log_dir

_SUBSYSTEM_LOGGERS = [
    "app",
    "inventory",
    "storage",
    "updates",
    "uninstall",
    "elevation",
    "errors",
]

_CONFIGURED = False


def configure_logging(level: str = "INFO") -> None:
    global _CONFIGURED
    if _CONFIGURED:
        return
    _CONFIGURED = True

    root = logging.getLogger("systemsieve")
    root.setLevel(getattr(logging, level.upper(), logging.INFO))

    fmt = logging.Formatter(
        fmt="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    combined_handler = logging.handlers.RotatingFileHandler(
        log_dir() / "systemsieve.log", maxBytes=5 * 1024 * 1024, backupCount=3, encoding="utf-8"
    )
    combined_handler.setFormatter(fmt)
    root.addHandler(combined_handler)

    console_handler = logging.StreamHandler()
    console_handler.setFormatter(fmt)
    console_handler.setLevel(logging.WARNING)
    root.addHandler(console_handler)

    for name in _SUBSYSTEM_LOGGERS:
        sub_logger = logging.getLogger(f"systemsieve.{name}")
        handler = logging.handlers.RotatingFileHandler(
            log_dir() / f"{name}.log", maxBytes=2 * 1024 * 1024, backupCount=2, encoding="utf-8"
        )
        handler.setFormatter(fmt)
        sub_logger.addHandler(handler)
        sub_logger.propagate = True


def get_logger(subsystem: str) -> logging.Logger:
    return logging.getLogger(f"systemsieve.{subsystem}")
