# Phase 1 total acceptance — run key automated checks
$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
. (Join-Path $PSScriptRoot "_port_utils.ps1")
$Py = Get-DevPython

Write-Host "=== Phase 1 automated verification ===" -ForegroundColor Cyan

Push-Location $Root
try {
    & $Py -m pytest @(
        "tests/test_phase1_acceptance.py",
        "tests/test_feedback_api.py",
        "tests/test_feedback_triage.py",
        "tests/test_feedback_stats.py",
        "tests/test_feedback_api_d.py",
        "tests/test_tenant_feedback_isolation.py",
        "tests/test_admin_roles.py",
        "-q",
        "--tb=short"
    )
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

    Push-Location (Join-Path $Root "frontend")
    npm test -- --run tests/RequireAuth.test.tsx tests/useAuth.test.tsx tests/departmentAccess.test.tsx tests/exportChatMarkdown.test.ts 2>&1 | Out-Host
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
    Pop-Location

    Write-Host "`nPhase 1 automated checks passed." -ForegroundColor Green
    Write-Host "Manual ops checklist: docs/phase1_acceptance.md" -ForegroundColor Yellow
}
finally {
    Pop-Location
}
