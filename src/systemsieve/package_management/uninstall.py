"""Executes uninstall plans.

Dry-run is the default everywhere in this module's public API: callers must
pass dry_run=False explicitly to perform a real removal. Administrator-required
steps are escalated through systemsieve.elevation, never by relaunching the
whole application as admin.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Literal

from systemsieve.elevation.manager import (
    ElevationDeclinedError,
    ElevationTimeoutError,
    build_command_request,
    is_elevated,
    run_elevated,
)
from systemsieve.logging_config import get_logger
from systemsieve.models.operation import (
    OperationKind,
    OperationRecord,
    OperationStatus,
    UninstallPlan,
)
from systemsieve.package_management.command_runner import CommandRunner, SubprocessCommandRunner

logger = get_logger("uninstall")

BulkFailureAction = Literal["stop", "continue"]


def execute_uninstall(
    plan: UninstallPlan,
    *,
    dry_run: bool = True,
    runner: CommandRunner | None = None,
) -> OperationRecord:
    runner = runner or SubprocessCommandRunner()

    if not plan.is_supported or not plan.steps:
        return OperationRecord(
            kind=OperationKind.UNINSTALL,
            target_name=plan.application_name,
            target_id=plan.application_id,
            dry_run=dry_run,
            administrator=False,
            status=OperationStatus.FAILURE,
            details=plan.unsupported_reason or "No supported uninstall method available.",
        )

    step = plan.steps[0]

    if dry_run:
        return OperationRecord(
            kind=OperationKind.UNINSTALL,
            target_name=plan.application_name,
            target_id=plan.application_id,
            dry_run=True,
            administrator=step.requires_admin,
            status=OperationStatus.DRY_RUN,
            details=f"Dry run only. Would execute: {' '.join(step.command)}",
        )

    try:
        if step.requires_admin and not is_elevated():
            request = build_command_request(step.command)
            response = run_elevated(request)
            return OperationRecord(
                kind=OperationKind.UNINSTALL,
                target_name=plan.application_name,
                target_id=plan.application_id,
                dry_run=False,
                administrator=True,
                exit_code=response.exit_code,
                status=OperationStatus.SUCCESS if response.success else OperationStatus.FAILURE,
                details=response.error,
                stdout=response.stdout,
                stderr=response.stderr,
            )

        result = runner.run(step.command, timeout=300)
        return OperationRecord(
            kind=OperationKind.UNINSTALL,
            target_name=plan.application_name,
            target_id=plan.application_id,
            dry_run=False,
            administrator=step.requires_admin,
            exit_code=result.exit_code,
            status=OperationStatus.SUCCESS if result.exit_code == 0 else OperationStatus.FAILURE,
            stdout=result.stdout,
            stderr=result.stderr,
        )
    except ElevationDeclinedError as exc:
        return OperationRecord(
            kind=OperationKind.UNINSTALL,
            target_name=plan.application_name,
            target_id=plan.application_id,
            dry_run=False,
            administrator=True,
            status=OperationStatus.CANCELLED,
            details=str(exc),
        )
    except ElevationTimeoutError as exc:
        return OperationRecord(
            kind=OperationKind.UNINSTALL,
            target_name=plan.application_name,
            target_id=plan.application_id,
            dry_run=False,
            administrator=True,
            status=OperationStatus.FAILURE,
            details=str(exc),
        )


def execute_bulk_uninstall(
    plans: list[UninstallPlan],
    *,
    dry_run: bool = True,
    continue_on_failure: bool = False,
    runner: CommandRunner | None = None,
    on_progress: Callable[[int, int, UninstallPlan], None] | None = None,
    on_result: Callable[[int, int, OperationRecord], None] | None = None,
    should_cancel: Callable[[], bool] | None = None,
) -> list[OperationRecord]:
    """Processes applications sequentially, never launching multiple uninstallers at once."""
    results: list[OperationRecord] = []
    total = len(plans)

    for index, plan in enumerate(plans, start=1):
        if should_cancel and should_cancel():
            record = OperationRecord(
                kind=OperationKind.UNINSTALL,
                target_name=plan.application_name,
                target_id=plan.application_id,
                dry_run=dry_run,
                administrator=False,
                status=OperationStatus.CANCELLED,
                details="Bulk operation was cancelled before this application was processed.",
            )
            results.append(record)
            if on_result:
                on_result(index, total, record)
            continue

        if on_progress:
            on_progress(index, total, plan)

        record = execute_uninstall(plan, dry_run=dry_run, runner=runner)
        results.append(record)
        if on_result:
            on_result(index, total, record)

        if record.status == OperationStatus.FAILURE and not continue_on_failure:
            logger.info("Stopping bulk uninstall after failure on '%s'", plan.application_name)
            break

    return results
