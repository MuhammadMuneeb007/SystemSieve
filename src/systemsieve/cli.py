"""SystemSieve command-line interface.

Safety rules enforced throughout:
  * Dry-run is the default for every destructive command; --execute is
    required to perform a real action.
  * --dry-run and --execute together is a usage error (exit code 2).
  * --yes without --execute is a usage error (exit code 2).
  * Every real operation prints its exact plan and requires interactive
    confirmation unless --yes is explicitly given.
"""

from __future__ import annotations

import json
from pathlib import Path

import typer
from rich.console import Console
from rich.table import Table

from systemsieve import __app_name__, __version__
from systemsieve.config import load_config
from systemsieve.logging_config import configure_logging
from systemsieve.models.application import InstalledApplication
from systemsieve.models.operation import OperationStatus
from systemsieve.package_management.operation_planner import plan_uninstall, plan_update
from systemsieve.package_management.uninstall import execute_uninstall
from systemsieve.package_management.updates import execute_update
from systemsieve.restore.restore_point import build_default_description

console = Console()
err_console = Console(stderr=True)

app = typer.Typer(
    name="systemsieve",
    help="Discover, inspect, update, and safely remove Windows software and files.",
    no_args_is_help=True,
)
apps_app = typer.Typer(help="Inspect and manage installed applications.", no_args_is_help=True)
disk_app = typer.Typer(help="Scan disk usage for large files and folders.", no_args_is_help=True)
history_app = typer.Typer(help="View SystemSieve's own operation history.", no_args_is_help=True)
app.add_typer(apps_app, name="apps")
app.add_typer(disk_app, name="disk")
app.add_typer(history_app, name="history")


def _init() -> None:
    cfg = load_config()
    configure_logging(cfg.logging_level)


@app.callback()
def _main_callback() -> None:
    _init()


# --- version / doctor / gui ---------------------------------------------------------


@app.command()
def version() -> None:
    """Print the SystemSieve version and exit."""
    console.print(f"{__app_name__} {__version__}")


@app.command()
def doctor() -> None:
    """Check the local environment for common issues."""
    import sys as _sys

    from systemsieve.elevation.manager import is_elevated
    from systemsieve.package_management.winget import is_winget_available

    checks: list[tuple[str, bool, str]] = []
    checks.append(("Running on Windows", _sys.platform == "win32", _sys.platform))
    checks.append(("Python version >= 3.11", _sys.version_info >= (3, 11), _sys.version.split()[0]))

    try:
        from systemsieve.database.connection import get_connection

        conn = get_connection()
        conn.close()
        checks.append(("Local database accessible", True, "OK"))
    except Exception as exc:  # noqa: BLE001
        checks.append(("Local database accessible", False, str(exc)))

    try:
        winget_ok = is_winget_available()
        checks.append(("WinGet available", winget_ok, "Found" if winget_ok else "Not found"))
    except Exception as exc:  # noqa: BLE001
        checks.append(("WinGet available", False, str(exc)))

    checks.append(("Running elevated", is_elevated(), "This is informational, not required."))

    try:
        import PySide6
        from PySide6.QtCore import qVersion

        checks.append(
            ("PySide6/Qt available", True, f"PySide6 {PySide6.__version__}, Qt {qVersion()}")
        )
    except ImportError as exc:
        checks.append(("PySide6/Qt available", False, str(exc)))

    table = Table(title="SystemSieve Doctor")
    table.add_column("Check")
    table.add_column("Status")
    table.add_column("Detail")
    all_ok = True
    for name, ok, detail in checks:
        status = "[green]OK[/green]" if ok else "[red]FAIL[/red]"
        if not ok and name not in ("Running elevated",):
            all_ok = False
        table.add_row(name, status, detail)
    console.print(table)

    if not all_ok:
        raise typer.Exit(code=1)


@app.command()
def gui() -> None:
    """Launch the SystemSieve graphical interface."""
    from systemsieve.gui.app import run_gui

    raise typer.Exit(code=run_gui())


# --- apps ------------------------------------------------------------------------


def _build_inventory_list(show_system_components: bool | None = None) -> list[InstalledApplication]:
    from systemsieve.inventory.service import build_inventory, filter_visible

    cfg = load_config()
    result = build_inventory()
    for error in result.errors:
        err_console.print(f"[yellow]Warning:[/yellow] {error}")
    show = cfg.show_system_components if show_system_components is None else show_system_components
    return filter_visible(result.applications, show_system_components=show)


