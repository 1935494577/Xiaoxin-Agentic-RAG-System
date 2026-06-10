#!/usr/bin/env bash
set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
. "$SCRIPT_DIR/_port_utils.sh"
echo "Stopping dev services..."
stop_dev_ports
echo "Done."
