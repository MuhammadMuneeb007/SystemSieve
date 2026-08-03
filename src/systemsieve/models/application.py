"""The InstalledApplication model: the central record for a discovered application.

Command fields store validated argument arrays (never a shell string) alongside
the original raw text for display/inspection purposes only. Only the validated
argument arrays are ever passed to a process runner.
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

from pydantic import BaseModel, Field

from systemsieve.constants import SAFETY_UNKNOWN
from systemsieve.models.activity import ActivityConfidence


class InstalledApplication(BaseModel):
    id: str
    """Stable synthetic identifier, derived from registry key path or winget id."""

    display_name: str
    display_version: str | None = None
    publisher: str | None = None
    install_date: datetime | None = None
    estimated_size_bytes: int | None = None
    install_location: Path | None = None
    display_icon: str | None = None

    registry_path: str | None = None
    registry_hive: str | None = None

    source: str = "registry"
    """'registry', 'winget', or 'registry+winget' after dedup merge."""

    winget_id: str | None = None

    # Validated argument arrays used for execution. Never a shell string.
    uninstall_command: list[str] | None = None
    quiet_uninstall_command: list[str] | None = None
    modify_command: list[str] | None = None

    # Original raw text preserved for inspection/audit only — never executed directly.
    raw_uninstall_string: str | None = None
    raw_quiet_uninstall_string: str | None = None

    product_code: str | None = None
    """MSI GUID, e.g. {12345678-1234-1234-1234-123456789012}"""

    system_component: bool = False
    requires_admin: bool | None = None

    update_available: bool = False
    current_version: str | None = None
    available_version: str | None = None
    update_source: str | None = None

    uninstall_confidence: str = "unknown"
    """'high', 'medium', 'low', or 'unknown' — how confident we are the uninstall
    command will work without user interaction."""

    safety_level: str = SAFETY_UNKNOWN
    safety_reasons: list[str] = Field(default_factory=list)

    activity_date: datetime | None = None
    activity_confidence: ActivityConfidence = ActivityConfidence.UNAVAILABLE
    activity_sources: list[str] = Field(default_factory=list)
    activity_explanation: str = "No reliable activity evidence available"

    model_config = {"arbitrary_types_allowed": True}

    @property
    def is_protected(self) -> bool:
        from systemsieve.constants import SAFETY_PROTECTED

        return self.safety_level == SAFETY_PROTECTED

    @property
    def estimated_size_display(self) -> str:
        from systemsieve.inventory.size_parser import format_bytes

        if self.estimated_size_bytes is None:
            return "Unknown"
        return format_bytes(self.estimated_size_bytes)
