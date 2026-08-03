"""Coordinates elevation from the unelevated GUI/CLI process.

The main SystemSieve process (GUI or CLI) never runs elevated as a whole.
Only a single, specific, pre-validated operation is escalated: this module
writes a structured request file, launches a helper process with a UAC
consent prompt ('runas'), waits for a response file, then cleans up both
files. If the user declines the UAC prompt, this is reported as a normal,
non-fatal failure -- never worked around.
"""

from __future__ import annotations

import ctypes
import json
import sys
import time
import uuid
from pathlib import Path

from systemsieve.elevation.protocol import (
    ElevatedOperationKind,
    ElevationRequest,
    ElevationResponse,
)
from systemsieve.logging_config import get_logger
from systemsieve.paths import elevation_result_dir

logger = get_logger("elevation")

_POLL_INTERVAL_SECONDS = 0.5


def is_elevated() -> bool:
    if sys.platform != "win32":
        return False
    try:
        return bool(ctypes.windll.shell32.IsUserAnAdmin())
    except Exception:  # noqa: BLE001
        return False


def _helper_launch_args(request_path: Path) -> tuple[str, str]:
    """Returns (executable, parameters) for ShellExecuteW."""
    if getattr(sys, "frozen", False):
        return sys.executable, f'_elevated-helper --request "{request_path}"'
    return sys.executable, f'-m systemsieve _elevated-helper --request "{request_path}"'


class ElevationDeclinedError(RuntimeError):
    """Raised when the user declines the UAC consent prompt."""


class ElevationTimeoutError(RuntimeError):
    """Raised when the elevated helper does not respond within the timeout."""


def run_elevated(request: ElevationRequest) -> ElevationResponse:
    if sys.platform != "win32":
        raise RuntimeError("Elevation is only supported on Windows.")

    result_dir = elevation_result_dir()
    token = uuid.uuid4().hex
    request_path = result_dir / f"request-{token}.json"
    response_path = result_dir / f"response-{token}.json"

    request_path.write_text(request.model_dump_json(), encoding="utf-8")

    executable, params = _helper_launch_args(request_path)
    # Include the response path via an environment-independent mechanism: append to params.
    params = f'{params} --response "{response_path}"'

    try:
        result_code = ctypes.windll.shell32.ShellExecuteW(
            None, "runas", executable, params, None, 0
        )
        if result_code <= 32:
            logger.warning(
                "Elevation request declined or failed (ShellExecuteW code %d)", result_code
            )
            raise ElevationDeclinedError(
                "Administrator approval was not granted, so this operation was not performed."
            )

        deadline = time.monotonic() + request.timeout_seconds + 15
        while time.monotonic() < deadline:
            if response_path.exists():
                break
            time.sleep(_POLL_INTERVAL_SECONDS)
        else:
            raise ElevationTimeoutError("The elevated operation did not complete in time.")

        data = json.loads(response_path.read_text(encoding="utf-8"))
        return ElevationResponse.model_validate(data)
    finally:
        for path in (request_path, response_path):
            try:
                if path.exists():
                    path.unlink()
            except OSError as exc:
                logger.warning("Failed to remove elevation temp file %s: %s", path, exc)


def build_command_request(argv: list[str], *, timeout_seconds: float = 300.0) -> ElevationRequest:
    return ElevationRequest(
        kind=ElevatedOperationKind.RUN_VALIDATED_COMMAND, argv=argv, timeout_seconds=timeout_seconds
    )


def build_restore_point_request(description: str) -> ElevationRequest:
    return ElevationRequest(
        kind=ElevatedOperationKind.CREATE_RESTORE_POINT, restore_point_description=description
    )
