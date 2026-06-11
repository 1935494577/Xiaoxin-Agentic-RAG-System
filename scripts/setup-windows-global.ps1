# Install Python 3.10+ globally, pytest, and prepare this repo (user PATH only; no HKLM registry).
# Run from repo root: powershell -ExecutionPolicy Bypass -File scripts/setup-windows-global.ps1
param(
    [string]$PythonVersion = "3.12",
    [switch]$SkipWingetInstall,
    [switch]$SkipGlobalPytest,
    [switch]$SkipVenvBootstrap
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

function Test-RealPython {
    param([string]$Exe)
    if (-not (Test-Path $Exe)) { return $false }
    if ($Exe -like "*\WindowsApps\*") { return $false }
  try {
        $ver = & $Exe -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')" 2>$null
        if (-not $ver) { return $false }
        $parts = $ver.Trim().Split(".")
        $major = [int]$parts[0]
        $minor = [int]$parts[1]
        return ($major -ge 3 -and $minor -ge 10)
    } catch {
        return $false
    }
}

function Find-PythonExe {
    $candidates = @()
    if ($env:LOCALAPPDATA) {
        $candidates += Get-ChildItem -Path (Join-Path $env:LOCALAPPDATA "Programs\Python\Python*\python.exe") -ErrorAction SilentlyContinue
    }
    $candidates += @(
        "$env:ProgramFiles\Python312\python.exe",
        "$env:ProgramFiles\Python311\python.exe",
        "$env:ProgramFiles\Python310\python.exe"
    )
    foreach ($path in $candidates) {
        if (Test-RealPython $path) { return $path }
    }
    $cmd = Get-Command python -ErrorAction SilentlyContinue
    if ($cmd -and (Test-RealPython $cmd.Source)) { return $cmd.Source }
    return $null
}

function Ensure-UserPathContains {
    param([string[]]$Dirs)
    $userPath = [Environment]::GetEnvironmentVariable("Path", "User")
    if (-not $userPath) { $userPath = "" }
    $segments = $userPath -split ";" | Where-Object { $_ }
    foreach ($dir in $Dirs) {
        if (-not $dir -or -not (Test-Path $dir)) { continue }
        if ($segments -notcontains $dir) {
            $segments += $dir
            Write-Host "Adding to user PATH: $dir"
        }
    }
    $newPath = ($segments -join ";")
    if ($newPath -ne $userPath) {
        [Environment]::SetEnvironmentVariable("Path", $newPath, "User")
        $env:Path = $newPath + ";" + [Environment]::GetEnvironmentVariable("Path", "Machine")
    }
}

Write-Host "=== Enterprise RAG: Windows global Python setup ==="

$Py = Find-PythonExe
if (-not $Py -and -not $SkipWingetInstall) {
    $pkg = "Python.Python.$PythonVersion"
    Write-Host "Python 3.10+ not found. Installing $pkg via winget..."
    winget install --id $pkg -e --accept-package-agreements --accept-source-agreements
    $Py = Find-PythonExe
}

if (-not $Py) {
    Write-Error @"
Python 3.10+ not found.
Install manually:
  winget install --id Python.Python.3.12 -e --accept-package-agreements --accept-source-agreements
Or download: https://www.python.org/downloads/windows/ (check 'Add python.exe to PATH').
Then re-run this script.
"@
    exit 1
}

Write-Host "Using Python: $Py"
& $Py --version

$PyDir = Split-Path -Parent $Py
$ScriptsDir = Join-Path $PyDir "Scripts"
Ensure-UserPathContains @($PyDir, $ScriptsDir)

& $Py -m pip install --upgrade pip
if (-not $SkipGlobalPytest) {
    Write-Host "Installing pytest globally..."
    & $Py -m pip install pytest
}

$envFile = Join-Path $Root ".env"
$envExample = Join-Path $Root ".env.example"
if (-not (Test-Path $envFile) -and (Test-Path $envExample)) {
    Copy-Item $envExample $envFile
    Write-Host "Created .env from .env.example — edit API keys before running API."
}

if (-not $SkipVenvBootstrap) {
    Write-Host "Creating project .venv and installing requirements (torch, FlagEmbedding, etc.)..."
    & $Py -m venv (Join-Path $Root ".venv")
    $VenvPy = Join-Path $Root ".venv\Scripts\python.exe"
    & $VenvPy -m pip install --upgrade pip
    & $VenvPy -m pip install -r (Join-Path $Root "requirements.txt") `
        -i https://pypi.tuna.tsinghua.edu.cn/simple --trusted-host pypi.tuna.tsinghua.edu.cn
}

Write-Host ""
Write-Host "=== Verify (new shell after PATH update) ==="
Write-Host "  python --version"
Write-Host "  pytest --version"
Write-Host "  powershell -File scripts/verify_env.ps1"
Write-Host ""
Write-Host "Project PYTHONPATH (tests / manual runs): enterprise_rag/src"
Write-Host "Heavy ML deps stay in .venv — recommended even with global Python."
