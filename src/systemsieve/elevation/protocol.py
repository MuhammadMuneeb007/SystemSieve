"""Structured request/response schema exchanged between the unelevated GUI/CLI
process and the elevated helper process.

Only these typed models cross the elevation boundary -- never a free-form
command string. The unelevated side writes a request file, launches the
helper with 'runas', and polls for a response file.
"""

from __future__ import annotations

import uuid
from enum import StrEnum

from pydantic import BaseModel, Field


class ElevatedOperationKind(StrEnum):
    RUN_VALIDATED_COMMAND = "run_validated_command"
    CREATE_RESTORE_POINT = "create_restore_point"


class ElevationRequest(BaseModel):
    request_id: str = Field(default_factory=lambda: uuid.uuid4().hex)
    kind: ElevatedOperationKind
    argv: list[str] | None = None
    """Validated argument array. Required for RUN_VALIDATED_COMMAND."""
    restore_point_description: str | None = None
    """Required for CREATE_RESTORE_POINT."""
    timeout_seconds: float = 300.0


class ElevationResponse(BaseModel):
    request_id: str
    success: bool
    exit_code: int | None = None
    stdout: str = ""
    stderr: str = ""
    error: str | None = None
