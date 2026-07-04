# Query understanding + retrieval robustness verification
$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
. (Join-Path $PSScriptRoot "_port_utils.ps1")
$Py = Get-DevPython

Write-Host "=== Query understanding verification ===" -ForegroundColor Cyan

Push-Location $Root
try {
    & $Py -m pytest @(
        "tests/unit/test_query_understanding.py",
        "tests/unit/test_query_normalize.py",
        "tests/unit/test_domain_lexicon.py",
        "tests/unit/test_domain_lexicon_rebuild.py",
        "tests/unit/test_term_fuzzy.py",
        "tests/unit/test_term_embeddings.py",
        "tests/unit/test_query_aliases_store.py",
        "tests/unit/test_prepare_query_understanding.py",
        "tests/unit/test_miss_query_analyzer.py",
        "tests/unit/test_scene_presets.py",
        "tests/unit/test_effective_reasoning_mode.py",
        "tests/unit/test_architecture_router.py",
        "tests/unit/test_query_robustness_eval.py",
        "tests/test_ui_config.py",
        "tests/unit/test_tool_routing.py",
        "tests/unit/test_speech_transcribe.py",
        "tests/test_kb_judge.py",
        "tests/test_kb_strict_mode.py",
        "tests/test_feedback_actuator.py",
        "-q",
        "--tb=short"
    )
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

    & $Py (Join-Path $PSScriptRoot "eval_query_robustness.py")
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

    Push-Location (Join-Path $Root "frontend")
    npm test -- --run tests/speechRecognition.test.ts tests/adminProxyBypass.test.ts tests/ChatInput.test.tsx tests/MemoryPage.test.tsx 2>&1 | Out-Host
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
    Pop-Location

    Write-Host "`nQuery understanding checks passed." -ForegroundColor Green
}
finally {
    Pop-Location
}
