# Start API + Frontend for LAN access (same office network, no cloud server).
# Colleagues open http://<your-LAN-IP>:8502 — Chat uses Vite proxy to API on this PC.
param(
    [switch]$NoReload,
    [switch]$NoSpa,
    [switch]$OpenFirewall,
    [switch]$KbOnly
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
. (Join-Path $PSScriptRoot "_port_utils.ps1")

if ($KbOnly) {
    $Py = Get-DevPython
    Write-Host "Ensuring KB-only Chat settings (hybrid/general fallback off)..."
    & $Py (Join-Path $PSScriptRoot "ensure_kb_only_ui.py")
}

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

if ($OpenFirewall) {
    $fwScript = Join-Path $PSScriptRoot "open-lan-firewall.ps1"
    & $fwScript -ChatPort $SpaPort -ChatOnly
}

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
Write-Host "========== Jnao Chat (LAN) ==========" -ForegroundColor Green
if ($KbOnly) {
    Write-Host "  Mode: 知识库专用（不启用混合专家 / 通用兜底）" -ForegroundColor Green
} else {
    Write-Host "  Mode: 跟随 ui_config（建议 LAN 演示用 -KbOnly）" -ForegroundColor Yellow
}
Write-Host ""
Write-Host "  >>> You (this PC):     http://127.0.0.1:$SpaPort" -ForegroundColor Green
Write-Host "  >>> Colleagues (LAN):  http://${LanIp}:$SpaPort" -ForegroundColor Cyan
Write-Host ""
Write-Host "  同事：浏览器打开上面 LAN 地址 → 登录选部门 → 直接提问（仅检索本机知识库）"
Write-Host "  管理后台（请勿分享给同事）: http://${LanIp}:$SpaPort/admin/"
Write-Host ""
Write-Host "  API (direct): http://${LanIp}:$ApiPort"
Write-Host ""
if (-not $OpenFirewall) {
    Write-Host "  若同事连不上：以管理员运行 .\scripts\open-lan-firewall.ps1" -ForegroundColor Yellow
    Write-Host "  或：.\scripts\run-dev-lan.ps1 -OpenFirewall -KbOnly" -ForegroundColor Yellow
}
Write-Host "  保持本机不休眠；在此窗口 Ctrl+C 停止服务。"
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
