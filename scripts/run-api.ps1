$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
Set-Location (Join-Path $Root "enterprise_rag\src")
python -m uvicorn api.main:app --reload --port 8000 @args
