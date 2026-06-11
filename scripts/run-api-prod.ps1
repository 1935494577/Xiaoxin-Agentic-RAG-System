param(
    [int]$Port = 8010,
    [string]$BindHost = "0.0.0.0"
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
. (Join-Path $PSScriptRoot "_port_utils.ps1")

$Py = Get-DevPython
$Src = Join-Path $Root "enterprise_rag\src"

Invoke-DevService -Port $Port -Label "API (production)" -Run {
    Set-Location $Src
    Write-Host "Production API: http://$($using:BindHost):$($using:Port)  (no reload, workers=1)"
    Write-Host "See docs/production_deploy.md for .env and Redis setup."
    & $using:Py -m uvicorn api.main:app `
        --host $using:BindHost `
        --port $using:Port `
        --proxy-headers `
        --forwarded-allow-ips 127.0.0.1
}
