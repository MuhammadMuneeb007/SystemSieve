"""Executes update plans via WinGet. Dry-run by default."""

from __future__ import annotations

from collections.abc import Callable

from systemsieve.logging_config import get_logger
from systemsieve.models.operation import OperationKind, OperationRecord, OperationStatus, UpdatePlan
from systemsieve.package_management.command_runner import CommandRunner, SubprocessCommandRunner

logger = get_logger("updates")


def execute_update(
    plan: UpdatePlan,
    *,
    dry_run: bool = True,
    runner: CommandRunner | None = None,
) -> OperationRecord:
    runner = runner or SubprocessCommandRunner()

    if dry_run:
        return OperationRecord(
            kind=OperationKind.UPDATE,
            target_name=plan.application_name,
            target_id=plan.application_id,
            dry_run=True,
            administrator=plan.requires_admin,
            status=OperationStatus.DRY_RUN,
            details=f"Dry run only. Would execute: {plan.display_command()}",
        )

    result = runner.run(plan.command, timeout=600)
    return OperationRecord(
        kind=OperationKind.UPDATE,
        target_name=plan.application_name,
        target_id=plan.application_id,
        dry_run=False,
        administrator=plan.requires_admin,
        exit_code=result.exit_code,
        status=OperationStatus.SUCCESS if result.exit_code == 0 else OperationStatus.FAILURE,
        stdout=result.stdout,
        stderr=result.stderr,
    )


def execute_bulk_update(
    plans: list[UpdatePlan],
    *,
    dry_run: bool = True,
    continue_on_failure: bool = False,
    runner: CommandRunner | None = None,
    on_progress: Callable[[int, int, UpdatePlan], None] | None = None,
    should_cancel: Callable[[], bool] | None = None,
) -> list[OperationRecord]:
    results: list[OperationRecord] = []
    total = len(plans)

    for index, plan in enumerate(plans, start=1):
        if should_cancel and should_cancel():
            results.append(
                OperationRecord(
                    kind=OperationKind.UPDATE,
                    target_name=plan.application_name,
                    target_id=plan.application_id,
                    dry_run=dry_run,
                    administrator=plan.requires_admin,
                    status=OperationStatus.CANCELLED,
                    details="Bulk update was cancelled before this application was processed.",
                )
            )
            continue

        if on_progress:
            on_progress(index, total, plan)

        record = execute_update(plan, dry_run=dry_run, runner=runner)
        results.append(record)

        if record.status == OperationStatus.FAILURE and not continue_on_failure:
            logger.info("Stopping bulk update after failure on '%s'", plan.application_name)
            break

    return results
