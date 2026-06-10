#!/usr/bin/env bash
# Start API + Chat SPA + Streamlit admin (macOS / Linux).
set -e

NO_RELOAD=0
NO_CHAT_SPA=0
NO_ADMIN=0

while [[ $# -gt 0 ]]; do
  case "$1" in
    --no-reload) NO_RELOAD=1; shift ;;
    --no-chat-spa) NO_CHAT_SPA=1; shift ;;
    --no-admin) NO_ADMIN=1; shift ;;
    -h|--help)
      echo "Usage: $0 [--no-reload] [--no-chat-spa] [--no-admin]"
      exit 0
      ;;
    *) echo "Unknown option: $1" >&2; exit 1 ;;
  esac
done

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
# shellcheck source=scripts/_port_utils.sh
. "$SCRIPT_DIR/_port_utils.sh"

PY="$(get_dev_python)"
SRC="$ROOT/enterprise_rag/src"
CHAT_DIR="$ROOT/web/chat"
PIDS=""

cleanup() {
  echo ""
  echo "Stopping dev services..."
  for pid in $PIDS; do
    kill -TERM "$pid" 2>/dev/null || true
  done
  sleep 0.5
  for pid in $PIDS; do
    kill -KILL "$pid" 2>/dev/null || true
  done
  stop_dev_ports
  exit 0
}

trap cleanup INT TERM

stop_dev_ports

if [[ "$NO_RELOAD" -eq 0 ]]; then
  echo "Starting API on port ${DEV_API_PORT} (hot reload)..."
  (cd "$SRC" && "$PY" -m uvicorn api.main:app --host 127.0.0.1 --port "$DEV_API_PORT" \
    --reload --reload-dir "$SRC" --reload-delay 0.4 \
    --reload-exclude data --reload-exclude '*/data/*' \
    --reload-exclude '*__pycache__*' --reload-exclude '*.pyc') &
else
  echo "Starting API on port ${DEV_API_PORT}..."
  (cd "$SRC" && "$PY" -m uvicorn api.main:app --host 127.0.0.1 --port "$DEV_API_PORT") &
fi
PIDS="$PIDS $!"
sleep 2

if [[ "$NO_CHAT_SPA" -eq 0 ]]; then
  chat_pid="$(start_dev_chat_spa "$CHAT_DIR" "$DEV_CHAT_SPA_PORT" || true)"
  if [[ -n "$chat_pid" ]]; then
    PIDS="$PIDS $chat_pid"
    sleep 2
  fi
fi

if [[ "$NO_ADMIN" -eq 0 ]]; then
  echo "Starting Streamlit admin on port ${DEV_FRONTEND_PORT}..."
  (cd "$ROOT" && "$PY" -m streamlit run frontend/streamlit_app.py \
    --server.port "$DEV_FRONTEND_PORT" \
    --server.runOnSave true) &
  PIDS="$PIDS $!"
fi

echo ""
echo "  >>> Jnao Chat:      http://127.0.0.1:${DEV_CHAT_SPA_PORT}"
echo "  API:              http://127.0.0.1:${DEV_API_PORT}"
if [[ "$NO_ADMIN" -eq 0 ]]; then
  echo "  管理后台:         http://127.0.0.1:${DEV_FRONTEND_PORT}"
fi
echo ""
echo "Press Ctrl+C here to stop all services."

while true; do
  alive=0
  for pid in $PIDS; do
    if kill -0 "$pid" 2>/dev/null; then
      alive=1
      break
    fi
  done
  if [[ "$alive" -eq 0 ]]; then
    echo "All services exited."
    break
  fi
  sleep 1
done

cleanup
