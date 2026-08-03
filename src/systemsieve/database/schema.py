"""Versioned SQLite schema definitions."""

from __future__ import annotations

CURRENT_SCHEMA_VERSION = 1

SCHEMA_STATEMENTS_V1: list[str] = [
    """
    CREATE TABLE IF NOT EXISTS schema_meta (
        version INTEGER NOT NULL
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS operations (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        timestamp TEXT NOT NULL,
        kind TEXT NOT NULL,
        target_name TEXT NOT NULL,
        target_id TEXT,
        dry_run INTEGER NOT NULL,
        administrator INTEGER NOT NULL,
        exit_code INTEGER,
        status TEXT NOT NULL,
        details TEXT,
        stdout TEXT,
        stderr TEXT,
        log_location TEXT
    )
    """,
    """
    CREATE INDEX IF NOT EXISTS idx_operations_timestamp ON operations(timestamp)
    """,
    """
    CREATE TABLE IF NOT EXISTS scan_history (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        root_path TEXT NOT NULL,
        started_at TEXT NOT NULL,
        completed_at TEXT,
        cancelled INTEGER NOT NULL DEFAULT 0,
        total_files INTEGER NOT NULL DEFAULT 0,
        total_folders INTEGER NOT NULL DEFAULT 0,
        total_size_bytes INTEGER NOT NULL DEFAULT 0,
        error_count INTEGER NOT NULL DEFAULT 0,
        summary_json TEXT NOT NULL
    )
    """,
    """
    CREATE INDEX IF NOT EXISTS idx_scan_history_started ON scan_history(started_at)
    """,
    """
    CREATE TABLE IF NOT EXISTS inventory_snapshots (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        taken_at TEXT NOT NULL,
        application_count INTEGER NOT NULL,
        applications_json TEXT NOT NULL
    )
    """,
    """
    CREATE INDEX IF NOT EXISTS idx_inventory_snapshots_taken ON inventory_snapshots(taken_at)
    """,
]
