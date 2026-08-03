# Runs the quality gates: lint, format check, type check, and the automated
# (non-destructive, non-manual) test suite.
#
# Usage: .\scripts\test.ps1

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

$venvPython = Join-Path $root ".venv\Scripts\python.exe"
if (-not (Test-Path $venvPython)) {
    $venvPython = "python"
}

function Invoke-CheckedPython {
    param([Parameter(ValueFromRemainingArguments = $true)][string[]]$Arguments)
    & $venvPython @Arguments
    if ($LASTEXITCODE -ne 0) {
        throw "Python command failed with exit code $LASTEXITCODE`: python $($Arguments -join ' ')"
    }
}

Write-Host "Running ruff check..."
Invoke-CheckedPython -m ruff check .

Write-Host "Running ruff format --check..."
Invoke-CheckedPython -m ruff format --check .

Write-Host "Running mypy..."
Invoke-CheckedPython -m mypy src

Write-Host "Running pytest (excluding manual/destructive tests)..."
Invoke-CheckedPython -m pytest -m "not manual and not destructive" --cov=systemsieve

Write-Host "All checks passed."
