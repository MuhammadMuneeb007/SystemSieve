"""Parses and validates Windows uninstall/modify command strings from the registry.

This is the single safety chokepoint between "text found in the registry" and
"argument array that may eventually be executed". Nothing downstream should
execute a command that has not passed through :func:`validate_command`.

Design principles:
  * We never build or execute a shell string. Everything becomes a validated
    ``list[str]`` argument array passed to a process runner with ``shell=False``.
  * Dangerous shell metacharacters in the *source* registry string are treated
    as a hard rejection, even though they would be inert as literal argv
    tokens under ``shell=False`` -- their presence indicates either a
    malformed/unusual entry or an attempt to smuggle shell behaviour into a
    later code path, and we would rather be over-cautious.
  * Only a small allow-list of executable patterns is considered safe to run
    automatically. Everything else is marked unsupported rather than guessed.
"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass
from enum import StrEnum

_GUID_RE = re.compile(
    r"^\{[0-9A-Fa-f]{8}-[0-9A-Fa-f]{4}-[0-9A-Fa-f]{4}-[0-9A-Fa-f]{4}-[0-9A-Fa-f]{12}\}$"
)

# Shell metacharacters / patterns that cause outright rejection of the source string.
_DANGEROUS_PATTERNS = [
    "&&",
    "||",
    "|",
    ">",
    "<",
    "%COMSPEC%",
]
_DANGEROUS_TOKEN_REGEXES = [
    re.compile(r"-enc(odedcommand)?\b", re.IGNORECASE),  # PowerShell -EncodedCommand
    re.compile(r"iex\s*\(", re.IGNORECASE),  # Invoke-Expression
    re.compile(r"downloadstring", re.IGNORECASE),
]

# Executable basenames that are trusted uninstall entry points.
_TRUSTED_EXE_BASENAMES = {
    "msiexec.exe",
}
_TRUSTED_EXE_SUFFIXES = (".exe",)

# Executable types that are never auto-executed, even if referenced legitimately.
_REJECTED_SUFFIXES = (".bat", ".cmd", ".vbs", ".vbe", ".js", ".jse", ".ps1", ".wsf", ".scr")


class CommandValidationResult(StrEnum):
    VALID = "valid"
    UNSUPPORTED = "unsupported"
    REJECTED = "rejected"


@dataclass(frozen=True)
class ValidatedCommand:
    result: CommandValidationResult
    argv: list[str] | None
    reason: str
    product_code: str | None = None
    is_msi: bool = False


def _win_split(command: str) -> list[str]:
    """Splits a Windows command line into argv tokens using MSVCRT parsing rules.

    Implements the standard algorithm: backslashes escape only when followed by
    a double quote (n backslashes + quote -> n//2 backslashes, and the quote
    toggles quoting if n is even, or is a literal quote if n is odd).
    """
    args: list[str] = []
    current: list[str] = []
    in_quotes = False
    i = 0
    length = len(command)
    started_token = False

    while i < length:
        ch = command[i]
        if ch == "\\":
            backslashes = 0
            while i < length and command[i] == "\\":
                backslashes += 1
                i += 1
            if i < length and command[i] == '"':
                current.append("\\" * (backslashes // 2))
                if backslashes % 2 == 1:
                    current.append('"')
                    i += 1
                else:
                    in_quotes = not in_quotes
                    i += 1
                started_token = True
            else:
                current.append("\\" * backslashes)
                started_token = True
            continue
        if ch == '"':
            in_quotes = not in_quotes
            started_token = True
            i += 1
            continue
        if ch in (" ", "\t") and not in_quotes:
            if started_token:
                args.append("".join(current))
                current = []
                started_token = False
            i += 1
            continue
        current.append(ch)
        started_token = True
        i += 1

    if started_token or current:
        args.append("".join(current))
    return args


def _resolve_env_vars(argv: list[str]) -> list[str]:
    return [os.path.expandvars(arg) for arg in argv]


def _has_dangerous_content(raw: str) -> str | None:
    for pattern in _DANGEROUS_PATTERNS:
        if pattern in raw:
            return f"contains disallowed shell metacharacter sequence '{pattern}'"
    for regex in _DANGEROUS_TOKEN_REGEXES:
        if regex.search(raw):
            return f"matches disallowed pattern '{regex.pattern}'"
    return None


def extract_msi_product_code(raw: str) -> str | None:
    """Extracts a GUID from an MsiExec.exe /I{GUID} or /X{GUID} style string."""
    match = re.search(
        r"\{[0-9A-Fa-f]{8}-[0-9A-Fa-f]{4}-[0-9A-Fa-f]{4}-[0-9A-Fa-f]{4}-[0-9A-Fa-f]{12}\}", raw
    )
    if match and _GUID_RE.match(match.group(0)):
        return match.group(0)
    return None


def validate_command(raw: str | None, *, context: str = "uninstall") -> ValidatedCommand:
    """Validates a raw registry command string and produces a safe argv, if possible.

    Returns UNSUPPORTED (not REJECTED) for strings we simply don't know how to
    safely automate -- callers should offer these only as read-only, informational
    text, never as something SystemSieve executes.
    """
    if not raw or not raw.strip():
        return ValidatedCommand(CommandValidationResult.UNSUPPORTED, None, "No command present")

    raw = raw.strip()

    danger = _has_dangerous_content(raw)
    if danger:
        return ValidatedCommand(CommandValidationResult.REJECTED, None, f"Rejected: {danger}")

    if re.search(r"\bcmd(\.exe)?\s*/c\b", raw, re.IGNORECASE):
        return ValidatedCommand(
            CommandValidationResult.UNSUPPORTED,
            None,
            "Unsupported: 'cmd /c' wrapped commands are not automated in this release",
        )

    try:
        argv = _win_split(raw)
    except Exception as exc:  # noqa: BLE001 - defensive parse boundary
        return ValidatedCommand(
            CommandValidationResult.REJECTED, None, f"Failed to parse command: {exc}"
        )

    if not argv:
        return ValidatedCommand(
            CommandValidationResult.UNSUPPORTED, None, "Command parsed to no tokens"
        )

    argv = _resolve_env_vars(argv)
    executable = argv[0]
    exe_basename = os.path.basename(executable).lower()

    product_code = extract_msi_product_code(raw)
    is_msi = exe_basename == "msiexec.exe" or (
        product_code is not None and "msiexec" in raw.lower()
    )

    if is_msi:
        if product_code is None:
            return ValidatedCommand(
                CommandValidationResult.UNSUPPORTED,
                None,
                "Unsupported: MSI command found but no valid product code GUID could be extracted",
            )
        return ValidatedCommand(
            CommandValidationResult.VALID,
            argv,
            "Valid MSI uninstall command",
            product_code=product_code,
            is_msi=True,
        )

    if exe_basename.endswith(_REJECTED_SUFFIXES):
        return ValidatedCommand(
            CommandValidationResult.UNSUPPORTED,
            None,
            f"Unsupported: script-based uninstallers ('{exe_basename}') are not automated in this release",
        )

    if exe_basename in _TRUSTED_EXE_BASENAMES or exe_basename.endswith(_TRUSTED_EXE_SUFFIXES):
        return ValidatedCommand(
            CommandValidationResult.VALID, argv, f"Valid executable command ({context})"
        )

    return ValidatedCommand(
        CommandValidationResult.UNSUPPORTED,
        None,
        f"Unsupported: executable type for '{exe_basename}' is not in the trusted allow-list",
    )
