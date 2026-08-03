"""Applies versioned schema migrations to a SQLite connection."""

from __future__ import annotations

import sqlite3

from systemsieve.database.schema import CURRENT_SCHEMA_VERSION, SCHEMA_STATEMENTS_V1
from systemsieve.logging_config import get_logger

logger = get_logger("app")

_MIGRATIONS: dict[int, list[str]] = {
    1: SCHEMA_STATEMENTS_V1,
}


def _get_version(conn: sqlite3.Connection) -> int:
    cursor = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='schema_meta'"
    )
    if cursor.fetchone() is None:
        return 0
    row = conn.execute("SELECT version FROM schema_meta LIMIT 1").fetchone()
    return row["version"] if row else 0


def apply_migrations(conn: sqlite3.Connection) -> None:
    current = _get_version(conn)
    for version in range(current + 1, CURRENT_SCHEMA_VERSION + 1):
        statements = _MIGRATIONS.get(version)
        if not statements:
            continue
        logger.info("Applying database migration to version %d", version)
        for statement in statements:
            conn.execute(statement)
        conn.execute("DELETE FROM schema_meta")
        conn.execute("INSERT INTO schema_meta (version) VALUES (?)", (version,))
    conn.commit()
