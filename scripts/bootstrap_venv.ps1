# Create .venv at repo root and install requirements (isolates LangChain from global Python).
$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

$VenvPy = Join-Path $Root ".venv\Scripts\python.exe"
if (-not (Test-Path $VenvPy)) {
    python -m venv .venv
}
& $VenvPy -m pip install --upgrade pip
& $VenvPy -m pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple --trusted-host pypi.tuna.tsinghua.edu.cn

Write-Host "Done. Activate: .\.venv\Scripts\Activate.ps1"