def _find_application(
    name_or_id: str, applications: list[InstalledApplication]
) -> InstalledApplication | None:
    for app_record in applications:
        if app_record.id == name_or_id:
            return app_record
    matches = [a for a in applications if a.display_name.lower() == name_or_id.lower()]
    if len(matches) == 1:
        return matches[0]
    if not matches:
        matches = [a for a in applications if name_or_id.lower() in a.display_name.lower()]
    if len(matches) == 1:
        return matches[0]
    if len(matches) > 1:
        err_console.print(f"[red]Ambiguous application name '{name_or_id}'. Matches:[/red]")
        for m in matches:
            err_console.print(f"  - {m.display_name} ({m.id})")
    return None


@apps_app.command("list")
def apps_list(
    json_output: bool = typer.Option(False, "--json", help="Output as JSON."),
    show_system_components: bool = typer.Option(
        False, "--show-system-components", help="Include Windows system components."
    ),
) -> None:
    """List installed applications."""
    applications = _build_inventory_list(show_system_components=show_system_components)

    if json_output:
        console.print_json(json.dumps([a.model_dump(mode="json") for a in applications]))
        return

    table = Table(title=f"Installed Applications ({len(applications)})")
    table.add_column("Application")
    table.add_column("Version")
    table.add_column("Publisher")
    table.add_column("Size")
    table.add_column("Update")
    table.add_column("Safety")
    for a in applications:
        table.add_row(
            a.display_name,
            a.display_version or "-",
            a.publisher or "-",
            a.estimated_size_display,
            (a.available_version or "Yes") if a.update_available else "-",
            a.safety_level,
        )
    console.print(table)


@apps_app.command("inspect")
def apps_inspect(application: str) -> None:
    """Show complete metadata for one application."""
    applications = _build_inventory_list(show_system_components=True)
    target = _find_application(application, applications)
    if target is None:
        err_console.print(f"[red]Application not found:[/red] {application}")
        raise typer.Exit(code=1)

    console.print(f"[bold]{target.display_name}[/bold]")
    console.print(f"Version: {target.display_version or 'Unknown'}")
    console.print(f"Publisher: {target.publisher or 'Unknown'}")
    console.print(f"Estimated size: {target.estimated_size_display}")
    console.print(f"Install location: {target.install_location or 'Unknown'}")
    console.print(f"Source: {target.source}")
    console.print(f"WinGet ID: {target.winget_id or 'N/A'}")
    console.print(f"Registry path: {target.registry_path or 'N/A'}")
    console.print(
        f"Uninstall command (validated): {' '.join(target.uninstall_command) if target.uninstall_command else 'None available'}"
    )
    console.print(
        f"Quiet uninstall command (validated): {' '.join(target.quiet_uninstall_command) if target.quiet_uninstall_command else 'None available'}"
    )
    console.print(
        f"Update available: {target.update_available} ({target.available_version or 'N/A'})"
    )
    console.print(f"Safety level: [bold]{target.safety_level}[/bold]")
    for reason in target.safety_reasons:
        console.print(f"  - {reason}")
    console.print(f"Activity confidence: {target.activity_confidence.value}")
    console.print(f"Activity explanation: {target.activity_explanation}")


@apps_app.command("updates")
def apps_updates(json_output: bool = typer.Option(False, "--json")) -> None:
    """List applications with an available update."""
    applications = [a for a in _build_inventory_list() if a.update_available]
    if json_output:
        console.print_json(json.dumps([a.model_dump(mode="json") for a in applications]))
        return
    table = Table(title=f"Available Updates ({len(applications)})")
    table.add_column("Application")
    table.add_column("Current")
    table.add_column("Available")
    table.add_column("Package ID")
    for a in applications:
        table.add_row(
            a.display_name,
            a.current_version or a.display_version or "-",
            a.available_version or "-",
            a.winget_id or "-",
        )
    console.print(table)


def _confirm_or_exit(prompt: str, yes: bool) -> None:
    if yes:
        return
    if not typer.confirm(prompt):
        console.print("Cancelled.")
        raise typer.Exit(code=3)


