# Stop local API (8010) and Streamlit (8501); release ports.
$ErrorActionPreference = "Stop"
. (Join-Path $PSScriptRoot "_port_utils.ps1")

Write-Host "Stopping dev services..."
Stop-DevPorts
Write-Host "Done."
