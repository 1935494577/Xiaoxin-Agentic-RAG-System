#!/usr/bin/env bash
# Create .venv at repo root and install requirements.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$ROOT"

PY_BOOT="python3"
if ! command -v python3 >/dev/null 2>&1; then
  PY_BOOT="python"
fi

if [[ ! -x "$ROOT/.venv/bin/python" ]]; then
  "$PY_BOOT" -m venv .venv
fi

"$ROOT/.venv/bin/python" -m pip install --upgrade pip
"$ROOT/.venv/bin/python" -m pip install -r requirements.txt \
  -i https://pypi.tuna.tsinghua.edu.cn/simple \
  --trusted-host pypi.tuna.tsinghua.edu.cn

echo "Done. Activate: source .venv/bin/activate"
