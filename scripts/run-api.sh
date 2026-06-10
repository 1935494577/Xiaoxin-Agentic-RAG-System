#!/usr/bin/env bash
set -e

NO_RELOAD=0
while [[ $# -gt 0 ]]; do
  case "$1" in
    --no-reload) NO_RELOAD=1; shift ;;
    *) break ;;
  esac
done

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
. "$SCRIPT_DIR/_port_utils.sh"

PY="$(get_dev_python)"
SRC="$ROOT/enterprise_rag/src"

stop_port_listeners "$DEV_API_PORT" "API"
trap 'stop_port_listeners "$DEV_API_PORT" "API"' EXIT INT TERM

hint=""
if [[ "$NO_RELOAD" -eq 0 ]]; then
  hint=" (hot reload)"
  echo "API: http://127.0.0.1:${DEV_API_PORT}${hint}  (Ctrl+C to stop and release port)"
  cd "$SRC"
  exec "$PY" -m uvicorn api.main:app --host 127.0.0.1 --port "$DEV_API_PORT" \
    --reload --reload-dir "$SRC" --reload-delay 0.4 \
    --reload-exclude data --reload-exclude '*/data/*' \
    --reload-exclude '*__pycache__*' --reload-exclude '*.pyc'
else
  echo "API: http://127.0.0.1:${DEV_API_PORT}  (Ctrl+C to stop and release port)"
  cd "$SRC"
  exec "$PY" -m uvicorn api.main:app --host 127.0.0.1 --port "$DEV_API_PORT"
fi
