# Start Chat SPA only (port 8502)
$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
. (Join-Path $PSScriptRoot "_port_utils.ps1")

$ChatDir = Join-Path $Root "web\chat"
$ChatPort = $script:DevChatSpaPort

Stop-PortListeners -Port $ChatPort -Label "Chat SPA"

if (-not (Get-Command npm -ErrorAction SilentlyContinue)) {
    Write-Error "npm not found. Install Node.js first."
}

if (-not (Test-Path (Join-Path $ChatDir "node_modules"))) {
    Push-Location $ChatDir
    npm install
    Pop-Location
}

Write-Host "Chat SPA: http://127.0.0.1:$ChatPort"
Push-Location $ChatDir
try {
    npm run dev
} finally {
    Pop-Location
    Stop-PortListeners -Port $ChatPort -Label "Chat SPA"
}
