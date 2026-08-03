"""Activity evidence models: conservative, explainable "last used" signals."""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel


class ActivityConfidence(StrEnum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    UNAVAILABLE = "unavailable"


class ActivityEvidence(BaseModel):
    """A single piece of evidence about whether/when an application was used.

    This is deliberately conservative: it is evidence, not proof. GUI and CLI
    text must never claim an application "was last used on" a date derived
    from low-confidence evidence.
    """

    source: str
    """e.g. 'prefetch', 'executable_mtime', 'install_record'"""

    detected_date: datetime | None = None
    confidence: ActivityConfidence = ActivityConfidence.UNAVAILABLE
    explanation: str = "No reliable activity evidence available"

    model_config = {"frozen": True}
