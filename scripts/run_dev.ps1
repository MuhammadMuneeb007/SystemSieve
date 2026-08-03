# Sets up (if needed) and activates a local development environment, then
# launches the SystemSieve GUI from source.
#
# Usage: .\scripts\run_dev.ps1

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

if (-not (Test-Path ".venv")) {
    Write-Host "Creating virtual environment at .venv ..."
    python -m venv .venv
}

$venvPython = Join-Path $root ".venv\Scripts\python.exe"

Write-Host "Installing SystemSieve in editable mode with dev dependencies..."
& $venvPython -m pip install --upgrade pip
& $venvPython -m pip install -e ".[dev]"

Write-Host "Launching SystemSieve GUI..."
& $venvPython -m systemsieve gui
