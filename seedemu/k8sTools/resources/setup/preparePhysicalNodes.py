#!/usr/bin/env python3
"""Python entrypoint for preparePhysicalNodes with its shell body embedded."""
from __future__ import annotations

import sys
from pathlib import Path

from _embeddedShell import runEmbeddedShell


SHELL_BODY = r'''#!/usr/bin/env bash
# Validate physical nodes before building a SeedEMU K3s cluster.
#
# Args:
#   $1: Optional configK3s.yaml path. Defaults to ./configK3s.yaml.
#
# Checks:
#   - Each node can be reached with the configured connection method.
#   - sudo -n works for the configured user.
#   - iproute2 and curl are available.
#   - linux-vxlan fabric nodes expose their configured underlay interface.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${SEED_K8S_ENTRYPOINT}")" && pwd)"
CONFIG_PATH="${1:-./configK3s.yaml}"
HELPER="${SCRIPT_DIR}/manageK3sConfig.py"

if [ ! -s "$CONFIG_PATH" ]; then
    echo "Missing config file: $CONFIG_PATH" >&2
    exit 1
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

runNodeCommand() {
    local name="$1"
    local ip="$2"
    local connection="$3"
    local ssh_user="$4"
    local ssh_key="$5"
    local command="$6"

    if [ "$connection" = "local" ]; then
        bash -lc "$command"
        return
    fi

    # shellcheck disable=SC2046
    ssh $(sshOptions "$ssh_key") "${ssh_user}@${ip}" "$command" </dev/null
}

echo "Validating physical K3s nodes from: $CONFIG_PATH"
while IFS=$'\t' read -r name role ip mac vcpus memory_mb disk_gb; do
    eval "$(python3 "$HELPER" --config "$CONFIG_PATH" node-ssh-vars --name "$name")"
    echo "  ${name} role=${role} ip=${ip} connection=${nodeConnection}"
    runNodeCommand "$name" "$ip" "$nodeConnection" "$nodeSshUser" "$nodeSshKey" "sudo -n true"
    runNodeCommand "$name" "$ip" "$nodeConnection" "$nodeSshUser" "$nodeSshKey" "command -v ip >/dev/null && command -v curl >/dev/null"
done < <(python3 "$HELPER" --config "$CONFIG_PATH" nodes-tsv)

eval "$(python3 "$HELPER" --config "$CONFIG_PATH" fabric-shell-vars)"
if [ "${fabricType}" = "linux-vxlan" ]; then
    echo "Validating linux-vxlan underlay interfaces..."
    while IFS=$'\t' read -r name role ip connection ssh_user ssh_key underlay bridge_test_ip macvlan_test_ip peer_name peer_ip; do
        echo "  ${name}: underlay=${underlay}"
        runNodeCommand "$name" "$ip" "$connection" "$ssh_user" "$ssh_key" "ip link show $(printf '%q' "$underlay") >/dev/null"
    done < <(python3 "$HELPER" --config "$CONFIG_PATH" fabric-nodes-tsv)
fi

echo "Physical node preflight passed."
'''


def main(argv: list[str] | None = None) -> int:
    """Run this entrypoint with optional argv override for tests."""
    return runEmbeddedShell(Path(__file__), list(sys.argv[1:] if argv is None else argv), SHELL_BODY)


if __name__ == "__main__":
    raise SystemExit(main())
