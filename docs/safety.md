# Safety model

SystemSieve performs potentially destructive operations. This document describes the rules
the codebase enforces, and where the limits of those guarantees are.

> **Test in a virtual machine first.** See [testing.md](testing.md).

## Core rules

1. **Nothing happens on selection.** Checking an application or file only marks it as
   selected. Every destructive action requires a separate, explicit confirmation step that
   shows exactly what will happen.
2. **Dry-run is the default everywhere.** The GUI's dry-run checkbox is checked by default
   (from `AppConfig.dry_run_default`, itself `True` by default). The CLI requires `--execute`
   to perform a real uninstall or update; without it, every destructive command only prints
   its plan.
3. **No shell strings.** `package_management/command_validator.py` parses raw registry
   uninstall strings into validated `list[str]` argument arrays. `command_runner.py` always
   calls `subprocess.run(argv, shell=False, ...)`. Dangerous shell metacharacters
   (`&&`, `||`, `|`, `>`, `<`), PowerShell `-EncodedCommand`, and `cmd /c` wrapping are
   rejected outright rather than passed through.
4. **No arbitrary user-entered commands.** There is no code path that lets a user type a
   command for SystemSieve to execute. Every executed command is derived from a validated
   registry/WinGet/MSI source and re-checked before execution.
5. **Protected components are blocked, not just warned.** `inventory/safety_classifier.py`
   assigns one of `normal` / `review` / `protected` / `unknown`. Applications classified
   `protected` (core OS components, hardware drivers, anything under
   `C:\Windows\System32`) cannot be planned for uninstall at all --
   `operation_planner.plan_uninstall()` returns an unsupported plan for them.
6. **Review warnings before removal** are shown for Microsoft Visual C++ redistributables,
   .NET runtimes, security software, VPN software, Python/Java runtimes, database servers,
   development tools, and shared frameworks (see `constants.WARN_BEFORE_REMOVAL_CATEGORIES`).
7. **Restore points are offered, never guaranteed.** Before a real uninstall, SystemSieve
   can attempt to create a System Restore point. If creation fails, the user is told and
   asked whether to continue -- SystemSieve does not silently proceed. The UI and CLI both
   state plainly that a restore point does not guarantee recovery of every removed
   application or file.
8. **Files go to the Recycle Bin by default.** `storage/deletion.py` uses `send2trash`
   unless the caller explicitly passes `permanent=True`, which the GUI/CLI must obtain a
   second, explicit confirmation for.
9. **Protected directories can never be deleted as a whole.** `storage/protected_paths.py`
   blocks whole-directory deletion of `C:\Windows`, `C:\Program Files`,
   `C:\Program Files (x86)`, `C:\ProgramData`, any drive root, the user profile root, and
   recognisable Windows recovery locations. These locations can still be *scanned*.
10. **The application never runs elevated as a whole.** `elevation/manager.py` escalates
    only a single, specific, pre-validated operation via a UAC prompt and a dedicated
    helper process (`elevation/helper.py`), which independently re-validates the request
    before acting. SystemSieve never attempts to bypass or suppress UAC.
11. **Cancellation is cooperative and safe.** Disk scans and bulk uninstall/update runs
    check a cancellation flag between units of work (per directory, per application) and
    stop cleanly, recording what happened rather than leaving inconsistent state.
12. **Everything is logged.** Every operation (uninstall, update, restore point, deletion)
    is recorded to the local SQLite database and to per-subsystem log files, including
    dry-run/administrator status, exit code, and outcome.

## What SystemSieve does *not* do (by design, in this release)

- It does not remove leftover registry keys or folders after an uninstall.
- It does not click through third-party uninstall wizards.
- It does not attempt secure/multi-pass file erasure.
- It does not guess WinGet package IDs for applications it cannot confidently match.
- It does not execute `.bat`, `.cmd`, `.vbs`, `.ps1`, or other script-based uninstallers --
  these are reported as unsupported rather than run.

## Activity detection

"Last activity detected" is evidence, not proof. Sources, in order of preference:

1. **Prefetch** (medium confidence) -- the modification time of a matching
   `C:\Windows\Prefetch\*.pf` file. Requires the Prefetch folder to be readable (often
   restricted to administrators) and Prefetch to be enabled; both are common enough that
   this frequently falls back to a lower-confidence source.
2. **Executable modification time** (low confidence) -- typically reflects install/update
   time, not usage.
3. **Install record** (low confidence) -- the recorded install date only.

If none of these produce a result, the UI shows "No reliable activity evidence available"
rather than guessing. A low-confidence date is never presented as a guaranteed last-used
date, in the GUI, the CLI, or exports.

## Uninstall confidence and method preference

When planning an uninstall, SystemSieve prefers, in order:

1. WinGet exact package ID (`winget uninstall --id ... --exact`)
2. MSI product code (`msiexec.exe /X{GUID}`)
3. A validated quiet uninstall command from the registry
4. A validated standard uninstall command from the registry

If none of these validate, the application is marked unsupported and SystemSieve will not
attempt removal.

## Reporting a safety issue

See [SECURITY.md](../SECURITY.md). Please do not disclose a safety or security issue
publicly before it has been reviewed.
