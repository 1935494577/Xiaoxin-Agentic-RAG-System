# Start optional Docker infra for Jnao.
# Usage:
#   .\scripts\infra-up.ps1              # Redis (default)
#   .\scripts\infra-up.ps1 cache
#   .\scripts\infra-up.ps1 db
#   .\scripts\infra-up.ps1 legacy
#   .\scripts\infra-up.ps1 app
# See docs/external-dependencies.md

[CmdletBinding()]
param(
    [Parameter(Position = 0)]
    [ValidateSet("cache", "db", "legacy", "app")]
    [string]$Profile = "cache"
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
    Write-Host "ERROR: 'docker' command not found."
    Write-Host ""
    Write-Host "Default dev uses Milvus Lite + local BM25 — Docker is optional."
    Write-Host "External deps: docs/external-dependencies.md"
    Write-Host ""
    Write-Host "Examples after installing Docker Desktop:"
    Write-Host "  .\scripts\infra-up.ps1 cache     # Redis"
    Write-Host "  .\scripts\infra-up.ps1 db        # PostgreSQL"
    Write-Host "  .\scripts\infra-up.ps1 legacy    # remote Milvus + ES"
    Write-Host ""
    Write-Host "Docker Desktop: https://docs.docker.com/desktop/setup/install/windows-install/"
    exit 1
}

Write-Host "Starting Docker Compose profile: $Profile ..."
Write-Host "See docs/external-dependencies.md for REDIS_URL / DATABASE_URL hints."
docker compose -f docker-compose.yml --profile $Profile up -d
