# Shared harness / Gateway environment for Jnao (Windows PowerShell).
# Dot-source from run scripts:  . (Join-Path $PSScriptRoot "_harness_env.ps1")

$ErrorActionPreference = "Stop"

if (-not $script:HarnessEnvRoot) {
    $script:HarnessEnvRoot = Split-Path -Parent $PSScriptRoot
}

$Root = $script:HarnessEnvRoot

$HarnessDefault = "D:\bytedance flow\deer-flow\backend\packages\harness"
$HarnessPath = if ($env:AGENT_HARNESS_PATH) {
    $env:AGENT_HARNESS_PATH
} elseif ($env:DEER_FLOW_HARNESS_PATH) {
    $env:DEER_FLOW_HARNESS_PATH
} else {
    $HarnessDefault
}

function Get-HarnessRoot {
    return $Root
}

function Get-HarnessCheckoutPath {
    if (-not (Test-Path $HarnessPath)) {
        throw "Agent harness not found at '$HarnessPath'. Set AGENT_HARNESS_PATH to your deer-flow harness checkout."
    }
    return $HarnessPath
}

function Get-HarnessPython {
    $venvPy = Join-Path $Root ".venv-harness\Scripts\python.exe"
    if (Test-Path $venvPy) { return $venvPy }
    throw ".venv-harness not found. Run: .\scripts\bootstrap-harness-venv.ps1"
}

function Import-DotEnvFile {
    param([Parameter(Mandatory)][string]$Path)
    if (-not (Test-Path $Path)) { return }
    Get-Content $Path | ForEach-Object {
        $line = $_.Trim()
        if (-not $line -or $line.StartsWith("#")) { return }
        $idx = $line.IndexOf("=")
        if ($idx -lt 1) { return }
        $key = $line.Substring(0, $idx).Trim()
        $val = $line.Substring($idx + 1).Trim()
        if (($val.StartsWith('"') -and $val.EndsWith('"')) -or ($val.StartsWith("'") -and $val.EndsWith("'"))) {
            $val = $val.Substring(1, $val.Length - 2)
        }
        if ([string]::IsNullOrEmpty([Environment]::GetEnvironmentVariable($key))) {
            Set-Item -Path "env:$key" -Value $val
        }
    }
}

function Set-HarnessEnv {
    param(
        [int]$GatewayPort = 8011
    )
    $env:DEER_FLOW_PROJECT_ROOT = $Root
    $env:DEER_FLOW_CONFIG_PATH = Join-Path $Root "config.yaml"
    $env:DEER_FLOW_EXTENSIONS_CONFIG_PATH = Join-Path $Root "extensions_config.json"
    $env:PYTHONPATH = Join-Path $Root "enterprise_rag\src"
    $env:JNAO_HARNESS_GATEWAY_URL = "http://127.0.0.1:$GatewayPort"
    $env:DEER_FLOW_CHANNELS_GATEWAY_URL = $env:JNAO_HARNESS_GATEWAY_URL
    $env:DEER_FLOW_CHANNELS_LANGGRAPH_URL = "http://127.0.0.1:$GatewayPort/api"
    $env:JNAO_CHANNEL_RAG_API_URL = "http://127.0.0.1:8010"
    if (-not $env:JNAO_CHANNEL_RAG_ENABLED) {
        $env:JNAO_CHANNEL_RAG_ENABLED = "1"
    }
    if (-not $env:JNAO_IM_DEFAULT_DEPARTMENT) {
        $env:JNAO_IM_DEFAULT_DEPARTMENT = "技术部"
    }
    # Local dev only — bypass Gateway JWT; never set in production.
    if (-not $env:DEER_FLOW_AUTH_DISABLED) {
        $env:DEER_FLOW_AUTH_DISABLED = "1"
    }

    Import-DotEnvFile -Path (Join-Path $Root ".env")

    if (-not $env:OPENAI_CHAT_MODEL) { $env:OPENAI_CHAT_MODEL = "deepseek-v4-flash" }
}

function Test-HarnessReady {
    $py = Get-HarnessPython
    & $py -c "import deerflow, fastapi; print('ok')" 2>$null
    return ($LASTEXITCODE -eq 0)
}
