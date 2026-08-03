# Builds a standalone Windows distribution of SystemSieve with PyInstaller.
#
# Output: dist\SystemSieve\SystemSieve.exe (one-folder distribution).
# This build is NOT code-signed. See docs/release.md before distributing it.
#
# Usage: .\scripts\build_windows.ps1

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

$venvPython = Join-Path $root ".venv\Scripts\python.exe"
if (-not (Test-Path $venvPython)) {
    Write-Host "No .venv found; creating one..."
    python -m venv .venv
    & $venvPython -m pip install --upgrade pip
    & $venvPython -m pip install -e ".[dev]"
}

Write-Host "Cleaning previous build artifacts..."
Remove-Item -Recurse -Force -ErrorAction SilentlyContinue "$root\build"
Remove-Item -Recurse -Force -ErrorAction SilentlyContinue "$root\dist"

Write-Host "Running PyInstaller..."
& $venvPython -m PyInstaller "packaging\systemsieve.spec" --noconfirm
if ($LASTEXITCODE -ne 0) {
    throw "PyInstaller failed with exit code $LASTEXITCODE"
}

Write-Host ""
Write-Host "Build complete: dist\SystemSieve\SystemSieve.exe"
Write-Host "This build is unsigned. Do not distribute it publicly without code-signing"
Write-Host "and without testing it in a virtual machine first (see docs/testing.md)."
