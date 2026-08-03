"""Disk-scan result models: files, folders, categories, and scan summaries."""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, Field


class FileCategory(StrEnum):
    DOCUMENTS = "Documents"
    IMAGES = "Images"
    VIDEOS = "Videos"
    AUDIO = "Audio"
    ARCHIVES = "Archives"
    INSTALLERS = "Installers"
    SOURCE_CODE = "Source Code"
    DATA_FILES = "Data Files"
    ML_MODELS = "Machine Learning Models"
    GENOMICS = "Genomics/Scientific"
    VIRTUAL_ENVIRONMENTS = "Virtual Environments"
    TEMPORARY_FILES = "Temporary Files"
    LOGS = "Logs"
    APPLICATION_CACHES = "Application Caches"
    UNKNOWN = "Unknown"


class FileItem(BaseModel):
    path: str
    size_bytes: int
    modified: datetime | None = None
    category: FileCategory = FileCategory.UNKNOWN
    extension: str = ""


class FolderItem(BaseModel):
    path: str
    total_size_bytes: int
    file_count: int
    subfolder_count: int
    modified: datetime | None = None


class ScanError(BaseModel):
    path: str
    reason: str


class ScanSummary(BaseModel):
    id: int | None = None
    root_path: str
    started_at: datetime = Field(default_factory=datetime.now)
    completed_at: datetime | None = None
    cancelled: bool = False
    total_files: int = 0
    total_folders: int = 0
    total_size_bytes: int = 0
    error_count: int = 0
    largest_files: list[FileItem] = Field(default_factory=list)
    largest_folders: list[FolderItem] = Field(default_factory=list)
    old_files: list[FileItem] = Field(default_factory=list)
    """Files older than the configured threshold, largest first."""
    recent_files: list[FileItem] = Field(default_factory=list)
    """Files modified within the configured recent-days window, newest first."""
    category_totals: dict[str, int] = Field(default_factory=dict)
    """Category name -> total bytes."""
    extension_totals: dict[str, int] = Field(default_factory=dict)
    """Extension -> total bytes."""
    errors: list[ScanError] = Field(default_factory=list)
