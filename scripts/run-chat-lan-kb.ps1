# 局域网分享：仅知识库 Chat（同事访问 http://<本机IP>:8502）
# 等价于 run-dev-lan.ps1 -KbOnly；首次可加 -OpenFirewall（需管理员）
param(
    [switch]$OpenFirewall,
    [switch]$NoReload,
    [switch]$NoSpa
)

$lanScript = Join-Path $PSScriptRoot "run-dev-lan.ps1"
$args = @("-KbOnly")
if ($OpenFirewall) { $args += "-OpenFirewall" }
if ($NoReload) { $args += "-NoReload" }
if ($NoSpa) { $args += "-NoSpa" }
& $lanScript @args
