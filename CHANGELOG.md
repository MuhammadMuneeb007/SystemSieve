# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this
project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.1.1] - 2026-08-03

### Fixed

- Made checkbox cells reliably clickable across Applications, Updates, and Storage tables.
- Added persistent uninstall progress, per-application results, and clear preview/real modes.
- Corrected WinGet elevation validation so approved uninstall requests can execute.
- Made install-location and Explorer actions reliable in packaged Windows builds.
- Repaired README branding, encoding, repository links, warnings, and installation guidance.

### Changed

- Removed generated artifacts from source-control scope and corrected release quality gates.
- Preserved Python wheel/sdist artifacts when producing the standalone Windows build.

## [0.1.0] - 2026-08-03

### Added

- Initial public release.
- Read-only installed-application inventory: 64-bit, 32-bit, and per-user uninstall
  registry keys, plus WinGet, deduplicated into a single view.
- Safety classification (`normal` / `review` / `protected` / `unknown`) with human-readable
  reasons, and hard blocks for core Windows components, drivers, and system-marked entries.
- Conservative, explainable activity-evidence detection (Prefetch, executable modification
  time, install record) with honest confidence levels -- never presented as certain.
- Safe uninstall planning and execution: WinGet, MSI product code, validated quiet
  uninstall, and validated standard uninstall, always dry-run by default, always previewed
  and confirmed before a real change.
- WinGet-backed update detection and execution, dry-run by default.
- Dedicated command parser/validator that rejects shell metacharacters, PowerShell encoded
  commands, and script-based uninstallers; never builds or runs a shell string.
- Elevation helper: escalates only a single validated operation via UAC, never the whole
  application.
- Optional System Restore point creation before uninstall, with honest failure reporting.
- Cancellable, metadata-only disk scanner: largest files/folders, file categories
  (including ML/scientific file types), old files, recently modified files, and scan
  errors.
- Safe file deletion via the Recycle Bin by default; permanent deletion requires two
  explicit confirmations.
- Protected-path enforcement blocking whole-directory deletion of `C:\Windows`,
  `C:\Program Files`, `C:\Program Files (x86)`, `C:\ProgramData`, drive roots, the user
  profile root, and recognisable recovery partitions.
- Local SQLite history for operations, disk scans, and inventory snapshots; CSV/JSON
  export for applications and scan results.
- PySide6 GUI with Dashboard, Applications, Updates, Storage, Scan History, Operations,
  Settings, and About pages; all long-running work runs off the UI thread.
- Typer-based CLI mirroring the GUI's safety model (`--execute` required for real changes,
  `--yes` requires `--execute`, conflicting `--dry-run`/`--execute` rejected).
- PyPI packaging (`pip install systemsieve`) and a PyInstaller build configuration for a
  standalone Windows distribution.
