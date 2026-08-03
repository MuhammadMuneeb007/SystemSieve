"""Thin façade over the database repositories for operation/scan history."""

from __future__ import annotations

from systemsieve.database.connection import get_connection
from systemsieve.database.repositories import (
    InventorySnapshotRepository,
    OperationsRepository,
    ScanHistoryRepository,
)
from systemsieve.models.application import InstalledApplication
from systemsieve.models.operation import OperationRecord
from systemsieve.models.storage import ScanSummary


def record_operation(record: OperationRecord) -> int:
    conn = get_connection()
    try:
        return OperationsRepository(conn).add(record)
    finally:
        conn.close()


def list_operations(limit: int = 200) -> list[OperationRecord]:
    conn = get_connection()
    try:
        return OperationsRepository(conn).list_recent(limit)
    finally:
        conn.close()


def record_scan(summary: ScanSummary) -> int:
    conn = get_connection()
    try:
        return ScanHistoryRepository(conn).add(summary)
    finally:
        conn.close()


def list_scans(limit: int = 50) -> list[ScanSummary]:
    conn = get_connection()
    try:
        return ScanHistoryRepository(conn).list_recent(limit)
    finally:
        conn.close()


def latest_scan() -> ScanSummary | None:
    conn = get_connection()
    try:
        return ScanHistoryRepository(conn).get_latest()
    finally:
        conn.close()


def record_inventory_snapshot(applications: list[InstalledApplication]) -> int:
    conn = get_connection()
    try:
        return InventorySnapshotRepository(conn).add(applications)
    finally:
        conn.close()
