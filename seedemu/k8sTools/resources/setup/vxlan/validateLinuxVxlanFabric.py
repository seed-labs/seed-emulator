#!/usr/bin/env python3
"""Python entrypoint for validateLinuxVxlanFabric with its shell body embedded."""
from __future__ import annotations

import sys
from pathlib import Path

from _embeddedShell import runEmbeddedShell


SHELL_BODY = r'''#!/usr/bin/env bash
# Validate the Linux VXLAN bridge fabric used by SeedEMU Multus/macvlan.
#
# Args:
#   $1: Optional configK3s.yaml path. Defaults to ./configK3s.yaml.
#
# Validation:
#   1. Adds temporary /30 IPs to the configured bridge and pings both ways.
#   2. Creates temporary macvlan interfaces on the bridge and pings both ways.
#
# Side effects:
#   Temporary test IPs and macvlan interfaces are always removed. If validation
#   fails, the configured VXLAN fabric is also removed to avoid stale state.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${SEED_K8S_ENTRYPOINT}")" && pwd)"
SETUP_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
CONFIG_PATH="${1:-${SETUP_DIR}/configK3s.yaml}"
HELPER="${SETUP_DIR}/manageK3sConfig.py"

if [ ! -s "$CONFIG_PATH" ]; then
    echo "Missing config file: $CONFIG_PATH" >&2
    exit 1
fi

eval "$(python3 "$HELPER" --config "$CONFIG_PATH" fabric-shell-vars)"

if [ "${fabricType}" != "linux-vxlan" ]; then
    echo "No linux-vxlan fabric configured; skipping fabric validation."
    exit 0
fi

sshOptions() {
    local ssh_key="$1"
    printf '%s\n' \
        -o StrictHostKeyChecking=no \
        -o UserKnownHostsFile=/dev/null \
        -o LogLevel=ERROR \
        -o ConnectTimeout=10 \
        -i "$ssh_key"
}

runNodeRootScript() {
    local name="$1"
    local ip="$2"
    local connection="$3"
    local ssh_user="$4"
    local ssh_key="$5"
    local script="$6"
    shift 6

    echo "[fabric-validate] ${name} (${ip})"
    if [ "$connection" = "local" ]; then
        sudo -n bash -s -- "$@" <<<"$script"
        return
    fi

    local quoted_args=""
    local arg
    for arg in "$@"; do
        quoted_args+=" $(printf '%q' "$arg")"
    done
    # shellcheck disable=SC2046
    ssh $(sshOptions "$ssh_key") "${ssh_user}@${ip}" "sudo -n bash -s --${quoted_args}" <<<"$script"
}

runNodeRootCommand() {
    local name="$1"
    local ip="$2"
    local connection="$3"
    local ssh_user="$4"
    local ssh_key="$5"
    local command="$6"

    echo "[fabric-validate] ${name} (${ip})"
    if [ "$connection" = "local" ]; then
        sudo -n bash -lc "$command"
        return
    fi

    # shellcheck disable=SC2046
    ssh $(sshOptions "$ssh_key") "${ssh_user}@${ip}" "sudo -n bash -lc $(printf '%q' "$command")" </dev/null
}

cleanupTestArtifacts() {
    local cleanup_script='
set -euo pipefail
bridge_name="$1"
macvlan_name="$2"
bridge_test_ip="$3"

ip link del "$macvlan_name" 2>/dev/null || true
ip addr del "$bridge_test_ip" dev "$bridge_name" 2>/dev/null || true
ip neigh flush dev "$bridge_name" 2>/dev/null || true
'
    while IFS=$'\t' read -r name role ip connection ssh_user ssh_key underlay bridge_test_ip macvlan_test_ip peer_name peer_ip; do
        runNodeRootScript \
            "$name" "$ip" "$connection" "$ssh_user" "$ssh_key" "$cleanup_script" \
            "$fabricBridgeName" "$fabricMacvlanTestName" "$bridge_test_ip" || true
    done < <(python3 "$HELPER" --config "$CONFIG_PATH" fabric-nodes-tsv)
}

cleanupOnExit() {
    local rc=$?
    cleanupTestArtifacts
    if [ "$rc" -ne 0 ]; then
        echo "[fabric] validation failed; cleaning configured fabric interfaces" >&2
        python3 "${SCRIPT_DIR}/cleanLinuxVxlanFabric.py" "$CONFIG_PATH" || true
    fi
    exit "$rc"
}
trap cleanupOnExit EXIT

setup_bridge_ip='
set -euo pipefail
bridge_name="$1"
bridge_test_ip="$2"

ip link show "$bridge_name" >/dev/null
ip addr del "$bridge_test_ip" dev "$bridge_name" 2>/dev/null || true
ip addr add "$bridge_test_ip" dev "$bridge_name"
ip link set "$bridge_name" up
'

setup_macvlan='
set -euo pipefail
bridge_name="$1"
macvlan_name="$2"
macvlan_test_ip="$3"

ip link del "$macvlan_name" 2>/dev/null || true
ip link add "$macvlan_name" link "$bridge_name" type macvlan mode bridge
ip addr add "$macvlan_test_ip" dev "$macvlan_name"
ip link set "$macvlan_name" up
'

echo "Validating Linux VXLAN bridge reachability..."
while IFS=$'\t' read -r name role ip connection ssh_user ssh_key underlay bridge_test_ip macvlan_test_ip peer_name peer_ip; do
    runNodeRootScript \
        "$name" "$ip" "$connection" "$ssh_user" "$ssh_key" "$setup_bridge_ip" \
        "$fabricBridgeName" "$bridge_test_ip"
done < <(python3 "$HELPER" --config "$CONFIG_PATH" fabric-nodes-tsv)
sleep 1

while IFS=$'\t' read -r name role ip connection ssh_user ssh_key underlay bridge_test_ip macvlan_test_ip peer_name peer_ip; do
    peer_bridge_test_ip="$(python3 "$HELPER" --config "$CONFIG_PATH" fabric-nodes-tsv | awk -F '\t' -v peer="$peer_name" '$1 == peer {print $8; exit}')"
    peer_bridge_ip="${peer_bridge_test_ip%/*}"
    runNodeRootCommand \
        "$name" "$ip" "$connection" "$ssh_user" "$ssh_key" \
        "ping -c 3 -W 2 $(printf '%q' "$peer_bridge_ip")"
done < <(python3 "$HELPER" --config "$CONFIG_PATH" fabric-nodes-tsv)

echo "Removing bridge test IPs before macvlan validation..."
cleanupTestArtifacts
sleep 1

echo "Validating macvlan reachability over Linux VXLAN bridge..."
while IFS=$'\t' read -r name role ip connection ssh_user ssh_key underlay bridge_test_ip macvlan_test_ip peer_name peer_ip; do
    runNodeRootScript \
        "$name" "$ip" "$connection" "$ssh_user" "$ssh_key" "$setup_macvlan" \
        "$fabricBridgeName" "$fabricMacvlanTestName" "$macvlan_test_ip"
done < <(python3 "$HELPER" --config "$CONFIG_PATH" fabric-nodes-tsv)
sleep 2

while IFS=$'\t' read -r name role ip connection ssh_user ssh_key underlay bridge_test_ip macvlan_test_ip peer_name peer_ip; do
    peer_macvlan_test_ip="$(python3 "$HELPER" --config "$CONFIG_PATH" fabric-nodes-tsv | awk -F '\t' -v peer="$peer_name" '$1 == peer {print $9; exit}')"
    peer_macvlan_ip="${peer_macvlan_test_ip%/*}"
    runNodeRootCommand \
        "$name" "$ip" "$connection" "$ssh_user" "$ssh_key" \
        "ping -I $(printf '%q' "$fabricMacvlanTestName") -c 3 -W 2 $(printf '%q' "$peer_macvlan_ip")"
done < <(python3 "$HELPER" --config "$CONFIG_PATH" fabric-nodes-tsv)

cleanupTestArtifacts
trap - EXIT
echo "Linux VXLAN fabric validation passed."
'''


def main(argv: list[str] | None = None) -> int:
    """Run this entrypoint with optional argv override for tests."""
    return runEmbeddedShell(Path(__file__), list(sys.argv[1:] if argv is None else argv), SHELL_BODY)


if __name__ == "__main__":
    raise SystemExit(main())
