$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
    Write-Host "ERROR: 'docker' command not found."
    Write-Host ""
    Write-Host "Default dev uses Milvus Lite + local BM25 (plan1) — Docker is optional."
    Write-Host "To run legacy Milvus+ES stack: install Docker Desktop, then:"
    Write-Host "  docker compose --profile legacy up -d"
    Write-Host ""
    Write-Host "Docker Desktop: https://docs.docker.com/desktop/setup/install/windows-install/"
    exit 1
}

Write-Host "Starting legacy profile (Milvus + Elasticsearch + etcd + minio)..."
docker compose -f docker-compose.yml --profile legacy up -d @args
