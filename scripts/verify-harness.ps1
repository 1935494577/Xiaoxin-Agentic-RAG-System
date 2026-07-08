# Quick health check for harness venv + optional running gateway.
param(
    [int]$GatewayPort = 8011,
    [int]$MainPort = 8010
)

$ErrorActionPreference = "Continue"
. (Join-Path $PSScriptRoot "_harness_env.ps1")

Write-Host "=== Jnao Harness verify ==="
Write-Host ""

try {
    $py = Get-HarnessPython
    Write-Host "[OK]  .venv-harness: $py"
} catch {
    Write-Host "[FAIL] $($_.Exception.Message)"
    Write-Host "       Run: .\scripts\bootstrap-harness-venv.ps1"
    exit 1
}

Set-HarnessEnv -GatewayPort $GatewayPort
$prevEap = $ErrorActionPreference
$ErrorActionPreference = "SilentlyContinue"
$importOut = & $py -c "import deerflow, fastapi; from app.gateway.app import create_app; print('[OK]  deerflow + gateway imports')" 2>&1
$ErrorActionPreference = $prevEap
$importOut | ForEach-Object {
    if ($_ -is [System.Management.Automation.ErrorRecord]) {
        Write-Host $_.ToString()
    } else {
        Write-Host $_
    }
}
if ($importOut -notmatch "\[OK\]") {
    Write-Host "[FAIL] Harness imports — re-run bootstrap-harness-venv.ps1"
    exit 1
}

$cfg = $env:DEER_FLOW_CONFIG_PATH
if (Test-Path $cfg) {
    Write-Host "[OK]  config.yaml: $cfg"
} else {
    Write-Host "[WARN] config.yaml missing"
}

$rt = Join-Path (Get-HarnessRoot) "enterprise_rag\data\channels\runtime-config.json"
if (Test-Path $rt) {
    Write-Host "[OK]  channel runtime-config.json present"
} else {
    Write-Host "[INFO] no runtime-config.json yet (configure in Admin -> IM 渠道)"
}

foreach ($pair in @(
    @{ Name = "Main API"; Url = "http://127.0.0.1:$MainPort/health" },
    @{ Name = "Harness Gateway"; Url = "http://127.0.0.1:$GatewayPort/health" },
    @{ Name = "Channels status"; Url = "http://127.0.0.1:$GatewayPort/api/channels/" }
)) {
    try {
        $r = Invoke-WebRequest -Uri $pair.Url -UseBasicParsing -TimeoutSec 3 -ErrorAction Stop
        Write-Host "[OK]  $($pair.Name): $($pair.Url) ($($r.StatusCode))"
    } catch {
        Write-Host "[--]  $($pair.Name): not running ($($pair.Url))"
    }
}

Write-Host ""
Write-Host "Start full dev stack:  .\scripts\run-dev-harness.ps1"
Write-Host "Gateway only:          .\scripts\run-harness-gateway.ps1"
