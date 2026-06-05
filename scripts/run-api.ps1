param(
    [switch]$NoReload
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
. (Join-Path $PSScriptRoot "_port_utils.ps1")

$Port = $script:DevApiPort
$Py = Get-DevPython
$Src = Join-Path $Root "enterprise_rag\src"

Invoke-DevService -Port $Port -Label "API" -Run {
    Set-Location $Src
    $uvicornArgs = @(
        "-m", "uvicorn", "api.main:app",
        "--host", "127.0.0.1", "--port", $using:Port
    )
    if (-not $using:NoReload) {
        $uvicornArgs += Get-UvicornReloadArgs -SrcDir $using:Src
    }
    $hint = if (-not $using:NoReload) { " (hot reload)" } else { "" }
    Write-Host "API: http://127.0.0.1:$($using:Port)$hint  (Ctrl+C to stop and release port)"
    & $using:Py @uvicornArgs
}
