# Run from repo root: creates .venv-harness and installs agent harness from local checkout.
$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

$HarnessDefault = "D:\bytedance flow\deer-flow\backend\packages\harness"
$HarnessPath = if ($env:AGENT_HARNESS_PATH) { $env:AGENT_HARNESS_PATH } elseif ($env:DEER_FLOW_HARNESS_PATH) { $env:DEER_FLOW_HARNESS_PATH } else { $HarnessDefault }

if (-not (Test-Path $HarnessPath)) {
    Write-Error "Agent harness not found at $HarnessPath. Set AGENT_HARNESS_PATH."
    exit 1
}

$Venv = Join-Path $Root ".venv-harness"
if (-not (Test-Path (Join-Path $Venv "Scripts\python.exe"))) {
    python -m venv $Venv
}

$Py = Join-Path $Venv "Scripts\python.exe"
& $Py -m pip install -U pip
& $Py -m pip install -r (Join-Path $Root "requirements-harness.txt")
& $Py -m pip install -e $HarnessPath

$env:DEER_FLOW_PROJECT_ROOT = $Root
$env:DEER_FLOW_CONFIG_PATH = Join-Path $Root "config.yaml"
$env:DEER_FLOW_EXTENSIONS_CONFIG_PATH = Join-Path $Root "extensions_config.json"
$env:PYTHONPATH = Join-Path $Root "enterprise_rag\src"

if (-not $env:OPENAI_CHAT_MODEL) { $env:OPENAI_CHAT_MODEL = "gpt-4o-mini" }
if (-not $env:OPENAI_API_BASE) { $env:OPENAI_API_BASE = "http://127.0.0.1:9999/v1" }
if (-not $env:OPENAI_API_KEY) { $env:OPENAI_API_KEY = "test-key-for-harness-config" }

Write-Host "Running harness integration tests..."
& $Py -m pytest @(
    (Join-Path $Root "tests\test_harness_df0_config.py"),
    (Join-Path $Root "tests\test_harness_df3_tools.py")
) -m harness -q
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
Write-Host "bootstrap-harness-venv: OK"
