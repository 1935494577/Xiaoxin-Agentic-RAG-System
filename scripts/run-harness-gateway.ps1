# Harness Gateway (DeerFlow LangGraph + IM channel worker) on port 8011.
param(
    [switch]$NoReload,
    [int]$Port = 8011
)

$ErrorActionPreference = "Stop"
. (Join-Path $PSScriptRoot "_harness_env.ps1")
. (Join-Path $PSScriptRoot "_port_utils.ps1")

$Root = Get-HarnessRoot
$Py = Get-HarnessPython
$Src = Join-Path $Root "enterprise_rag\src"

Set-HarnessEnv -GatewayPort $Port

if (-not (Test-HarnessReady)) {
    Write-Error "Harness venv incomplete. Run: .\scripts\bootstrap-harness-venv.ps1"
    exit 1
}

function Wait-Gateway {
    $url = "http://127.0.0.1:$Port/health"
    for ($i = 0; $i -lt 45; $i++) {
        try {
            $r = Invoke-WebRequest -Uri $url -UseBasicParsing -TimeoutSec 2 -ErrorAction Stop
            if ($r.StatusCode -eq 200) {
                Write-Host "  Harness Gateway ready ($url)"
                return
            }
        } catch {}
        Start-Sleep -Seconds 1
    }
    Write-Host "WARN: Harness Gateway not reachable after 45s at $url"
}

Stop-PortListeners -Port $Port -Label "Harness Gateway"

$uvicornArgs = @(
    "-m", "uvicorn", "harness_gateway:app",
    "--host", "127.0.0.1", "--port", "$Port"
)
if (-not $NoReload) {
    $uvicornArgs += Get-UvicornReloadArgs -SrcDir $Src
}

Write-Host "Starting Harness Gateway on port $Port (channel worker + LangGraph /api)..."
Write-Host "  Config: $env:DEER_FLOW_CONFIG_PATH"
Write-Host "  Python: $Py"

Push-Location $Src
try {
    $proc = Start-Process -FilePath $Py -ArgumentList $uvicornArgs -WorkingDirectory $Src -PassThru -WindowStyle Normal
} finally {
    Pop-Location
}

Wait-Gateway

Write-Host ""
Write-Host "  Harness Gateway:  http://127.0.0.1:$Port"
Write-Host "  Channels status:  http://127.0.0.1:$Port/api/channels/"
Write-Host "  LangGraph API:    http://127.0.0.1:$Port/api"
Write-Host ""
Write-Host "Press Ctrl+C to stop."

try {
    while (-not $proc.HasExited) {
        Start-Sleep -Seconds 1
    }
} finally {
    if (-not $proc.HasExited) {
        Stop-ProcessTree -ProcessId $proc.Id
    }
    Stop-PortListeners -Port $Port -Label "Harness Gateway"
}
