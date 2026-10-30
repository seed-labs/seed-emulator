#!/usr/bin/env python3
"""Python entrypoint for destroyMultiHostKvmVms with its shell body embedded."""
from __future__ import annotations

import sys
from pathlib import Path

from _embeddedShell import runEmbeddedShell


SHELL_BODY = r'''#!/usr/bin/env bash
# Destroy KVM VMs and routed networks created by the multi-host KVM flow.
#
# Inputs:
#   $1: multiHostKvmState.yaml. Defaults to ../multiHostKvmState.yaml.
#
# Side effects:
#   - Runs each host-local kvm/destroyKvmVms.py on its owning hypervisor.
#   - Removes static routes between hypervisor VM subnets.
#   - Removes optional point-to-point VXLAN route tunnels.
#   - Destroys and undefines the generated libvirt routed networks.
#   - Removes generated local configK3s/kubeconfig/inventory/state outputs.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${SEED_K8S_ENTRYPOINT}")" && pwd)"
SETUP_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
STATE_PATH="${1:-${SETUP_DIR}/multiHostKvmState.yaml}"
HELPER="${SCRIPT_DIR}/manageMultiHostKvmConfig.py"

usage() {
    cat <<EOF
Usage: $0 [multiHostKvmState.yaml]

Destroy multi-host KVM VMs recorded in multiHostKvmState.yaml.
EOF
}

requireCommand() {
    command -v "$1" >/dev/null 2>&1 || {
        echo "Missing required command: $1" >&2
        exit 1
    }
}

sshOptions() {
    # Args:
    #   $1: SSH private key path.
    local ssh_key="$1"
    printf '%s\n' \
        -o StrictHostKeyChecking=no \
        -o UserKnownHostsFile=/dev/null \
        -o LogLevel=ERROR \
        -o ConnectTimeout=10 \
        -o IdentitiesOnly=yes \
        -o IdentityAgent=none \
        -i "${ssh_key}"
}

runHostCommand() {
    # Args:
    #   $1=name, $2=ip, $3=connection, $4=ssh_user, $5=ssh_key, $6=command.
    local name="$1"
    local ip="$2"
    local connection="$3"
    local ssh_user="$4"
    local ssh_key="$5"
    local command="$6"
    local libvirt_command="export LIBVIRT_DEFAULT_URI=qemu:///system; ${command}"

    if [ "${connection}" = "local" ]; then
        bash -lc "${libvirt_command}"
        return
    fi

    # shellcheck disable=SC2046
    ssh $(sshOptions "${ssh_key}") "${ssh_user}@${ip}" "${libvirt_command}" </dev/null
}

destroyHostVms() {
    # Args are read from one state-hosts-tsv row.
    local name="$1"
    local ip="$2"
    local connection="$3"
    local ssh_user="$4"
    local ssh_key="$5"
    local network_name="$6"
    local bridge_name="$7"
    local cidr="$8"
    local remote_work_dir="${10}"

    echo "[multi-host-destroy] ${name} (${ip})"
    runHostCommand "${name}" "${ip}" "${connection}" "${ssh_user}" "${ssh_key}" "
        set -euo pipefail
        if [ -x $(printf '%q' "${remote_work_dir}/kvm/destroyKvmVms.py") ] && [ -s $(printf '%q' "${remote_work_dir}/kvmState.yaml") ]; then
            cd $(printf '%q' "${remote_work_dir}")
            python3 ./kvm/destroyKvmVms.py ./kvmState.yaml || { echo host-local KVM cleanup failed, retrying once >&2; sleep 2; python3 ./kvm/destroyKvmVms.py ./kvmState.yaml; }
        fi
        virsh net-destroy $(printf '%q' "${network_name}") >/dev/null 2>&1 || true
        virsh net-undefine $(printf '%q' "${network_name}") >/dev/null 2>&1 || true
        if command -v iptables >/dev/null 2>&1; then
            sudo -n iptables -t nat -D POSTROUTING -s $(printf '%q' "${cidr}") ! -d 10.0.0.0/8 -j MASQUERADE >/dev/null 2>&1 || true
            sudo -n iptables -D FORWARD -i $(printf '%q' "${bridge_name}") -j ACCEPT >/dev/null 2>&1 || true
            sudo -n iptables -D FORWARD -o $(printf '%q' "${bridge_name}") -j ACCEPT >/dev/null 2>&1 || true
        fi
        rm -rf $(printf '%q' "${remote_work_dir}")
    "

    while IFS=$'\t' read -r remote_cidr peer_ip peer_name route_dev; do
        [ -n "${remote_cidr}" ] || continue
        echo "  delete route ${remote_cidr} via ${peer_ip} (${peer_name})"
        if [ -n "${route_dev}" ]; then
            runHostCommand "${name}" "${ip}" "${connection}" "${ssh_user}" "${ssh_key}" \
                "sudo -n ip route del $(printf '%q' "${remote_cidr}") dev $(printf '%q' "${route_dev}") >/dev/null 2>&1 || sudo -n ip route del $(printf '%q' "${remote_cidr}") >/dev/null 2>&1 || true"
        else
            runHostCommand "${name}" "${ip}" "${connection}" "${ssh_user}" "${ssh_key}" \
                "sudo -n ip route del $(printf '%q' "${remote_cidr}") via $(printf '%q' "${peer_ip}") >/dev/null 2>&1 || true"
        fi
    done < <(python3 "${HELPER}" --config /dev/null state-routes-tsv --state "${STATE_PATH}" --host "${name}")

    while IFS=$'\t' read -r tunnel_name vni dst_port local_ip peer_ip local_tunnel_cidr peer_tunnel_ip peer_name; do
        [ -n "${tunnel_name}" ] || continue
        echo "  delete tunnel ${tunnel_name} (${peer_name})"
        runHostCommand "${name}" "${ip}" "${connection}" "${ssh_user}" "${ssh_key}" \
            "sudo -n ip link del $(printf '%q' "${tunnel_name}") >/dev/null 2>&1 || true"
    done < <(python3 "${HELPER}" --config /dev/null state-tunnels-tsv --state "${STATE_PATH}" --host "${name}")
}

cleanupLocalOutputs() {
    eval "$(python3 "${HELPER}" --config /dev/null state-output-vars --state "${STATE_PATH}")"
    rm -f "${stateConfigK3s}"
    rm -f "${stateKubeconfig}"
    rm -f "${stateInventory}"
    rm -f "${STATE_PATH}"
}

main() {
    if [ "${1:-}" = "-h" ] || [ "${1:-}" = "--help" ]; then
        usage
        exit 0
    fi
    requireCommand python3
    requireCommand ssh

    [ -s "${STATE_PATH}" ] || {
        echo "Missing state file: ${STATE_PATH}" >&2
        exit 1
    }

    while IFS=$'\t' read -r name ip connection ssh_user ssh_key network_name bridge_name cidr gateway remote_work_dir; do
        destroyHostVms "${name}" "${ip}" "${connection}" "${ssh_user}" "${ssh_key}" \
            "${network_name}" "${bridge_name}" "${cidr}" "${gateway}" "${remote_work_dir}"
    done < <(python3 "${HELPER}" --config /dev/null state-hosts-tsv --state "${STATE_PATH}")
    cleanupLocalOutputs
    echo "Multi-host KVM cleanup completed."
}

main "$@"
'''


def main(argv: list[str] | None = None) -> int:
    """Run this entrypoint with optional argv override for tests."""
    return runEmbeddedShell(Path(__file__), list(sys.argv[1:] if argv is None else argv), SHELL_BODY)


if __name__ == "__main__":
    raise SystemExit(main())
