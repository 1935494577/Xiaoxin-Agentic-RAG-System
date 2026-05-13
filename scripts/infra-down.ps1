$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
    Write-Host "No Docker CLI; plan1 local mode has nothing to stop."
    exit 0
}

docker compose -f docker-compose.yml down --remove-orphans @args
