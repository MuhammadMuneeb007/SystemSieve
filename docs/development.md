# Development setup

## Prerequisites

- Windows 10/11 (most subsystems only work on Windows)
- Python 3.11+
- Git

## Setup

```powershell
git clone https://github.com/systemsieve/systemsieve.git
cd systemsieve
python -m venv .venv
.venv\Scripts\activate
pip install -e ".[dev]"
pre-commit install
```

Or use the helper script, which does the same thing and launches the GUI:

```powershell
.\scripts\run_dev.ps1
```

## Project layout

See [architecture.md](architecture.md) for the subsystem breakdown. Key conventions:

- `src/` layout; the installable package is `systemsieve` under `src/systemsieve/`.
- GUI code (`gui/`) never contains business logic -- it calls into `inventory/`,
  `package_management/`, `storage/`, etc., and only handles presentation and threading.
- Windows-specific code (registry access, elevation, restore points) is isolated in its own
  modules so the rest of the codebase can still be imported (though not fully exercised) on
  non-Windows platforms for editor tooling and static analysis.
- Every process execution goes through `package_management/command_runner.py`
  (`shell=False`, validated argument arrays only).

## Running the app from source

```powershell
python -m systemsieve gui
python -m systemsieve apps list
```

## Code style

- Ruff for linting and formatting (`ruff check .`, `ruff format .`).
- mypy for type checking (`mypy src`).
- Type hints throughout; prefer `pathlib.Path` over string paths.
- Small, focused modules -- avoid growing any single file into a catch-all.

Run everything at once:

```powershell
.\scripts\test.ps1
```

## Adding a new uninstall/update method

1. Extend `package_management/command_validator.py` if a new command shape needs parsing.
2. Extend `package_management/operation_planner.py` to produce an `UninstallPlan`/
   `UpdatePlan` for it, keeping the WinGet > MSI > quiet > standard preference order.
3. Add safety classification keywords to `constants.py` if the change affects what should
   be flagged for review or protected.
4. Update `docs/safety.md` if the change affects the safety model.

## Database migrations

Schema changes go in `database/schema.py` (add a new `SCHEMA_STATEMENTS_V{n}` list) and
`database/migrations.py` (register it in `_MIGRATIONS` and bump
`CURRENT_SCHEMA_VERSION`). Migrations must be additive and safe to run against an existing
database.

## Troubleshooting

### `ImportError: DLL load failed while importing QtCore/QtWidgets: The specified procedure could not be found`

This means Qt6Core.dll itself failed to load (not a "module not found" -- Windows found the
file but a dependency resolved to a mismatched version). We've seen this specifically with
**PySide6 6.10.3 and 6.11.1** on an up-to-date Windows 11 (build 26200) machine, reproduced
even in a fully isolated `venv` with `PATH` scrubbed down to just `System32`/`Windows` -- ruling out
PATH conflicts with other Qt installs (Anaconda's `qt-main`/`pyqt5`, MiKTeX's bundled Qt,
etc.) as the sole cause on that machine. Installing **PySide6 6.8.0.2** in the same
environment fixed it immediately, which is why `pyproject.toml` pins `PySide6==6.8.0.2` for now.

If you hit this:

1. Confirm your installed version: `pip show PySide6`.
2. If it's `6.10.x` or `6.11.x`, reinstall the verified version:
   `pip install --force-reinstall "PySide6==6.8.0.2"`.
3. If that doesn't fix it, it's likely a genuine PATH conflict on your machine -- check for
   other Qt-providing packages/tools (Anaconda `qt-main`/`pyqt5`/`pyqtwebengine`, MiKTeX,
   other PySide/PyQt installs) earlier on `PATH` than your virtual environment, and prefer
   running SystemSieve from a plain (non-Conda) virtual environment if possible.
4. As a last resort, ensure the latest Microsoft Visual C++ Redistributable (x64) is
   installed, though in the case we diagnosed this was not the cause.
