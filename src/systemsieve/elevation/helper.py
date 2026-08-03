"""Entry point executed inside the elevated (UAC-consented) helper process.

Invoked as ``systemsieve _elevated-helper --request <path> --response <path>``.
Reads a single ElevationRequest, re-validates it, performs exactly one
operation, and writes a single ElevationResponse. Never reads or trusts
anything other than the two file paths it is given.
"""

from __future__ import annotations

from pathlib import Path

from systemsieve.elevation.protocol import (
    ElevatedOperationKind,
    ElevationRequest,
    ElevationResponse,
)
from systemsieve.elevation.validation import validate_elevated_request
from systemsieve.logging_config import get_logger
from systemsieve.package_management.command_runner import SubprocessCommandRunner
from systemsieve.restore.restore_point import create_restore_point

logger = get_logger("elevation")


def run(request_path: str, response_path: str) -> None:
    response: ElevationResponse
    try:
        raw = Path(request_path).read_text(encoding="utf-8")
        request = ElevationRequest.model_validate_json(raw)
    except Exception as exc:  # noqa: BLE001 - must always produce a response file
        logger.exception("Failed to read/parse elevation request")
        response = ElevationResponse(
            request_id="unknown", success=False, error=f"Invalid request: {exc}"
        )
        _write_response(response_path, response)
        return

    valid, reason = validate_elevated_request(request)
    if not valid:
        logger.warning("Elevated request %s failed validation: %s", request.request_id, reason)
        response = ElevationResponse(request_id=request.request_id, success=False, error=reason)
        _write_response(response_path, response)
        return

    try:
        if request.kind == ElevatedOperationKind.RUN_VALIDATED_COMMAND:
            runner = SubprocessCommandRunner()
            result = runner.run(request.argv or [], timeout=request.timeout_seconds)
            response = ElevationResponse(
                request_id=request.request_id,
                success=result.exit_code == 0,
                exit_code=result.exit_code,
                stdout=result.stdout,
                stderr=result.stderr,
            )
        elif request.kind == ElevatedOperationKind.CREATE_RESTORE_POINT:
            rp_result = create_restore_point(
                request.restore_point_description or "SystemSieve restore point"
            )
            response = ElevationResponse(
                request_id=request.request_id,
                success=rp_result.success,
                stdout=rp_result.message,
                error=None if rp_result.success else rp_result.message,
            )
        else:
            response = ElevationResponse(
                request_id=request.request_id,
                success=False,
                error=f"Unhandled kind: {request.kind}",
            )
    except Exception as exc:  # noqa: BLE001 - elevated process must not crash silently
        logger.exception("Elevated operation raised an exception")
        response = ElevationResponse(request_id=request.request_id, success=False, error=str(exc))

    _write_response(response_path, response)


def _write_response(response_path: str, response: ElevationResponse) -> None:
    try:
        Path(response_path).write_text(response.model_dump_json(), encoding="utf-8")
    except OSError:
        logger.exception("Failed to write elevation response file %s", response_path)
