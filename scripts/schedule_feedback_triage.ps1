# Run feedback triage batch — for Windows Task Scheduler or manual cron substitute.
# Example Task Scheduler: daily at 02:00, action = powershell.exe -File D:\11\scripts\schedule_feedback_triage.ps1
param(
    [string]$ApiBase = "http://127.0.0.1:8010",
    [int]$Limit = 20,
    [switch]$UseLlm
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot

# Load .env if present (RAG_ADMIN_API_SECRET, etc.)
$envFile = Join-Path $Root ".env"
if (Test-Path $envFile) {
    Get-Content $envFile | ForEach-Object {
        if ($_ -match '^\s*([^#=]+)=(.*)$') {
            $k = $matches[1].Trim()
            $v = $matches[2].Trim().Trim('"').Trim("'")
            if (-not [string]::IsNullOrWhiteSpace($k) -and -not (Test-Path "env:$k")) {
                Set-Item -Path "env:$k" -Value $v
            }
        }
    }
}

$headers = @{ "Content-Type" = "application/json" }
$adminSecret = [string]$env:RAG_ADMIN_API_SECRET
if ($adminSecret) {
    $headers["X-API-Key"] = $adminSecret.Trim()
}

$body = @{
    limit   = $Limit
    use_llm = [bool]$UseLlm
} | ConvertTo-Json -Compress

$url = "$ApiBase/admin/feedback/triage"
Write-Host "[$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')] POST $url (limit=$Limit, use_llm=$UseLlm)"

try {
    $resp = Invoke-RestMethod -Uri $url -Method POST -Headers $headers -Body $body -TimeoutSec 120
    Write-Host "  processed=$($resp.processed) failed=$($resp.failed) queued=$($resp.queued)" -ForegroundColor Green
    exit 0
}
catch {
    Write-Host "  ERROR: $($_.Exception.Message)" -ForegroundColor Red
    exit 1
}
