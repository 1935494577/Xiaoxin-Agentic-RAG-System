$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
. (Join-Path $PSScriptRoot "_port_utils.ps1")

$Port = $script:DevApiPort
$Py = Get-DevPython
$Src = Join-Path $Root "enterprise_rag\src"

Invoke-DevService -Port $Port -Label "API" -Run {
    Set-Location $Src
    Write-Host "API: http://127.0.0.1:$Port  (Ctrl+C to stop and release port)"
    & $Py -m uvicorn api.main:app --host 127.0.0.1 --port $Port @args
}
