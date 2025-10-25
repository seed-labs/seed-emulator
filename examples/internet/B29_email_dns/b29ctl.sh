#!/usr/bin/env bash
# Unified controller for B29 Email (DNS-first) example
# Usage:
#   bash b29ctl.sh start [--platform arm|amd]
#   bash b29ctl.sh stop
#   bash b29ctl.sh status
#   bash b29ctl.sh test [--all] [--pairs file]
#   bash b29ctl.sh generate [--platform arm|amd]
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/../../.." && pwd)"
OUTPUT_DIR="$SCRIPT_DIR/output"
PLATFORM="auto" # default; override with --platform amd|arm; 'auto' uses uname

log() { echo -e "[b29ctl] $*"; }

compose() {
  if docker compose version >/dev/null 2>&1; then
    docker compose "$@"
  elif command -v docker-compose >/dev/null 2>&1; then
    docker-compose "$@"
  else
    echo "docker compose/docker-compose not found" >&2
    return 1
  fi
}

have_compose() {
  if docker compose version >/dev/null 2>&1 || command -v docker-compose >/dev/null 2>&1; then
    return 0
  fi
  echo "docker compose/docker-compose not found" >&2
  return 1
}

b29_generate() {
  log "Generating emulation (platform=$PLATFORM) ..."
  export PYTHONPATH="$ROOT_DIR:$PYTHONPATH"
  python3 "$SCRIPT_DIR/email_realistic.py" "$PLATFORM"
  log "Generation complete: $OUTPUT_DIR"
}

b29_up() {
  have_compose || { echo "Please install docker-compose"; exit 1; }
  if [ ! -f "$OUTPUT_DIR/docker-compose.yml" ]; then
    b29_generate
  fi
  log "Starting network (compose up -d) ..."
  (cd "$OUTPUT_DIR" && compose up -d)
  log "Provisioning Roundcube accounts ..."
  "$SCRIPT_DIR/manage_roundcube.sh" accounts || true
  log "Starting Roundcube ..."
  "$SCRIPT_DIR/manage_roundcube.sh" start
  log "Done. Map: http://localhost:8080/map.html  Roundcube: http://localhost:8082"
}

b29_down() {
  have_compose || { echo "Please install docker-compose"; exit 1; }
  log "Stopping Roundcube ..."
  "$SCRIPT_DIR/manage_roundcube.sh" stop || true
  if [ -f "$OUTPUT_DIR/docker-compose.yml" ]; then
    log "Stopping network (compose down) ..."
    (cd "$OUTPUT_DIR" && compose down)
  else
    log "No output/docker-compose.yml; skip network down"
  fi
  log "Stopped."
}

b29_status() {
  have_compose || true
  if [ -f "$OUTPUT_DIR/docker-compose.yml" ]; then
    echo "--- Network status ---"
    (cd "$OUTPUT_DIR" && compose ps || true)
  else
    echo "No output/docker-compose.yml yet"
  fi
  echo "--- Roundcube status ---"
  "$SCRIPT_DIR/manage_roundcube.sh" status || true
}

b29_test() {
  # Proxy to run_cross_tests.sh with given args
  bash "$SCRIPT_DIR/run_cross_tests.sh" "$@"
}

# Parse args
CMD="${1:-start}"; shift || true
while [[ $# -gt 0 ]]; do
  case "$1" in
    --platform) PLATFORM="${2:-arm}"; shift 2;;
    *) ARGS+=("$1"); shift;;
  esac
done

case "$CMD" in
  start|up)
    b29_up
    ;;
  stop|down)
    b29_down
    ;;
  status)
    b29_status
    ;;
  test)
    b29_test "${ARGS[@]:-}"
    ;;
  generate|gen|build)
    b29_generate
    ;;
  restart)
    b29_down; b29_up
    ;;
  *)
    echo "Usage: bash b29ctl.sh {start|stop|status|test|generate|restart} [--platform auto|arm|amd]"
    exit 1
    ;;
esac
