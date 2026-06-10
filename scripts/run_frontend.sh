#!/usr/bin/env bash
set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
. "$SCRIPT_DIR/_port_utils.sh"

PY="$(get_dev_python)"

stop_port_listeners "$DEV_FRONTEND_PORT" "Streamlit frontend"
trap 'stop_port_listeners "$DEV_FRONTEND_PORT" "Streamlit frontend"' EXIT INT TERM

echo "Frontend: http://127.0.0.1:${DEV_FRONTEND_PORT}  (save file to refresh, Ctrl+C to stop)"
cd "$ROOT"
exec "$PY" -m streamlit run frontend/admin/streamlit_app.py \
  --server.port "$DEV_FRONTEND_PORT" \
  --server.runOnSave true \
  "$@"