@apps_app.command("uninstall")
def apps_uninstall(
    application: str,
    dry_run: bool = typer.Option(False, "--dry-run", help="Preview only (default behaviour)."),
    execute: bool = typer.Option(False, "--execute", help="Perform the real uninstall."),
    yes: bool = typer.Option(
        False, "--yes", help="Skip interactive confirmation. Requires --execute."
    ),
    restore_point: bool = typer.Option(
        True, "--restore-point/--no-restore-point", help="Attempt to create a restore point first."
    ),
) -> None:
    """Uninstall an application. Dry-run unless --execute is given."""
    if dry_run and execute:
        err_console.print("[red]Error:[/red] --dry-run and --execute cannot be used together.")
        raise typer.Exit(code=2)
    if yes and not execute:
        err_console.print("[red]Error:[/red] --yes requires --execute.")
        raise typer.Exit(code=2)

    effective_dry_run = not execute

    applications = _build_inventory_list(show_system_components=True)
    target = _find_application(application, applications)
    if target is None:
        err_console.print(f"[red]Application not found:[/red] {application}")
        raise typer.Exit(code=1)

    plan = plan_uninstall(target)

    console.print(f"Application: {plan.application_name}")
    console.print(f"Publisher: {plan.publisher or 'Unknown'}")
    console.print(f"Version: {plan.version or 'Unknown'}")
    console.print(f"Method: {plan.method.value}")
    console.print(f"Command: {plan.display_command()}")
    console.print(f"Administrator access: {'Required' if plan.requires_admin else 'Not required'}")
    console.print(
        f"Restore point: {'Requested' if (restore_point and execute) else 'Not requested'}"
    )
    for warning in plan.warnings:
        console.print(f"[yellow]Warning:[/yellow] {warning}")

    if not plan.is_supported:
        err_console.print(f"[red]Cannot proceed:[/red] {plan.unsupported_reason}")
        raise typer.Exit(code=4)

    if effective_dry_run:
        console.print("[cyan]Dry run only. No changes were made.[/cyan]")
        raise typer.Exit(code=0)

    _confirm_or_exit(f"Proceed with uninstalling '{plan.application_name}'?", yes)

    if restore_point:
        from systemsieve.elevation.manager import (
            ElevationDeclinedError,
            build_restore_point_request,
            run_elevated,
        )

        console.print("Creating restore point...")
        try:
            response = run_elevated(build_restore_point_request(build_default_description()))
            if not response.success:
                err_console.print(f"[red]Restore point creation failed:[/red] {response.error}")
                if yes:
                    err_console.print(
                        "[red]Aborting because --yes was given and the restore point could not be created. "
                        "Re-run interactively or with --no-restore-point to proceed anyway.[/red]"
                    )
                    raise typer.Exit(code=1)
                if not typer.confirm("Continue without a restore point?"):
                    raise typer.Exit(code=3)
        except ElevationDeclinedError as exc:
            err_console.print(f"[red]{exc}[/red]")
            raise typer.Exit(code=3) from exc

    record = execute_uninstall(plan, dry_run=False)
    from systemsieve.services.history_service import record_operation

    record_operation(record)

    if record.status == OperationStatus.SUCCESS:
        console.print("[green]Uninstall completed successfully.[/green]")
        raise typer.Exit(code=0)
    console.print(f"[red]Uninstall did not succeed: {record.status.value}[/red]")
    if record.details:
        console.print(record.details)
    raise typer.Exit(code=1)


@apps_app.command("update")
def apps_update(
    application: str,
    dry_run: bool = typer.Option(False, "--dry-run"),
    execute: bool = typer.Option(False, "--execute"),
    yes: bool = typer.Option(False, "--yes"),
) -> None:
    """Update a single application via WinGet. Dry-run unless --execute is given."""
    if dry_run and execute:
        err_console.print("[red]Error:[/red] --dry-run and --execute cannot be used together.")
        raise typer.Exit(code=2)
    if yes and not execute:
        err_console.print("[red]Error:[/red] --yes requires --execute.")
        raise typer.Exit(code=2)

    effective_dry_run = not execute

    applications = _build_inventory_list()
    target = _find_application(application, applications)
    if target is None:
        err_console.print(f"[red]Application not found:[/red] {application}")
        raise typer.Exit(code=1)

    plan = plan_update(target)
    if plan is None:
        err_console.print(
            f"[red]No confident WinGet update mapping is available for '{target.display_name}'.[/red]"
        )
        raise typer.Exit(code=4)

    console.print(f"Application: {plan.application_name}")
    console.print(f"Current version: {plan.current_version or 'Unknown'}")
    console.print(f"Available version: {plan.available_version or 'Unknown'}")
    console.print(f"Command: {plan.display_command()}")

    if effective_dry_run:
        console.print("[cyan]Dry run only. No changes were made.[/cyan]")
        raise typer.Exit(code=0)

    _confirm_or_exit(f"Proceed with updating '{plan.application_name}'?", yes)

    record = execute_update(plan, dry_run=False)
    from systemsieve.services.history_service import record_operation

    record_operation(record)

    if record.status == OperationStatus.SUCCESS:
        console.print("[green]Update completed successfully.[/green]")
        raise typer.Exit(code=0)
    console.print(f"[red]Update did not succeed: {record.status.value}[/red]")
    raise typer.Exit(code=1)


