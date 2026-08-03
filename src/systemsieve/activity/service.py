"""Attaches activity evidence to InstalledApplication records."""

from __future__ import annotations

from systemsieve.activity.confidence import pick_best_evidence
from systemsieve.activity.evidence import (
    evidence_from_executable_mtime,
    evidence_from_install_record,
    evidence_from_prefetch,
)
from systemsieve.models.application import InstalledApplication


def gather_evidence(app: InstalledApplication) -> list:
    candidates = [
        evidence_from_prefetch(app.install_location),
        evidence_from_executable_mtime(app.install_location),
        evidence_from_install_record(app.install_date),
    ]
    return candidates


def attach_activity_evidence(apps: list[InstalledApplication]) -> list[InstalledApplication]:
    updated: list[InstalledApplication] = []
    for app in apps:
        candidates = gather_evidence(app)
        best = pick_best_evidence(candidates)
        sources = [c.source for c in candidates if c.confidence.value != "unavailable"]
        updated.append(
            app.model_copy(
                update={
                    "activity_date": best.detected_date,
                    "activity_confidence": best.confidence,
                    "activity_sources": sources,
                    "activity_explanation": best.explanation,
                }
            )
        )
    return updated
