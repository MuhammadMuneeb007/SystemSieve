"""SQLite connection management.

A single local database file stores only operation history, scan history,
and inventory snapshots -- never file contents, credentials, or telemetry.
"""

from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from pathlib import Path

from systemsieve.database.migrations import apply_migrations
from systemsieve.paths import database_path


def _connect(path: Path) -> sqlite3.Connection:
    conn = sqlite3.connect(str(path), timeout=30)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA journal_mode = WAL")
    return conn


def get_connection(path: Path | None = None) -> sqlite3.Connection:
    db_path = path or database_path()
    conn = _connect(db_path)
    apply_migrations(conn)
    return conn


@contextmanager
def session(path: Path | None = None):
    conn = get_connection(path)
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
