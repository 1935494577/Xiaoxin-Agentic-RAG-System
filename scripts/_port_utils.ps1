# Shared port / process cleanup for local dev (Windows PowerShell).

$ErrorActionPreference = "SilentlyContinue"

$script:DevApiPort = 8010
$script:DevFrontendPort = 8501

function Stop-ProcessTree {
    param([Parameter(Mandatory)][int]$ProcessId)
    if ($ProcessId -le 0) { return }
    & taskkill.exe /PID $ProcessId /T /F 2>$null | Out-Null
}

function Get-PortListenerPids {
    param([Parameter(Mandatory)][int]$Port)
    $pids = @(
        Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue |
            Select-Object -ExpandProperty OwningProcess -Unique
    )
    return @($pids | Where-Object { $_ -gt 0 } | Select-Object -Unique)
}

function Stop-PortListeners {
    param(
        [Parameter(Mandatory)][int]$Port,
        [string]$Label = ""
    )
    $name = if ($Label) { $Label } else { "port $Port" }
    $pids = Get-PortListenerPids -Port $Port
    if (-not $pids -or $pids.Count -eq 0) {
        return
    }
    foreach ($procId in $pids) {
        Stop-ProcessTree -ProcessId $procId
    }
    Start-Sleep -Milliseconds 300
    Write-Host "Released $name (port $Port)."
}

function Stop-DevPorts {
    Stop-PortListeners -Port $script:DevApiPort -Label "API"
    Stop-PortListeners -Port $script:DevFrontendPort -Label "Streamlit frontend"
}

function Register-DevPortCleanup {
    param([Parameter(Mandatory)][int]$Port, [string]$Label = "")
    if ($script:DevCleanupRegistered) { return }
    $script:DevCleanupRegistered = $true
    $utilsPath = Join-Path $PSScriptRoot "_port_utils.ps1"

    Register-EngineEvent -SourceIdentifier PowerShell.Exiting -Action {
        . $using:utilsPath
        Stop-PortListeners -Port $using:Port -Label $using:Label
    } | Out-Null
}

function Invoke-DevService {
    param(
        [Parameter(Mandatory)][int]$Port,
        [Parameter(Mandatory)][string]$Label,
        [Parameter(Mandatory)][scriptblock]$Run
    )
    Stop-PortListeners -Port $Port -Label $Label
    Register-DevPortCleanup -Port $Port -Label $Label
    try {
        & $Run
    } finally {
        Stop-PortListeners -Port $Port -Label $Label
    }
}

function Get-DevPython {
    $root = Split-Path -Parent $PSScriptRoot
    $venvPy = Join-Path $root ".venv\Scripts\python.exe"
    if (Test-Path $venvPy) { return $venvPy }
    return "python"
}

function Get-UvicornReloadArgs {
    param([string]$SrcDir)
    # 仅监视 Python 源码；排除 data/models 等大目录，避免误触发
    return @(
        "--reload"
        "--reload-dir", $SrcDir
        "--reload-delay", "0.4"
        "--reload-exclude", "data"
        "--reload-exclude", "*/data/*"
        "--reload-exclude", "*__pycache__*"
        "--reload-exclude", "*.pyc"
    )
}
