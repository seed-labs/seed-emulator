#!/usr/bin/env python3
"""Python entrypoint for configureLinuxVxlanFabric with its shell body embedded."""
from __future__ import annotations

import sys
from pathlib import Path

from _embeddedShell import runEmbeddedShell


SHELL_BODY = r'''#!/usr/bin/env bash
# Create a two-node Linux VXLAN bridge fabric for SeedEMU Multus/macvlan.
#
# Args:
#   $1: Optional configK3s.yaml path. Defaults to ./configK3s.yaml.
#
# Expected config:
#   fabric.type: linux-vxlan
#   fabric.nodes.<nodeName>.underlayInterface: management NIC used as VXLAN underlay.
#
# Side effects:
#   Creates a bridge such as br-seedemu and a VXLAN device such as vxseed0 on
#   each node. On failure, it calls cleanLinuxVxlanFabric.py to roll back all
#   configured fabric interfaces.
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
    echo "No linux-vxlan fabric configured; skipping fabric setup."
    exit 0
fi

rollbackOnError() {
    local rc=$?
    if [ "$rc" -ne 0 ]; then
        echo "[fabric] setup failed; rolling back configured fabric interfaces" >&2
        python3 "${SCRIPT_DIR}/cleanLinuxVxlanFabric.py" "$CONFIG_PATH" || true
    fi
    exit "$rc"
}
trap rollbackOnError EXIT

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

    echo "[fabric-configure] ${name} (${ip})"
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

configure_script='
set -euo pipefail
bridge_name="$1"
vxlan_name="$2"
vni="$3"
local_ip="$4"
peer_ip="$5"
underlay="$6"
dst_port="$7"
mtu="$8"

if [ "${#bridge_name}" -gt 15 ] || [ "${#vxlan_name}" -gt 15 ]; then
    echo "Linux interface names must be at most 15 characters" >&2
    exit 1
fi

ip link show "$underlay" >/dev/null

if ip link show "$vxlan_name" >/dev/null 2>&1; then
    ip link del "$vxlan_name"
fi

if ! ip link show "$bridge_name" >/dev/null 2>&1; then
    ip link add "$bridge_name" type bridge
fi

ip link set "$bridge_name" up
ip link add "$vxlan_name" type vxlan id "$vni" local "$local_ip" remote "$peer_ip" dev "$underlay" dstport "$dst_port"
ip link set "$vxlan_name" mtu "$mtu" || true
ip link set "$vxlan_name" master "$bridge_name"
ip link set "$vxlan_name" up
'

echo "Configuring Linux VXLAN fabric:"
echo "  bridge=${fabricBridgeName}"
echo "  vxlan=${fabricVxlanName}"
echo "  vni=${fabricVni}"
echo "  dstPort=${fabricDstPort}"

while IFS=$'\t' read -r name role ip connection ssh_user ssh_key underlay bridge_test_ip macvlan_test_ip peer_name peer_ip; do
    runNodeRootScript \
        "$name" "$ip" "$connection" "$ssh_user" "$ssh_key" "$configure_script" \
        "$fabricBridgeName" "$fabricVxlanName" "$fabricVni" "$ip" "$peer_ip" \
        "$underlay" "$fabricDstPort" "$fabricMtu"
done < <(python3 "$HELPER" --config "$CONFIG_PATH" fabric-nodes-tsv)

trap - EXIT
echo "Linux VXLAN fabric configured."
'''


def main(argv: list[str] | None = None) -> int:
    """Run this entrypoint with optional argv override for tests."""
    return runEmbeddedShell(Path(__file__), list(sys.argv[1:] if argv is None else argv), SHELL_BODY)


if __name__ == "__main__":
    raise SystemExit(main())
