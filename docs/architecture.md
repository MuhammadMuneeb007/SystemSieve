# Architecture

SystemSieve is organised as a set of small, mostly independent subsystems under
`src/systemsieve/`, with the GUI and CLI as thin front-ends over the same core logic.

```
constants.py, paths.py, config.py, logging_config.py   Shared foundation
models/                                                  Typed data models (pydantic)
inventory/          Registry + WinGet discovery, dedup, safety classification
activity/            Conservative "last used" evidence
package_management/  Command validation, planning, WinGet, uninstall/update execution
elevation/           UAC escalation for the single operation that needs it
restore/             Windows System Restore point support
storage/             Disk scanning, categorisation, safe deletion
database/            SQLite connection, schema, migrations, repositories
services/            Export, history, diagnostics facades
cli.py               Typer CLI
gui/                 PySide6 GUI (app shell, main window, pages, dialogs, models)
```

## Data flow: inventory

```
registry_scanner.py  ──┐
                        ├──> deduplicator.py ──> safety_classifier.py ──> activity/service.py ──> InventoryResult
winget_scanner.py    ──┘
```

`inventory/service.py::build_inventory()` is the single entry point both the CLI and GUI
call. It is read-only: it never writes to the registry and never executes anything.

## Data flow: uninstall

```
InstalledApplication ──> operation_planner.plan_uninstall() ──> UninstallPlan
                                                                      │
                                       (preview shown, confirmation required)
                                                                      │
                                                                      v
                                                    package_management/uninstall.py
                                                      │                        │
                                      not admin-required                admin-required
                                                      │                        │
                                                      v                        v
                                        SubprocessCommandRunner      elevation/manager.py
                                                                        (UAC prompt, helper
                                                                         process, structured
                                                                         request/response files)
```

`operation_planner.py` never executes anything -- it only decides *what would happen*,
preferring WinGet > MSI product code > validated quiet uninstall > validated standard
uninstall, in that order, and marking anything else unsupported.

## Command validation boundary

`package_management/command_validator.py` is the single place raw registry text becomes an
executable argument array. Nothing downstream ever builds or runs a shell string; every
process invocation goes through `package_management/command_runner.py` with
`shell=False`. See [safety.md](safety.md) for the full rationale.

## Elevation boundary

The whole application never runs elevated. `elevation/manager.py` (unelevated side) writes
a structured `ElevationRequest` to a temp file, launches a helper process via
`ShellExecuteW(..., "runas", ...)`, and polls for an `ElevationResponse` file.
`elevation/helper.py` (the elevated side, invoked as `systemsieve _elevated-helper`)
re-validates the request independently before acting -- it does not trust that a request
file is safe just because it exists. Both temp files are deleted afterwards.

## Disk scanner

`storage/scanner.py` is deliberately isolated behind a narrow functional interface
(`scan(root, options, on_progress, cancel_event) -> ScanSummary`) so a future, faster
implementation (e.g. a Rust extension) can replace it without touching callers. It uses an
iterative, two-phase (explore/finalize) post-order traversal so folder sizes are only
recorded once every descendant has been accounted for, and so very deep trees cannot cause
a Python recursion error.

## GUI threading

Every long-running operation (`InventoryWorker`, `UninstallWorker`, `UpdateWorker`,
`RestorePointWorker`, `ScanWorker`) is a `QThread` subclass in `gui/workers.py` or
`storage/scan_worker.py`. `MainWindow` never calls scan/WinGet/uninstall code directly on
the UI thread.

## Persistence

SQLite (`database/`) stores operation history, scan history, and inventory snapshots only.
User preferences are stored as JSON (`config.py`, via `platformdirs`) rather than in the
database, since it is a small, simple key-value structure the GUI Settings page reads/writes
as a whole. No telemetry, no file contents, no credentials are ever stored.
