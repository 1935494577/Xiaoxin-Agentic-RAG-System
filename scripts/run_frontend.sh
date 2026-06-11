#!/usr/bin/env bash
# Start Frontend SPA (port 8502) — unified chat + admin
# Replaces the old Streamlit admin (8501); admin pages now at /admin/* in the SPA
set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
. "$SCRIPT_DIR/_port_utils.sh"

SPA_DIR="$ROOT/frontend"

if ! command -v npm >/dev/null 2>&1; then
  echo "npm not found. Install Node.js LTS (https://nodejs.org)." >&2
  exit 1
fi

stop_port_listeners "$DEV_SPA_PORT" "Frontend SPA"
trap 'stop_port_listeners "$DEV_SPA_PORT" "Frontend SPA"' EXIT INT TERM

if [[ ! -d "$SPA_DIR/node_modules" ]]; then
  (cd "$SPA_DIR" && npm install)
fi

echo "Frontend SPA: http://127.0.0.1:${DEV_SPA_PORT}  (管理后台: /admin/ingest)"
cd "$SPA_DIR"
exec npm run dev
