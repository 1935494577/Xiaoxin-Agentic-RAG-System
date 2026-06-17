# Start API + Frontend for LAN access (same office network, no cloud server).
# Your PC stays on; colleagues open http://<your-LAN-IP>:8502
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
    "--host", "0.0.0.0", "--port", "$ApiPort"
)
if (-not $NoReload) {
    $apiArgs += Get-UvicornReloadArgs -SrcDir $Src
}

Write-Host "Starting API on 0.0.0.0:$ApiPort (LAN + localhost)..."
$apiProc = Start-Process -FilePath $Py -ArgumentList $apiArgs -WorkingDirectory $Src -PassThru -WindowStyle Normal

Wait-Api

$spaProc = $null
if (-not $NoSpa) {
    $npm = Get-DevNpmCmd
    if (-not $npm) {
        Write-Host "WARN: npm.cmd not found — skip Frontend SPA."
    } else {
        $nodeModules = Join-Path $SpaDir "node_modules"
        if (-not (Test-Path $nodeModules)) {
            Write-Host "Installing Frontend SPA dependencies..."
            Push-Location $SpaDir
            & $npm install
            Pop-Location
        }
        Write-Host "Starting Frontend SPA on 0.0.0.0:$SpaPort ..."
        $env:VITE_DEV_HOST = "0.0.0.0"
        $spaProc = Start-Process -FilePath $npm -ArgumentList @("run", "dev") -WorkingDirectory $SpaDir -PassThru -WindowStyle Normal
        Start-Sleep -Seconds 3
    }
}

Write-Host ""
Write-Host "  >>> You (this PC):     http://127.0.0.1:$SpaPort" -ForegroundColor Green
Write-Host "  >>> Colleagues (LAN):  http://${LanIp}:$SpaPort" -ForegroundColor Cyan
Write-Host "  >>> Admin:             http://${LanIp}:$SpaPort/admin/" -ForegroundColor Cyan
Write-Host "  API (direct):          http://${LanIp}:$ApiPort"
Write-Host ""
Write-Host "If colleagues cannot connect, allow inbound TCP $SpaPort (and $ApiPort) in Windows Firewall."
Write-Host "Keep this PC awake; stop with Ctrl+C here."
Write-Host ""

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
