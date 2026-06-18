# Allow inbound TCP for LAN Chat SPA and/or RAG API.
# Requires Administrator PowerShell.
param(
    [int]$ChatPort = 8502,
    [int]$ApiPort = 8010,
    [switch]$ApiOnly,
    [switch]$ChatOnly
)

$ErrorActionPreference = "Stop"

function Add-LanRule {
    param(
        [string]$Name,
        [int]$Port
    )
    if ($Port -le 0) { return }
    $existing = Get-NetFirewallRule -DisplayName $Name -ErrorAction SilentlyContinue
    if ($existing) {
        Write-Host "Firewall rule already exists: $Name"
        return
    }
    New-NetFirewallRule `
        -DisplayName $Name `
        -Direction Inbound `
        -Action Allow `
        -Protocol TCP `
        -LocalPort $Port `
        -Profile Private, Domain | Out-Null
    Write-Host "Added firewall rule: $Name (TCP $Port, Private/Domain)"
}

$isAdmin = ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole(
    [Security.Principal.WindowsBuiltInRole]::Administrator
)
if (-not $isAdmin) {
    Write-Host "Re-run PowerShell as Administrator to open firewall ports." -ForegroundColor Yellow
    exit 1
}

if ($ApiOnly) {
    Add-LanRule -Name "Jnao RAG API LAN ($ApiPort)" -Port $ApiPort
    Write-Host "Done. Colleagues connect to http://<your-LAN-IP>:$ApiPort"
    exit 0
}

if ($ChatOnly) {
    Add-LanRule -Name "Jnao Chat LAN ($ChatPort)" -Port $ChatPort
    Write-Host "Done. Colleagues open http://<your-LAN-IP>:$ChatPort"
    exit 0
}

Add-LanRule -Name "Jnao Chat LAN ($ChatPort)" -Port $ChatPort
Add-LanRule -Name "Jnao RAG API LAN ($ApiPort)" -Port $ApiPort
Write-Host "Done. Chat SPA: port $ChatPort ; RAG API: port $ApiPort"
