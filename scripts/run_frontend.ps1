$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
. (Join-Path $PSScriptRoot "_port_utils.ps1")

$Port = $script:DevFrontendPort
$Py = Get-DevPython

Invoke-DevService -Port $Port -Label "Streamlit frontend" -Run {
    Set-Location $Root
    Write-Host "Frontend: http://127.0.0.1:$Port  (Ctrl+C to stop and release port)"
    & $Py -m streamlit run frontend/streamlit_app.py --server.port $Port @args
}
