# Dev stack: Main RAG API (8010) + Harness Gateway (8011) + Frontend (8502)
param(
    [switch]$NoReload,
    [switch]$NoSpa,
    [switch]$SkipBootstrapCheck
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
. (Join-Path $PSScriptRoot "_harness_env.ps1")
. (Join-Path $PSScriptRoot "_port_utils.ps1")

$ApiPort = $script:DevApiPort
$GatewayPort = 8011
$SpaPort = $script:DevSpaPort
$MainPy = Get-DevPython
$HarnessPy = Get-HarnessPython
$Src = Join-Path $Root "enterprise_rag\src"
$SpaDir = Join-Path $Root "frontend"

if (-not $SkipBootstrapCheck -and -not (Test-HarnessReady)) {
    Write-Host "Harness venv not ready — running bootstrap..."
    & (Join-Path $PSScriptRoot "bootstrap-harness-venv.ps1")
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
}

Stop-DevPorts
Stop-PortListeners -Port $GatewayPort -Label "Harness Gateway"

Set-HarnessEnv -GatewayPort $GatewayPort

function Wait-Http {
    param([string]$Url, [string]$Label, [int]$Max = 45)
    for ($i = 0; $i -lt $Max; $i++) {
        try {
            $r = Invoke-WebRequest -Uri $Url -UseBasicParsing -TimeoutSec 2 -ErrorAction Stop
            if ($r.StatusCode -eq 200) {
                Write-Host "  $Label ready ($Url)"
                return
            }
        } catch {}
        Start-Sleep -Seconds 1
    }
    Write-Host "WARN: $Label not reachable after ${Max}s ($Url)"
}

# --- Harness Gateway (8011) ---
$gwArgs = @("-m", "uvicorn", "harness_gateway:app", "--host", "127.0.0.1", "--port", "$GatewayPort")
if (-not $NoReload) {
    $gwArgs += Get-UvicornReloadArgs -SrcDir $Src
}
Write-Host "Starting Harness Gateway on $GatewayPort..."
$gwProc = Start-Process -FilePath $HarnessPy -ArgumentList $gwArgs -WorkingDirectory $Src -PassThru -WindowStyle Normal
Wait-Http -Url "http://127.0.0.1:$GatewayPort/health" -Label "Harness Gateway"

# --- Main RAG API (8010) ---
$apiArgs = @("-m", "uvicorn", "api.main:app", "--host", "127.0.0.1", "--port", "$ApiPort")
if (-not $NoReload) {
    $apiArgs += Get-UvicornReloadArgs -SrcDir $Src
}
Write-Host "Starting Main API on $ApiPort..."
$apiProc = Start-Process -FilePath $MainPy -ArgumentList $apiArgs -WorkingDirectory $Src -PassThru -WindowStyle Normal
Wait-Http -Url "http://127.0.0.1:$ApiPort/health" -Label "Main API"

$spaProc = $null
if (-not $NoSpa) {
    $spaProc = Start-DevSpa -SpaDir $SpaDir -Port $SpaPort
}

Write-Host ""
Write-Host "  >>> Frontend:         http://127.0.0.1:$SpaPort"
Write-Host "  >>> Admin / Chat:     http://127.0.0.1:$SpaPort/admin/"
Write-Host "  Main RAG API:        http://127.0.0.1:$ApiPort"
Write-Host "  Harness Gateway:     http://127.0.0.1:$GatewayPort  (IM Worker + LangGraph)"
Write-Host "  Channels (Worker):   http://127.0.0.1:$GatewayPort/api/channels/"
Write-Host ""
Write-Host "Press Ctrl+C to stop all."

try {
    while ($true) {
        $alive = @($apiProc, $gwProc, $spaProc) | Where-Object { $_ -and -not $_.HasExited }
        if (-not $alive) { break }
        Start-Sleep -Seconds 1
    }
} finally {
    foreach ($p in @($apiProc, $gwProc, $spaProc)) {
        if ($p -and -not $p.HasExited) {
            Stop-ProcessTree -ProcessId $p.Id
        }
    }
    Stop-DevPorts
    Stop-PortListeners -Port $GatewayPort -Label "Harness Gateway"
}
