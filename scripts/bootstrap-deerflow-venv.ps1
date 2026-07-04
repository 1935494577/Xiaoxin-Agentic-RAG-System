# Run from repo root: creates .venv-deerflow and installs deerflow-harness from local checkout.
$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

$HarnessDefault = "D:\bytedance flow\deer-flow\backend\packages\harness"
$HarnessPath = if ($env:DEER_FLOW_HARNESS_PATH) { $env:DEER_FLOW_HARNESS_PATH } else { $HarnessDefault }

if (-not (Test-Path $HarnessPath)) {
    Write-Error "DeerFlow harness not found at $HarnessPath. Set DEER_FLOW_HARNESS_PATH."
    exit 1
}

$Venv = Join-Path $Root ".venv-deerflow"
if (-not (Test-Path (Join-Path $Venv "Scripts\python.exe"))) {
    python -m venv $Venv
}

$Py = Join-Path $Venv "Scripts\python.exe"
& $Py -m pip install -U pip
& $Py -m pip install -r (Join-Path $Root "requirements-deerflow.txt")
& $Py -m pip install -e $HarnessPath

$env:DEER_FLOW_PROJECT_ROOT = $Root
$env:DEER_FLOW_CONFIG_PATH = Join-Path $Root "config.yaml"
$env:DEER_FLOW_EXTENSIONS_CONFIG_PATH = Join-Path $Root "extensions_config.json"
$env:PYTHONPATH = Join-Path $Root "enterprise_rag\src"

Write-Host "Running DeerFlow DF-0 integration tests..."
& $Py -m pytest (Join-Path $Root "tests\test_deerflow_df0_config.py") -m deerflow -q
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
Write-Host "bootstrap-deerflow-venv: OK"
