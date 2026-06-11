#!/usr/bin/env bash
set -e

PORT="${1:-8010}"
HOST="${2:-0.0.0.0}"

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
. "$SCRIPT_DIR/_port_utils.sh"

PY="$(get_dev_python)"
SRC="$ROOT/enterprise_rag/src"

stop_port_listeners "$PORT" "API (production)"
trap 'stop_port_listeners "$PORT" "API (production)"' EXIT INT TERM

echo "Production API: http://${HOST}:${PORT}  (no reload, workers=1)"
echo "See docs/production_deploy.md for .env and Redis setup."
cd "$SRC"
exec "$PY" -m uvicorn api.main:app \
  --host "$HOST" \
  --port "$PORT" \
  --proxy-headers \
  --forwarded-allow-ips 127.0.0.1
