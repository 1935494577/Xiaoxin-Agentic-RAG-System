# Stop local API (8010), admin Streamlit (8501), and Chat SPA (8502); release ports.
$ErrorActionPreference = "Stop"
. (Join-Path $PSScriptRoot "_port_utils.ps1")

Write-Host "Stopping dev services..."
Stop-DevPorts
Write-Host "Done."
