# Run from repo root: pytest + FastAPI app import (uses PYTHONPATH=enterprise_rag/src).
$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

$VenvPy = Join-Path $Root ".venv\Scripts\python.exe"
if (-not (Test-Path $VenvPy)) {
    Write-Error "Missing .venv. Run: powershell -File scripts/bootstrap_venv.ps1"
    exit 1
}

$env:PYTHONPATH = "enterprise_rag/src"
& $VenvPy -m pytest tests/ -q
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

& $VenvPy -c "from api.main import app; print('api.main OK:', app.title)"
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "verify_env: OK"
