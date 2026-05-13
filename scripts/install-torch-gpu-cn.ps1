$ErrorActionPreference = "Stop"
$Index = "https://pypi.tuna.tsinghua.edu.cn/simple"
$Trusted = "pypi.tuna.tsinghua.edu.cn"
$Extra = "https://download.pytorch.org/whl/cu124"
Write-Host "Installing CUDA 12.4 PyTorch wheels (extra-index) + Tsinghua PyPI for deps..."
& python -m pip install --upgrade torch torchvision torchaudio -i $Index --trusted-host $Trusted --extra-index-url $Extra @args
