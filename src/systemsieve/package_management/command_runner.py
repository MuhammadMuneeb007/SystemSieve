"""A minimal, injectable process runner. Every invocation is shell=False.

All callers pass validated argument arrays -- never a shell string built from
untrusted input. This is the single place subprocess.run is invoked from for
package-management operations, which keeps it auditable.
"""

from __future__ import annotations

import subprocess
from dataclasses import dataclass
from typing import Protocol


@dataclass
class CommandResult:
    argv: list[str]
    exit_code: int
    stdout: str
    stderr: str
    timed_out: bool = False


class CommandRunner(Protocol):
    def run(self, argv: list[str], *, timeout: float | None = None) -> CommandResult: ...


class SubprocessCommandRunner:
    """Executes commands as validated argument arrays with shell=False."""

    def run(self, argv: list[str], *, timeout: float | None = None) -> CommandResult:
        if not argv:
            raise ValueError("argv must not be empty")
        try:
            completed = subprocess.run(  # noqa: S603 - argv is validated upstream, shell=False
                argv,
                shell=False,
                capture_output=True,
                text=True,
                timeout=timeout,
                encoding="utf-8",
                errors="replace",
            )
            return CommandResult(
                argv=argv,
                exit_code=completed.returncode,
                stdout=completed.stdout or "",
                stderr=completed.stderr or "",
            )
        except subprocess.TimeoutExpired as exc:
            return CommandResult(
                argv=argv,
                exit_code=-1,
                stdout=(exc.stdout or ""),
                stderr=(exc.stderr or "") + "\nCommand timed out.",
                timed_out=True,
            )
        except OSError as exc:
            return CommandResult(argv=argv, exit_code=-1, stdout="", stderr=str(exc))
