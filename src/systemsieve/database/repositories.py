"""Typed repository classes over the SQLite database.

Each repository owns a single table and translates between pydantic models
and rows. Callers should use these instead of writing raw SQL elsewhere.
"""

from __future__ import annotations

import sqlite3
from datetime import datetime

from systemsieve.models.application import InstalledApplication
from systemsieve.models.operation import OperationKind, OperationRecord, OperationStatus
from systemsieve.models.storage import ScanSummary


class OperationsRepository:
    def __init__(self, conn: sqlite3.Connection) -> None:
        self._conn = conn

    def add(self, record: OperationRecord) -> int:
        cursor = self._conn.execute(
            """
            INSERT INTO operations
                (timestamp, kind, target_name, target_id, dry_run, administrator,
                 exit_code, status, details, stdout, stderr, log_location)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                record.timestamp.isoformat(),
                record.kind.value,
                record.target_name,
                record.target_id,
                int(record.dry_run),
                int(record.administrator),
                record.exit_code,
                record.status.value,
                record.details,
                record.stdout,
                record.stderr,
                record.log_location,
            ),
        )
        self._conn.commit()
        return int(cursor.lastrowid)

    def list_recent(self, limit: int = 200) -> list[OperationRecord]:
        rows = self._conn.execute(
            "SELECT * FROM operations ORDER BY id DESC LIMIT ?", (limit,)
        ).fetchall()
        return [self._row_to_record(row) for row in rows]

    @staticmethod
    def _row_to_record(row: sqlite3.Row) -> OperationRecord:
        return OperationRecord(
            id=row["id"],
            timestamp=datetime.fromisoformat(row["timestamp"]),
            kind=OperationKind(row["kind"]),
            target_name=row["target_name"],
            target_id=row["target_id"],
            dry_run=bool(row["dry_run"]),
            administrator=bool(row["administrator"]),
            exit_code=row["exit_code"],
            status=OperationStatus(row["status"]),
            details=row["details"],
            stdout=row["stdout"],
            stderr=row["stderr"],
            log_location=row["log_location"],
        )


class ScanHistoryRepository:
    def __init__(self, conn: sqlite3.Connection) -> None:
        self._conn = conn

    def add(self, summary: ScanSummary) -> int:
        cursor = self._conn.execute(
            """
            INSERT INTO scan_history
                (root_path, started_at, completed_at, cancelled, total_files,
                 total_folders, total_size_bytes, error_count, summary_json)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                summary.root_path,
                summary.started_at.isoformat(),
                summary.completed_at.isoformat() if summary.completed_at else None,
                int(summary.cancelled),
                summary.total_files,
                summary.total_folders,
                summary.total_size_bytes,
                summary.error_count,
                summary.model_dump_json(),
            ),
        )
        self._conn.commit()
        return int(cursor.lastrowid)

    def list_recent(self, limit: int = 50) -> list[ScanSummary]:
        rows = self._conn.execute(
            "SELECT summary_json FROM scan_history ORDER BY id DESC LIMIT ?", (limit,)
        ).fetchall()
        return [ScanSummary.model_validate_json(row["summary_json"]) for row in rows]

    def get_latest(self) -> ScanSummary | None:
        row = self._conn.execute(
            "SELECT summary_json FROM scan_history ORDER BY id DESC LIMIT 1"
        ).fetchone()
        if row is None:
            return None
        return ScanSummary.model_validate_json(row["summary_json"])


class InventorySnapshotRepository:
    def __init__(self, conn: sqlite3.Connection) -> None:
        self._conn = conn

    def add(self, applications: list[InstalledApplication]) -> int:
        import json

        payload = json.dumps([app.model_dump(mode="json") for app in applications])
        cursor = self._conn.execute(
            "INSERT INTO inventory_snapshots (taken_at, application_count, applications_json) VALUES (?, ?, ?)",
            (datetime.now().isoformat(), len(applications), payload),
        )
        self._conn.commit()
        return int(cursor.lastrowid)

    def get_latest(self) -> list[InstalledApplication] | None:
        row = self._conn.execute(
            "SELECT applications_json FROM inventory_snapshots ORDER BY id DESC LIMIT 1"
        ).fetchone()
        if row is None:
            return None
        import json

        data = json.loads(row["applications_json"])
        return [InstalledApplication.model_validate(item) for item in data]
