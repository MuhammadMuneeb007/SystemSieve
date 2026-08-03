# SystemSieve

A Windows desktop utility for discovering installed software, safely uninstalling or
updating it, and finding large files and folders to reclaim disk space.

[![Tests](https://github.com/systemsieve/systemsieve/actions/workflows/tests.yml/badge.svg)](https://github.com/systemsieve/systemsieve/actions/workflows/tests.yml)
[![Lint](https://github.com/systemsieve/systemsieve/actions/workflows/lint.yml/badge.svg)](https://github.com/systemsieve/systemsieve/actions/workflows/lint.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

> **⚠️ Test in a virtual machine first.** SystemSieve performs potentially destructive
> operations (uninstalling software, deleting files). Do not use an early build to remove
> important software from your main PC. See [docs/testing.md](docs/testing.md) for a safe
> manual test procedure, and [docs/safety.md](docs/safety.md) for the full safety model.

## Screenshots

![SystemSieve applications inventory with safety color coding](docs/screenshots/applications.png)

The Applications view supports multi-row selection, checkbox selection, searching, category
filters, sortable columns, safety color coding, and Explorer actions. Screenshot data is
representative and does not contain a real machine inventory.

![SystemSieve dashboard](docs/screenshots/dashboard.png)

![SystemSieve uninstall progress and per-application results](docs/screenshots/uninstall-progress.png)

## Features

- **Application inventory** — discovers installed software from the 64-bit, 32-bit, and
  per-user uninstall registry keys, plus WinGet, and merges duplicates into one view.
- **Rich inspection** — version, publisher, size, install date, install location, safety
  classification, and conservative "last activity" evidence (never claimed as certain).
- **Actionable tables** — sortable columns, multi-row and checkbox selection, safety status
  colors, context menus, and direct “Open Location”/“Show in Explorer” actions.
- **Safe uninstallation** — WinGet, MSI product code, quiet uninstall, or standard
  uninstall commands, always previewed, always confirmed, dry-run by default.
- **Updates via WinGet** — check for and apply updates with dry-run previews and progress
  reporting; never guesses at package IDs.
- **Disk scanner** — fast, cancellable, metadata-only scan for large files/folders, file
  categories (including ML/scientific file types), old files, and recently modified files.
- **Safe file deletion** — Recycle Bin by default; permanent deletion requires two explicit
  confirmations and is never the default.
- **Local-only history** — SQLite-backed operation history, scan history, and inventory
  snapshots. No telemetry, no analytics, fully offline except WinGet package lookups.
- **GUI and CLI** — a PySide6 desktop app and a scriptable Typer-based CLI share the same
  safety-first core.

## Safety model (summary)

- Nothing is uninstalled or deleted immediately after selection — every destructive action
  goes through a preview + confirmation step.
- Dry-run is the default everywhere; you must explicitly disable it (GUI checkbox, or
  `--execute` on the CLI) to make a real change.
- Commands are never built as shell strings. Registry uninstall strings are parsed into
  validated argument arrays and executed with `shell=False`; unsupported or suspicious
  commands are never auto-executed.
- Protected Windows components, drivers, security/VPN software, runtimes, database
  servers, and shared frameworks are flagged or blocked before removal.
- The whole application never runs elevated. Only the single operation that needs
  administrator rights is escalated, via a dedicated elevation helper and a UAC prompt.
- Whole-directory deletion of `C:\Windows`, `C:\Program Files`, `C:\Program Files (x86)`,
  `C:\ProgramData`, drive roots, the user profile root, and recovery partitions is blocked.

Read the full details in [docs/safety.md](docs/safety.md).

## Installation

```bash
pip install systemsieve
```

Requires Windows 10/11 and Python 3.11+. Most features (registry scanning, WinGet,
elevation, restore points) only work on Windows; the codebase itself imports cleanly on
other platforms for development purposes.

## Quick start

```bash
systemsieve doctor        # sanity-check your environment
systemsieve apps list     # see what's installed
systemsieve gui           # launch the desktop app
```

## GUI usage

Launch with `systemsieve gui` (or `python -m systemsieve gui`). The main window has eight
sections: Dashboard, Applications, Updates, Storage, Scan History, Operations, Settings,
and About. Every scan, WinGet call, and uninstall/update runs on a background thread, so
the interface stays responsive.

Every uninstall or update goes through a preview dialog showing the exact command that
will run and whether administrator access is required, before anything happens.

## CLI usage

```bash
systemsieve apps list
systemsieve apps inspect "7-Zip"
systemsieve apps updates
systemsieve apps uninstall "Example App"                 # dry run (default)
systemsieve apps uninstall "Example App" --execute        # real removal, asks to confirm
systemsieve apps uninstall "Example App" --execute --yes  # real removal, no prompt
systemsieve apps update "Example App" --execute
systemsieve apps export --format csv
systemsieve disk scan C:\Users\you\Downloads
systemsieve disk largest C:\ --limit 100
systemsieve disk categories C:\Users\you
systemsieve history operations
```

### Dry-run explanation

Every destructive CLI command defaults to a dry run: it prints the exact plan (application,
publisher, version, method, command, whether admin access is required) and makes no
changes. Pass `--execute` to perform the real action; you'll still be asked to confirm
unless you also pass `--yes`. `--yes` is rejected unless `--execute` is also given, and
`--dry-run`/`--execute` together is rejected as a usage error.

## Windows support

SystemSieve targets Windows 10 and Windows 11. Registry scanning, WinGet integration,
elevation, and restore points all rely on Windows-only APIs and are not available on other
platforms.

## Limitations

- WinGet integration depends on WinGet being installed and its text output format; parsing
  is defensive but not guaranteed to match every WinGet version.
- Activity detection is conservative and explicitly not a guarantee — see
  [docs/safety.md](docs/safety.md#activity-detection).
- Script-based uninstallers (`.bat`, `.cmd`, `.vbs`, `.ps1`, etc.) are never auto-executed;
  they are reported as unsupported.
- Leftover registry keys and folders are not cleaned up after uninstall in this release.
- Secure/multi-pass file erasure is not implemented; deletion uses the Recycle Bin or a
  single permanent delete.

## Development setup

```bash
git clone https://github.com/systemsieve/systemsieve.git
cd systemsieve
python -m venv .venv
.venv\Scripts\activate
pip install -e ".[dev]"
pre-commit install
```

## Testing

```bash
pytest -m "not manual and not destructive" --cov=systemsieve
```

See [docs/testing.md](docs/testing.md) for the recommended virtual-machine test procedure
before using a build on a real system.

## Packaging

```bash
python -m build                          # sdist + wheel
pyinstaller packaging/systemsieve.spec   # standalone Windows executable
```

See [docs/release.md](docs/release.md) for details.

## Roadmap

- Rust-backed disk scanner for large volumes.
- Optional leftover registry/folder cleanup (explicit opt-in).
- Richer third-party uninstall wizard automation.
- Code-signed release builds.

## Security reporting

Please report vulnerabilities privately — see [SECURITY.md](SECURITY.md). Do not open a
public issue for security reports.

## Privacy

SystemSieve works entirely offline except for WinGet package lookups. It stores inventory
snapshots, scan history, and operation history locally in SQLite. It sends no telemetry and
includes no analytics. See [docs/privacy.md](docs/privacy.md).

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md).

## Licence

MIT — see [LICENSE](LICENSE).

## Disclaimer

SystemSieve is provided "as is", without warranty of any kind. Uninstalling software or
deleting files can have consequences that are not fully reversible, even with a system
restore point. Use at your own risk, and test in a virtual machine first.
