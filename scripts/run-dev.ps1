# Start API + Streamlit with hot reload; Ctrl+C stops both and releases ports.
param(
    [switch]$NoReload
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
. (Join-Path $PSScriptRoot "_port_utils.ps1")

$Py = Get-DevPython
$ApiPort = $script:DevApiPort
$FePort = $script:DevFrontendPort
$Src = Join-Path $Root "enterprise_rag\src"

Stop-DevPorts

$apiArgs = @(
    "-m", "uvicorn", "api.main:app",
    "--host", "127.0.0.1", "--port", "$ApiPort"
)
if (-not $NoReload) {
    $apiArgs += Get-UvicornReloadArgs -SrcDir $Src
}

Write-Host "Starting API on port $ApiPort $(if (-not $NoReload) { '(hot reload)' } else { '' })..."
$apiProc = Start-Process -FilePath $Py -ArgumentList $apiArgs -WorkingDirectory $Src -PassThru -WindowStyle Normal

Start-Sleep -Seconds 2

Write-Host "Starting Streamlit on port $FePort (run on save) ..."
$feProc = Start-Process -FilePath $Py -ArgumentList @(
    "-m", "streamlit", "run", "frontend/streamlit_app.py",
    "--server.port", "$FePort",
    "--server.runOnSave", "true"
) -WorkingDirectory $Root -PassThru -WindowStyle Normal

Write-Host ""
Write-Host "  API:      http://127.0.0.1:$ApiPort"
Write-Host "  Frontend: http://127.0.0.1:$FePort"
Write-Host ""
if (-not $NoReload) {
    Write-Host "  Hot reload: API watches enterprise_rag/src; frontend refreshes on save."
    Write-Host "  Disable:    .\scripts\run-dev.ps1 -NoReload"
    Write-Host ""
}
Write-Host "Press Ctrl+C here to stop both services and release ports."

$utilsPath = Join-Path $PSScriptRoot "_port_utils.ps1"
Register-EngineEvent -SourceIdentifier PowerShell.Exiting -Action {
    . $using:utilsPath
    Stop-DevPorts
} | Out-Null

try {
    while ($true) {
        if ($apiProc.HasExited -and $feProc.HasExited) { break }
        Start-Sleep -Seconds 1
    }
} finally {
    foreach ($p in @($apiProc, $feProc)) {
        if ($p -and -not $p.HasExited) {
            Stop-ProcessTree -ProcessId $p.Id
        }
    }
    Stop-DevPorts
}