@apps_app.command("export")
def apps_export(
    format: str = typer.Option("csv", "--format", help="csv or json"),
    output: Path | None = typer.Option(None, "--output", help="Output file path."),  # noqa: B008
) -> None:
    """Export the installed-application inventory."""
    from systemsieve.paths import export_dir
    from systemsieve.services.export_service import (
        export_applications_csv,
        export_applications_json,
    )

    if format not in ("csv", "json"):
        err_console.print("[red]Error:[/red] --format must be 'csv' or 'json'.")
        raise typer.Exit(code=2)

    applications = _build_inventory_list()
    target_path = output or (export_dir() / f"applications.{format}")

    if format == "csv":
        result = export_applications_csv(applications, target_path)
    else:
        result = export_applications_json(applications, target_path)

    console.print(f"Exported {result.record_count} applications to {result.path}")


# --- disk ------------------------------------------------------------------------


@disk_app.command("scan")
def disk_scan(path: Path, json_output: bool = typer.Option(False, "--json")) -> None:
    """Scan a drive or folder and summarise disk usage."""
    from systemsieve.services.history_service import record_scan
    from systemsieve.storage.result_store import save_latest_scan
    from systemsieve.storage.scanner import scan

    cfg = load_config()
    from systemsieve.storage.scanner import ScanOptions

    options = ScanOptions(
        include_hidden=cfg.include_hidden_files_in_scans,
        follow_reparse_points=cfg.follow_reparse_points,
    )

    with console.status(f"Scanning {path}..."):
        summary = scan(path, options)

    record_scan(summary)
    save_latest_scan(summary)

    if json_output:
        console.print_json(summary.model_dump_json())
        return

    console.print(f"Root: {summary.root_path}")
    console.print(f"Files: {summary.total_files}   Folders: {summary.total_folders}")
    from systemsieve.inventory.size_parser import format_bytes

    console.print(f"Total size: {format_bytes(summary.total_size_bytes)}")
    console.print(f"Errors: {summary.error_count}")
    if summary.cancelled:
        console.print("[yellow]Scan was cancelled before completion.[/yellow]")


@disk_app.command("largest")
def disk_largest(path: Path, limit: int = typer.Option(100, "--limit")) -> None:
    """Show the largest files under PATH."""
    from systemsieve.inventory.size_parser import format_bytes
    from systemsieve.storage.scanner import scan

    with console.status(f"Scanning {path}..."):
        summary = scan(path)

    table = Table(title=f"Largest Files under {path}")
    table.add_column("Size")
    table.add_column("Path")
    for item in summary.largest_files[:limit]:
        table.add_row(format_bytes(item.size_bytes), item.path)
    console.print(table)


@disk_app.command("categories")
def disk_categories(path: Path) -> None:
    """Show file category totals under PATH."""
    from systemsieve.inventory.size_parser import format_bytes
    from systemsieve.storage.scanner import scan

    with console.status(f"Scanning {path}..."):
        summary = scan(path)

    table = Table(title=f"Category Totals under {path}")
    table.add_column("Category")
    table.add_column("Total Size")
    for category, total in sorted(summary.category_totals.items(), key=lambda kv: -kv[1]):
        table.add_row(category, format_bytes(total))
    console.print(table)


# --- history ------------------------------------------------------------------------


@history_app.command("operations")
def history_operations(
    limit: int = typer.Option(50, "--limit"), json_output: bool = typer.Option(False, "--json")
) -> None:
    """Show SystemSieve's recorded operation history."""
    from systemsieve.services.history_service import list_operations

    records = list_operations(limit)
    if json_output:
        console.print_json(json.dumps([r.model_dump(mode="json") for r in records]))
        return

    table = Table(title="Operation History")
    table.add_column("Timestamp")
    table.add_column("Kind")
    table.add_column("Target")
    table.add_column("Dry Run")
    table.add_column("Status")
    for r in records:
        table.add_row(
            r.timestamp.isoformat(timespec="seconds"),
            r.kind.value,
            r.target_name,
            str(r.dry_run),
            r.status.value,
        )
    console.print(table)


# --- hidden elevated helper entry point --------------------------------------------


@app.command("_elevated-helper", hidden=True)
def elevated_helper(
    request: str = typer.Option(..., "--request"),
    response: str = typer.Option(..., "--response"),
) -> None:
    """Internal entry point run inside the elevated (UAC) helper process."""
    from systemsieve.elevation.helper import run

    run(request, response)


def main() -> None:
    app()


if __name__ == "__main__":
    main()
