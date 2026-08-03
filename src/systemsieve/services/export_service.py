"""Exports application inventory and scan results to CSV or JSON."""

from __future__ import annotations

import csv
import json
from datetime import datetime
from pathlib import Path

from pydantic import BaseModel

from systemsieve.logging_config import get_logger
from systemsieve.models.application import InstalledApplication
from systemsieve.models.storage import FileItem, FolderItem, ScanSummary

logger = get_logger("app")

APPLICATION_EXPORT_FIELDS = [
    "display_name",
    "display_version",
    "publisher",
    "estimated_size_display",
    "install_date",
    "activity_date",
    "activity_confidence",
    "update_available",
    "available_version",
    "source",
    "safety_level",
]


class ExportResult(BaseModel):
    path: str
    format: str
    record_count: int
    exported_at: datetime


def export_applications_csv(applications: list[InstalledApplication], path: Path) -> ExportResult:
    with path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=APPLICATION_EXPORT_FIELDS)
        writer.writeheader()
        for app in applications:
            writer.writerow(
                {
                    "display_name": app.display_name,
                    "display_version": app.display_version or "",
                    "publisher": app.publisher or "",
                    "estimated_size_display": app.estimated_size_display,
                    "install_date": app.install_date.isoformat() if app.install_date else "",
                    "activity_date": app.activity_date.isoformat() if app.activity_date else "",
                    "activity_confidence": app.activity_confidence.value,
                    "update_available": app.update_available,
                    "available_version": app.available_version or "",
                    "source": app.source,
                    "safety_level": app.safety_level,
                }
            )
    logger.info("Exported %d applications to CSV: %s", len(applications), path)
    return ExportResult(
        path=str(path), format="csv", record_count=len(applications), exported_at=datetime.now()
    )


def export_applications_json(applications: list[InstalledApplication], path: Path) -> ExportResult:
    data = [app.model_dump(mode="json") for app in applications]
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")
    logger.info("Exported %d applications to JSON: %s", len(applications), path)
    return ExportResult(
        path=str(path), format="json", record_count=len(applications), exported_at=datetime.now()
    )


def export_scan_summary_json(summary: ScanSummary, path: Path) -> ExportResult:
    path.write_text(summary.model_dump_json(indent=2), encoding="utf-8")
    return ExportResult(
        path=str(path), format="json", record_count=summary.total_files, exported_at=datetime.now()
    )


def export_scan_summary_csv(summary: ScanSummary, path: Path) -> ExportResult:
    """Exports the largest-files list (the most actionable view) as CSV."""
    with path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.writer(fh)
        writer.writerow(["path", "size_bytes", "category", "modified"])
        for item in summary.largest_files:
            writer.writerow(
                [
                    item.path,
                    item.size_bytes,
                    item.category.value,
                    item.modified.isoformat() if item.modified else "",
                ]
            )
    return ExportResult(
        path=str(path),
        format="csv",
        record_count=len(summary.largest_files),
        exported_at=datetime.now(),
    )


def export_file_items_csv(items: list[FileItem], path: Path) -> ExportResult:
    with path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.writer(fh)
        writer.writerow(["path", "size_bytes", "category", "extension", "modified"])
        for item in items:
            writer.writerow(
                [
                    item.path,
                    item.size_bytes,
                    item.category.value,
                    item.extension,
                    item.modified.isoformat() if item.modified else "",
                ]
            )
    return ExportResult(
        path=str(path), format="csv", record_count=len(items), exported_at=datetime.now()
    )


def export_folder_items_csv(items: list[FolderItem], path: Path) -> ExportResult:
    with path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.writer(fh)
        writer.writerow(["path", "total_size_bytes", "file_count", "subfolder_count", "modified"])
        for item in items:
            writer.writerow(
                [
                    item.path,
                    item.total_size_bytes,
                    item.file_count,
                    item.subfolder_count,
                    item.modified.isoformat() if item.modified else "",
                ]
            )
    return ExportResult(
        path=str(path), format="csv", record_count=len(items), exported_at=datetime.now()
    )
