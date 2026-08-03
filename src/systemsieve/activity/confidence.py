"""Selects the best available evidence from multiple conservative sources."""

from __future__ import annotations

from datetime import datetime

from systemsieve.models.activity import ActivityConfidence, ActivityEvidence

_RANK = {
    ActivityConfidence.HIGH: 3,
    ActivityConfidence.MEDIUM: 2,
    ActivityConfidence.LOW: 1,
    ActivityConfidence.UNAVAILABLE: 0,
}


def pick_best_evidence(candidates: list[ActivityEvidence]) -> ActivityEvidence:
    if not candidates:
        return ActivityEvidence(source="none", confidence=ActivityConfidence.UNAVAILABLE)
    return max(candidates, key=lambda e: (_RANK[e.confidence], e.detected_date or datetime.min))
