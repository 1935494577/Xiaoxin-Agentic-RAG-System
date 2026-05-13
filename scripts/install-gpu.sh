#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
INDEX="https://pypi.tuna.tsinghua.edu.cn/simple"
TRUSTED="pypi.tuna.tsinghua.edu.cn"
python -m pip install -r "$ROOT/requirements-gpu.txt" -i "$INDEX" --trusted-host "$TRUSTED" "$@"
