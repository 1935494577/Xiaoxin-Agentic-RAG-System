#!/usr/bin/env bash
set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
. "$SCRIPT_DIR/_port_utils.sh"

CHAT_DIR="$ROOT/web/chat"

if ! command -v npm >/dev/null 2>&1; then
  echo "npm not found. Install Node.js LTS (https://nodejs.org)." >&2
  exit 1
fi

stop_port_listeners "$DEV_CHAT_SPA_PORT" "Jnao Chat"
trap 'stop_port_listeners "$DEV_CHAT_SPA_PORT" "Jnao Chat"' EXIT INT TERM

if [[ ! -d "$CHAT_DIR/node_modules" ]]; then
  (cd "$CHAT_DIR" && npm install)
fi

echo "Jnao Chat: http://127.0.0.1:${DEV_CHAT_SPA_PORT}"
cd "$CHAT_DIR"
exec npm run dev
