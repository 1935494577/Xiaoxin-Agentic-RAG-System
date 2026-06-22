# Expose FastAPI (Chat RAG backend) on LAN — colleagues call http://<your-IP>:8010 directly.
# No frontend required; use POST /chat or POST /chat/stream from their own client.
param(
    [switch]$NoReload,
    [switch]$OpenFirewall,
    [switch]$KbOnly
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
. (Join-Path $PSScriptRoot "_port_utils.ps1")
$ErrorActionPreference = "Stop"

if ($KbOnly) {
    $Py = Get-DevPython
    Write-Host "Ensuring server KB-only defaults (hybrid/general fallback off in ui_config)..."
    & $Py (Join-Path $PSScriptRoot "ensure_kb_only_ui.py")
}

$Port = $script:DevApiPort
$Py = Get-DevPython
$Src = Join-Path $Root "enterprise_rag\src"

function Get-LanIPv4 {
    $addrs = @(
        Get-NetIPAddress -AddressFamily IPv4 -ErrorAction SilentlyContinue |
            Where-Object {
                $_.IPAddress -notlike "127.*" -and
                $_.PrefixOrigin -ne "WellKnown"
            } |
            Sort-Object -Property InterfaceMetric
    )
    if ($addrs) { return $addrs[0].IPAddress }
    return "127.0.0.1"
}

$LanIp = Get-LanIPv4

if ($OpenFirewall) {
    $fwScript = Join-Path $PSScriptRoot "open-lan-firewall.ps1"
    try {
        & $fwScript -ChatPort 0 -ApiPort $Port -ApiOnly
    } catch {
        Write-Host "WARN: firewall rule not added — $_" -ForegroundColor Yellow
    }
    if ($LASTEXITCODE -ne 0) {
        Write-Host "WARN: run as Administrator: .\scripts\open-lan-firewall.ps1 -ApiOnly" -ForegroundColor Yellow
    }
}

Stop-DevPorts

function Wait-Api {
    $url = "http://127.0.0.1:$Port/health"
    $max = 45
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
    Write-Host "WARN: API not reachable after ${max}s — check the API window for errors."
}

$apiArgs = @(
    "-m", "uvicorn", "api.main:app",
    "--host", "0.0.0.0", "--port", "$Port"
)
if (-not $NoReload) {
    $apiArgs += Get-UvicornReloadArgs -SrcDir $Src
}

Write-Host ""
Write-Host "========== RAG API (LAN) ==========" -ForegroundColor Green
Write-Host "  Bind: 0.0.0.0:$Port"
Write-Host "  You:        http://127.0.0.1:$Port" -ForegroundColor Green
Write-Host "  Colleagues: http://${LanIp}:$Port" -ForegroundColor Cyan
Write-Host ""
Write-Host "  Health:  GET  /health"
Write-Host "  Chat:    POST /chat"
Write-Host "  Stream:  POST /chat/stream  (SSE)"
Write-Host "  Docs:    http://127.0.0.1:$Port/docs  (if enabled)"
Write-Host ""
Write-Host "  See docs/lan_api_chat.md for request JSON examples."
if (-not $OpenFirewall) {
    Write-Host "  Firewall: Admin: .\scripts\open-lan-firewall.ps1 -ApiOnly" -ForegroundColor Yellow
}
Write-Host ""
Write-Host "Starting API (keep this window open)..."
Write-Host ""

$apiProc = Start-Process -FilePath $Py -ArgumentList $apiArgs -WorkingDirectory $Src -PassThru -WindowStyle Normal

Wait-Api

Write-Host ""
Write-Host "Verify LAN bind: netstat -ano | findstr :$Port"
Write-Host "  expect: 0.0.0.0:$Port  LISTENING"
Write-Host ""
Write-Host "Press Ctrl+C here to stop API."

$utilsPath = Join-Path $PSScriptRoot "_port_utils.ps1"
Register-EngineEvent -SourceIdentifier PowerShell.Exiting -Action {
    . $using:utilsPath
    Stop-DevPorts
} | Out-Null

try {
    while ($true) {
        if ($apiProc.HasExited) {
            Write-Host "API process exited (code $($apiProc.ExitCode)). See the API window for errors." -ForegroundColor Red
            break
        }
        Start-Sleep -Seconds 1
    }
} finally {
    if (-not $apiProc.HasExited) {
        Stop-ProcessTree -ProcessId $apiProc.Id
    }
    Stop-DevPorts
}
