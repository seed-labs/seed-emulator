#!/usr/bin/env bash
set -eu

MODE=smurf
ARGS=()

while [ "$#" -gt 0 ]; do
    case "$1" in
    --mode)
        MODE="$2"
        shift 2
        ;;
    --mode=*)
        MODE="${1#--mode=}"
        shift
        ;;
    *)
        ARGS+=("$1")
        shift
        ;;
    esac
done

# Run this inside the attacker container. Defaults:
# - victim: AS151 host_0, 10.151.0.71
# - vulnerable directed-broadcast LAN: AS152, 10.152.0.255
case "$MODE" in
    smurf|icmp)
        python3 /opt/demo/smurf_attack.py "${ARGS[@]}"
        ;;
    fraggle|udp)
        python3 /opt/demo/fraggle_attack.py "${ARGS[@]}"
        ;;
    *)
        echo "unknown mode: $MODE" >&2
        exit 2
        ;;
esac
