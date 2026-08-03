"""Defense-in-depth validation applied inside the elevated helper process.

Even though requests originate from SystemSieve's own unelevated process, the
elevated helper re-validates everything before acting -- it must never trust
that a request file is well-formed or safe just because it exists.
"""

from __future__ import annotations

import os

from systemsieve.elevation.protocol import ElevatedOperationKind, ElevationRequest
from systemsieve.package_management.command_validator import (
    CommandValidationResult,
    validate_command,
)

_ALLOWED_EXE_BASENAMES = {"msiexec.exe", "winget.exe"}


def validate_elevated_request(request: ElevationRequest) -> tuple[bool, str]:
    if request.kind == ElevatedOperationKind.CREATE_RESTORE_POINT:
        if not request.restore_point_description:
            return False, "Restore point request is missing a description."
        return True, "OK"

    if request.kind == ElevatedOperationKind.RUN_VALIDATED_COMMAND:
        if not request.argv:
            return False, "Command request has an empty argument array."

        joined = " ".join(request.argv)
        revalidated = validate_command(joined, context="elevated_execution")
        exe_basename = os.path.basename(request.argv[0]).lower()

        if exe_basename in _ALLOWED_EXE_BASENAMES:
            return True, "OK"

        if revalidated.result == CommandValidationResult.VALID:
            return True, "OK"

        return False, f"Elevated command failed re-validation: {revalidated.reason}"

    return False, f"Unknown operation kind: {request.kind}"
