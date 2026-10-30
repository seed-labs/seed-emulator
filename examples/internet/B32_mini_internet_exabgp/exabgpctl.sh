#!/bin/sh

set -eu

SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
COMPOSE_FILE=${COMPOSE_FILE:-"$SCRIPT_DIR/output/docker-compose.yml"}
SERVICE=${EXABGP_SERVICE:-hnode_180_exabgp}

usage() {
    cat <<'EOF'
Usage:
  exabgpctl.sh announce PREFIX [NEXT_HOP]
  exabgpctl.sh withdraw PREFIX [NEXT_HOP]
  exabgpctl.sh command "RAW EXABGP COMMAND"
  exabgpctl.sh log

Examples:
  ./exabgpctl.sh announce 203.0.113.0/24 self
  ./exabgpctl.sh withdraw 203.0.113.0/24 self
  ./exabgpctl.sh command "announce route 203.0.113.0/24 next-hop self"

Environment:
  COMPOSE_FILE     Path to docker-compose.yml. Defaults to output/docker-compose.yml.
  EXABGP_SERVICE   Compose service name. Defaults to hnode_180_exabgp.
EOF
}

require_compose() {
    if [ ! -f "$COMPOSE_FILE" ]; then
        echo "compose file not found: $COMPOSE_FILE" >&2
        exit 1
    fi
}

send_command() {
    command_text=$1
    require_compose
    printf 'Sending to %s: %s\n' "$SERVICE" "$command_text"
    docker compose -f "$COMPOSE_FILE" exec -T "$SERVICE" sh -lc \
        'test -p /run/exabgp/manual.in && printf "%s\n" "$1" > /run/exabgp/manual.in' \
        sh "$command_text"
}

case "${1:-}" in
    announce|withdraw)
        action=$1
        prefix=${2:-}
        next_hop=${3:-self}
        if [ -z "$prefix" ]; then
            usage
            exit 1
        fi
        send_command "$action route $prefix next-hop $next_hop"
        ;;
    command)
        if [ -z "${2:-}" ]; then
            usage
            exit 1
        fi
        send_command "$2"
        ;;
    log)
        require_compose
        docker compose -f "$COMPOSE_FILE" exec -T "$SERVICE" sh -lc \
            'tail -n 80 /var/log/exabgp/exabgp.log'
        ;;
    ""|-h|--help|help)
        usage
        ;;
    *)
        usage
        exit 1
        ;;
esac
