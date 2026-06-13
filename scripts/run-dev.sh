#!/usr/bin/env bash
# Start API + Frontend SPA (macOS / Linux).
set -e

NO_RELOAD=0
NO_SPA=0

while [[ $# -gt 0 ]]; do
  case "$1" in
    --no-reload) NO_RELOAD=1; shift ;;
    --no-spa) NO_SPA=1; shift ;;
    -h|--help)
      echo "Usage: $0 [--no-reload] [--no-spa]"
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
SPA_DIR="$ROOT/frontend"
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

wait_for_api() {
  local url="http://127.0.0.1:${DEV_API_PORT}/health"
  local max=30
  local i=0
  while [[ $i -lt $max ]]; do
    if curl -sf -o /dev/null "$url" 2>/dev/null; then
      echo "  API ready (${url})"
      return 0
    fi
    sleep 1
    ((i++))
  done
  echo "WARN: API not reachable after ${max}s — continuing anyway" >&2
}

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
wait_for_api

if [[ "$NO_SPA" -eq 0 ]]; then
  spa_pid="$(start_dev_spa "$SPA_DIR" "$DEV_SPA_PORT" || true)"
  if [[ -n "$spa_pid" ]]; then
    PIDS="$PIDS $spa_pid"
    sleep 2
  fi
fi

echo ""
echo "  >>> Frontend:  http://127.0.0.1:${DEV_SPA_PORT}"
echo "  >>> 管理后台:  http://127.0.0.1:${DEV_SPA_PORT}/admin/"
echo "  API:           http://127.0.0.1:${DEV_API_PORT}"
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
