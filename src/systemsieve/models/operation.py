"""Operation planning and result models for uninstall/update/delete actions."""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, Field


class OperationKind(StrEnum):
    UNINSTALL = "uninstall"
    UPDATE = "update"
    FILE_DELETE = "file_delete"
    RESTORE_POINT = "restore_point"
    SCAN = "scan"


class OperationStatus(StrEnum):
    PLANNED = "planned"
    DRY_RUN = "dry_run"
    SUCCESS = "success"
    PARTIAL_SUCCESS = "partial_success"
    FAILURE = "failure"
    CANCELLED = "cancelled"


class UninstallMethod(StrEnum):
    WINGET = "winget"
    MSI_PRODUCT_CODE = "msi_product_code"
    QUIET_UNINSTALL_COMMAND = "quiet_uninstall_command"
    STANDARD_UNINSTALL_COMMAND = "standard_uninstall_command"
    UNSUPPORTED = "unsupported"


class UninstallStep(BaseModel):
    """A single, fully-resolved, ready-to-execute step."""

    description: str
    command: list[str]
    """Validated argument array. Never a shell string."""
    requires_admin: bool
    working_directory: str | None = None


class UninstallPlan(BaseModel):
    application_id: str
    application_name: str
    publisher: str | None = None
    version: str | None = None
    estimated_size_bytes: int | None = None
    method: UninstallMethod
    steps: list[UninstallStep] = Field(default_factory=list)
    requires_admin: bool = False
    is_supported: bool = True
    unsupported_reason: str | None = None
    safety_level: str = "unknown"
    safety_reasons: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)

    def display_command(self) -> str:
        if not self.steps:
            return "(no command available)"
        return " ".join(self.steps[0].command)


class UpdatePlan(BaseModel):
    application_id: str
    application_name: str
    winget_id: str
    current_version: str | None
    available_version: str | None
    command: list[str]
    requires_admin: bool = True

    def display_command(self) -> str:
        return " ".join(self.command)


class OperationRecord(BaseModel):
    id: int | None = None
    timestamp: datetime = Field(default_factory=datetime.now)
    kind: OperationKind
    target_name: str
    target_id: str | None = None
    dry_run: bool
    administrator: bool
    exit_code: int | None = None
    status: OperationStatus
    details: str | None = None
    stdout: str | None = None
    stderr: str | None = None
    log_location: str | None = None
