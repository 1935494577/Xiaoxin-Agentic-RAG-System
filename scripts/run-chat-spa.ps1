# Start Frontend SPA (port 8502) — unified chat + admin
$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
. (Join-Path $PSScriptRoot "_port_utils.ps1")

$SpaDir = Join-Path $Root "frontend"
$SpaPort = $script:DevSpaPort

Stop-PortListeners -Port $SpaPort -Label "Frontend SPA"

$npm = Get-DevNpmCmd
if (-not $npm) {
    Write-Error "npm.cmd not found. Install Node.js LTS (https://nodejs.org)."
}

if (-not (Test-Path (Join-Path $SpaDir "node_modules"))) {
    Push-Location $SpaDir
    & $npm install
    Pop-Location
}

Write-Host "Frontend SPA: http://127.0.0.1:$SpaPort  (管理后台: /admin/)"
Push-Location $SpaDir
try {
    & $npm run dev
} finally {
    Pop-Location
    Stop-PortListeners -Port $SpaPort -Label "Frontend SPA"
}
