$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
$Index = "https://pypi.tuna.tsinghua.edu.cn/simple"
$Trusted = "pypi.tuna.tsinghua.edu.cn"

$req = Join-Path $Root "requirements-gpu.txt"
& python -m pip install -r $req -i $Index --trusted-host $Trusted @args
