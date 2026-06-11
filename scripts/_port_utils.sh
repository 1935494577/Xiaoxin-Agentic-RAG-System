#!/usr/bin/env bash
# Shared port / process helpers for local dev (macOS / Linux).
# Compatible with macOS default Bash 3.2.

DEV_API_PORT=8010
DEV_SPA_PORT=8502

_UTILS_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

_repo_root() {
  cd "$_UTILS_DIR/.." && pwd
}

get_dev_python() {
  local root
  root="$(_repo_root)"
  if [[ -x "$root/.venv/bin/python" ]]; then
    echo "$root/.venv/bin/python"
  elif [[ -x "$root/.venv/Scripts/python.exe" ]]; then
    echo "$root/.venv/Scripts/python.exe"
  elif command -v python3 >/dev/null 2>&1; then
    echo "python3"
  else
    echo "python"
  fi
}

get_port_listener_pids() {
  local port="$1"
  if command -v lsof >/dev/null 2>&1; then
    lsof -ti "tcp:${port}" -sTCP:LISTEN 2>/dev/null || true
  fi
}

stop_port_listeners() {
  local port="$1"
  local label="${2:-port $port}"
  local pid
  local found=0
  while IFS= read -r pid; do
    [[ -z "$pid" ]] && continue
    found=1
    kill -TERM "$pid" 2>/dev/null || true
  done <<EOF
$(get_port_listener_pids "$port")
EOF
  if [[ "$found" -eq 0 ]]; then
    return 0
  fi
  sleep 0.3
  while IFS= read -r pid; do
    [[ -z "$pid" ]] && continue
    kill -KILL "$pid" 2>/dev/null || true
  done <<EOF
$(get_port_listener_pids "$port")
EOF
  echo "Released ${label} (port ${port})."
}

stop_dev_ports() {
  stop_port_listeners "$DEV_API_PORT" "API"
  stop_port_listeners "$DEV_SPA_PORT" "Frontend SPA"
}

start_dev_spa() {
  local spa_dir="$1"
  local port="${2:-$DEV_SPA_PORT}"
  if ! command -v npm >/dev/null 2>&1; then
    echo "WARN: npm not found — skip Frontend SPA. Install Node.js LTS." >&2
    return 1
  fi
  if [[ ! -d "$spa_dir/node_modules" ]]; then
    echo "Installing Frontend SPA dependencies..." >&2
    (cd "$spa_dir" && npm install) || {
      echo "WARN: npm install failed." >&2
      return 1
    }
  fi
  echo "Starting Frontend SPA on port ${port}..." >&2
  (cd "$spa_dir" && npm run dev) &
  echo $!
}
