# Remove local build artifacts and caches (safe; keeps .venv, node_modules, user data).
$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

$targets = @(
    "frontend/dist",
    "frontend/node_modules/.vite",
    "frontend/node_modules/.tmp",
    "frontend/node_modules/.vitest",
    ".codegraph",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    "enterprise_rag/data/_audit_tmp",
    "enterprise_rag/data/_bench_tmp"
)

$removed = @()
$skipped = @()
foreach ($rel in $targets) {
    $path = Join-Path $Root $rel
    if (Test-Path $path) {
        try {
            Remove-Item $path -Recurse -Force -ErrorAction Stop
            $removed += $rel
        } catch {
            $skipped += "$rel (in use)"
        }
    }
}

Get-ChildItem -Path (Join-Path $Root "enterprise_rag"), (Join-Path $Root "tests") -Recurse -Directory -Filter "__pycache__" -ErrorAction SilentlyContinue |
    ForEach-Object {
        try {
            Remove-Item $_.FullName -Recurse -Force -ErrorAction Stop
            $removed += $_.FullName.Replace($Root + "\", "")
        } catch {
            $skipped += $_.FullName.Replace($Root + "\", "") + " (in use)"
        }
    }

Get-ChildItem -Path $Root -Filter "debug-*.log" -File -ErrorAction SilentlyContinue |
    ForEach-Object {
        try {
            Remove-Item $_.FullName -Force -ErrorAction Stop
            $removed += $_.Name
        } catch {
            $skipped += $_.Name + " (in use)"
        }
    }

if ($removed.Count -eq 0 -and $skipped.Count -eq 0) {
    Write-Host "No cache directories found."
} else {
    if ($removed.Count -gt 0) {
        Write-Host "Removed $($removed.Count) item(s):"
        $removed | Sort-Object -Unique | ForEach-Object { Write-Host "  - $_" }
    }
    if ($skipped.Count -gt 0) {
        Write-Host "Skipped (file in use):"
        $skipped | Sort-Object -Unique | ForEach-Object { Write-Host "  - $_" }
    }
}
