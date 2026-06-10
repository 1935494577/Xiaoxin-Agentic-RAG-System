# Start API + Chat SPA + Streamlit admin
param(
    [switch]$NoReload,
    [switch]$NoChatSpa,
    [switch]$NoAdmin
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
. (Join-Path $PSScriptRoot "_port_utils.ps1")

$Py = Get-DevPython
$ApiPort = $script:DevApiPort
$AdminPort = $script:DevFrontendPort
$ChatPort = $script:DevChatSpaPort
$Src = Join-Path $Root "enterprise_rag\src"
$ChatDir = Join-Path $Root "web\chat"

Stop-DevPorts

$apiArgs = @(
    "-m", "uvicorn", "api.main:app",
    "--host", "127.0.0.1", "--port", "$ApiPort"
)
if (-not $NoReload) {
    $apiArgs += Get-UvicornReloadArgs -SrcDir $Src
}

Write-Host "Starting API on port $ApiPort..."
$apiProc = Start-Process -FilePath $Py -ArgumentList $apiArgs -WorkingDirectory $Src -PassThru -WindowStyle Normal

Start-Sleep -Seconds 2

$chatProc = $null
if (-not $NoChatSpa) {
    $chatProc = Start-DevChatSpa -ChatDir $ChatDir -Port $ChatPort
}

$adminProc = $null
if (-not $NoAdmin) {
    Write-Host "Starting Streamlit admin on port $AdminPort..."
    $adminProc = Start-Process -FilePath $Py -ArgumentList @(
        "-m", "streamlit", "run", "frontend/streamlit_app.py",
        "--server.port", "$AdminPort",
        "--server.runOnSave", "true"
    ) -WorkingDirectory $Root -PassThru -WindowStyle Normal
}

Write-Host ""
Write-Host "  >>> Jnao Chat:      http://127.0.0.1:$ChatPort"
Write-Host "  API:              http://127.0.0.1:$ApiPort"
if ($adminProc) { Write-Host "  管理后台:         http://127.0.0.1:$AdminPort" }
Write-Host ""
Write-Host "Press Ctrl+C here to stop all services."

$utilsPath = Join-Path $PSScriptRoot "_port_utils.ps1"
Register-EngineEvent -SourceIdentifier PowerShell.Exiting -Action {
    . $using:utilsPath
    Stop-DevPorts
} | Out-Null

try {
    while ($true) {
        $alive = @($apiProc, $chatProc, $adminProc) | Where-Object { $_ -and -not $_.HasExited }
        if (-not $alive) { break }
        Start-Sleep -Seconds 1
    }
} finally {
    foreach ($p in @($apiProc, $chatProc, $adminProc)) {
        if ($p -and -not $p.HasExited) {
            Stop-ProcessTree -ProcessId $p.Id
        }
    }
    Stop-DevPorts
}
