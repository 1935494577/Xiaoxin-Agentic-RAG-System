# Start API + Frontend SPA
param(
    [switch]$NoReload,
    [switch]$NoSpa
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
. (Join-Path $PSScriptRoot "_port_utils.ps1")

$Py = Get-DevPython
$ApiPort = $script:DevApiPort
$SpaPort = $script:DevSpaPort
$Src = Join-Path $Root "enterprise_rag\src"
$SpaDir = Join-Path $Root "frontend"

Stop-DevPorts

function Wait-Api {
    $url = "http://127.0.0.1:$ApiPort/health"
    $max = 30
    for ($i = 0; $i -lt $max; $i++) {
        try {
            $r = Invoke-WebRequest -Uri $url -UseBasicParsing -TimeoutSec 2 -ErrorAction Stop
            if ($r.StatusCode -eq 200) {
                Write-Host "  API ready ($url)"
                return
            }
        } catch {}
        Start-Sleep -Seconds 1
    }
    Write-Host "WARN: API not reachable after ${max}s — continuing anyway"
}

$apiArgs = @(
    "-m", "uvicorn", "api.main:app",
    "--host", "127.0.0.1", "--port", "$ApiPort"
)
if (-not $NoReload) {
    $apiArgs += Get-UvicornReloadArgs -SrcDir $Src
}

Write-Host "Starting API on port $ApiPort..."
$apiProc = Start-Process -FilePath $Py -ArgumentList $apiArgs -WorkingDirectory $Src -PassThru -WindowStyle Normal

Wait-Api

$spaProc = $null
if (-not $NoSpa) {
    $spaProc = Start-DevSpa -SpaDir $SpaDir -Port $SpaPort
}

Write-Host ""
Write-Host "  >>> Frontend:  http://127.0.0.1:$SpaPort"
Write-Host "  >>> 管理后台:  http://127.0.0.1:$SpaPort/admin/"
Write-Host "  API:           http://127.0.0.1:$ApiPort"
Write-Host ""
Write-Host "Press Ctrl+C here to stop all services."

$utilsPath = Join-Path $PSScriptRoot "_port_utils.ps1"
Register-EngineEvent -SourceIdentifier PowerShell.Exiting -Action {
    . $using:utilsPath
    Stop-DevPorts
} | Out-Null

try {
    while ($true) {
        $alive = @($apiProc, $spaProc) | Where-Object { $_ -and -not $_.HasExited }
        if (-not $alive) { break }
        Start-Sleep -Seconds 1
    }
} finally {
    foreach ($p in @($apiProc, $spaProc)) {
        if ($p -and -not $p.HasExited) {
            Stop-ProcessTree -ProcessId $p.Id
        }
    }
    Stop-DevPorts
}
