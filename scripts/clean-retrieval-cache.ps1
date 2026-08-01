# Clear retrieval/runtime caches without touching ingested KB indexes or exam_bank.
# Keeps: raw/, processed/, chunks/, bm25_index.json, numpy_vectors.json, doc_registry, exam_bank.db
param(
    [switch]$IncludeChatSessions,
    [switch]$IncludeFeedback
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

. (Join-Path $PSScriptRoot "_harness_env.ps1")

$Py = $null
foreach ($candidate in @(
        (Join-Path $Root ".venv-harness\Scripts\python.exe"),
        (Join-Path $Root ".venv\Scripts\python.exe")
    )) {
    if (Test-Path $candidate) { $Py = $candidate; break }
}
if (-not $Py) { $Py = "python" }

Write-Host "==> Build / test caches"
& (Join-Path $PSScriptRoot "clean-cache.ps1")

$data = Join-Path $Root "enterprise_rag\data"
$removed = @()

$optionalFiles = @(
    "chat_trace.jsonl",
    "config_revisions.jsonl",
    "ingest_proposals.jsonl",
    "retrieval_tuning.json"
)
foreach ($name in $optionalFiles) {
    $path = Join-Path $data $name
    if (Test-Path $path) {
        Remove-Item $path -Force
        $removed += "enterprise_rag/data/$name"
    }
}

if ($IncludeChatSessions) {
    foreach ($name in @("chat_sessions.db", "token_usage.db")) {
        $path = Join-Path $data $name
        if (Test-Path $path) {
            Remove-Item $path -Force
            $removed += "enterprise_rag/data/$name"
        }
    }
}

if ($IncludeFeedback) {
    $fb = Join-Path $data "feedback.jsonl"
    if (Test-Path $fb) {
        Remove-Item $fb -Force
        $removed += "enterprise_rag/data/feedback.jsonl"
    }
}

Write-Host "==> Invalidate in-process / Redis hybrid search cache"
$env:PYTHONPATH = Join-Path $Root "enterprise_rag\src"
& $Py -c @"
from retrieval.search_cache import invalidate_search_cache
invalidate_search_cache()
print('search cache invalidated')
"@

if ($removed.Count -gt 0) {
    Write-Host "Removed runtime files:"
    $removed | ForEach-Object { Write-Host "  - $_" }
} else {
    Write-Host "No optional runtime files to remove."
}

Write-Host "Done. KB indexes (bm25 / vectors / chunks / raw) were NOT deleted."
