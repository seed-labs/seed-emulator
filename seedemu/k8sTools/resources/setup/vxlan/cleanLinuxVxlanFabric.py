#!/usr/bin/env python3
"""Python entrypoint for cleanLinuxVxlanFabric with its shell body embedded."""
from __future__ import annotations

import sys
from pathlib import Path

from _embeddedShell import runEmbeddedShell


SHELL_BODY = r'''#!/usr/bin/env bash
# Remove the Linux VXLAN bridge fabric described by configK3s.yaml.
#
# Args:
#   $1: Optional configK3s.yaml path. Defaults to ./configK3s.yaml.
#
# Side effects:
#   Deletes the configured test macvlan interface, VXLAN interface, and bridge
#   on every configured node. It does not uninstall K3s or delete workload pods.
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
    echo "No linux-vxlan fabric configured; nothing to clean."
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

    echo "[fabric-clean] ${name} (${ip})"
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

cleanup_script='
set -euo pipefail
macvlan_name="$1"
vxlan_name="$2"
bridge_name="$3"

ip link del "$macvlan_name" 2>/dev/null || true
ip link del "$vxlan_name" 2>/dev/null || true
ip link del "$bridge_name" 2>/dev/null || true
'

while IFS=$'\t' read -r name role ip connection ssh_user ssh_key underlay bridge_test_ip macvlan_test_ip peer_name peer_ip; do
    runNodeRootScript \
        "$name" "$ip" "$connection" "$ssh_user" "$ssh_key" "$cleanup_script" \
        "$fabricMacvlanTestName" "$fabricVxlanName" "$fabricBridgeName"
done < <(python3 "$HELPER" --config "$CONFIG_PATH" fabric-nodes-tsv)

echo "Linux VXLAN fabric cleaned."
'''


def main(argv: list[str] | None = None) -> int:
    """Run this entrypoint with optional argv override for tests."""
    return runEmbeddedShell(Path(__file__), list(sys.argv[1:] if argv is None else argv), SHELL_BODY)


if __name__ == "__main__":
    raise SystemExit(main())
