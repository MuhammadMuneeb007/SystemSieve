# Privacy

SystemSieve is designed to work entirely offline and to collect nothing beyond what it
needs to function on your own machine.

## What SystemSieve stores, and where

- **SQLite database** (`%LOCALAPPDATA%\SystemSieve\systemsieve.sqlite3` by default, see
  `systemsieve.paths.database_path`): operation history, disk scan history, and installed-
  application inventory snapshots. All of this stays on your machine.
- **JSON configuration** (`%APPDATA%\SystemSieve\settings.json`): your preferences (dry-run
  default, theme, logging level, etc.).
- **Log files** (`%LOCALAPPDATA%\SystemSieve\logs\`): structured, per-subsystem logs used
  for troubleshooting.

## What SystemSieve does not do

- It does not send telemetry or usage analytics of any kind.
- It does not phone home, check licensing servers, or track feature usage.
- It does not read file contents during disk scans -- only metadata (name, size,
  modification time).
- It does not log file contents, credentials, or authentication tokens.

## Network access

The only network access SystemSieve performs is delegated entirely to WinGet, when you use
update-checking or WinGet-backed uninstall/update features. SystemSieve itself makes no
network requests.

## Troubleshooting export

The GUI can generate a troubleshooting ZIP (see `services/diagnostics_service.py`) containing
the application version, OS version, sanitised logs (Windows usernames in file paths are
redacted), your configuration, and a summary of recent errors. It does **not** include your
full software inventory or personal file paths unless you explicitly opt in when generating
the export.

## Data retention

All data is retained locally until you delete it yourself (uninstalling SystemSieve, or
manually removing the files listed above). There is no remote copy.
