#!/usr/bin/env python3
"""Python entrypoint for prepareKvmHypervisors with its shell body embedded."""
from __future__ import annotations

import sys
from pathlib import Path

from _embeddedShell import runEmbeddedShell


SHELL_BODY = r'''#!/usr/bin/env bash
# Prepare physical KVM hypervisors for a multi-host KVM SeedEMU cluster.
#
# Inputs:
#   $1: global multi-host kvm.yaml. Defaults to ../kvm.yaml.
#
# Generated/modified state:
#   - Creates one routed libvirt network per hypervisor.
#   - Enables IPv4 forwarding on each hypervisor.
#   - Optionally creates point-to-point VXLAN route tunnels.
#   - Installs static routes between the hypervisor VM subnets.
#
# Execution context:
#   Run from the generated setup directory before createMultiHostKvmVms.py.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${SEED_K8S_ENTRYPOINT}")" && pwd)"
SETUP_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
CONFIG_PATH="${1:-${SETUP_DIR}/kvm.yaml}"
HELPER="${SCRIPT_DIR}/manageMultiHostKvmConfig.py"
TMP_DIR=""

usage() {
    cat <<EOF
Usage: $0 [kvm.yaml]

Prepare physical KVM hypervisors for multi-host VM creation.
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

copyFileToHost() {
    # Args:
    #   $1=name, $2=ip, $3=connection, $4=ssh_user, $5=ssh_key,
    #   $6=local_file, $7=remote_file.
    local name="$1"
    local ip="$2"
    local connection="$3"
    local ssh_user="$4"
    local ssh_key="$5"
    local local_file="$6"
    local remote_file="$7"

    if [ "${connection}" = "local" ]; then
        mkdir -p "$(dirname "${remote_file}")"
        cp "${local_file}" "${remote_file}"
        return
    fi

    runHostCommand "${name}" "${ip}" "${connection}" "${ssh_user}" "${ssh_key}" \
        "mkdir -p $(printf '%q' "$(dirname "${remote_file}")")"
    # shellcheck disable=SC2046
    scp $(sshOptions "${ssh_key}") "${local_file}" "${ssh_user}@${ip}:${remote_file}" >/dev/null
}

cleanupTmp() {
    [ -n "${TMP_DIR}" ] && rm -rf "${TMP_DIR}" || true
}

validateConfig() {
    python3 "${HELPER}" --config "${CONFIG_PATH}" validate
}

prepareHost() {
    # Args are read from one hosts-tsv row.
    local name="$1"
    local ip="$2"
    local connection="$3"
    local ssh_user="$4"
    local ssh_key="$5"
    local network_name="$6"
    local bridge_name="$7"
    local cidr="$8"
    local remote_work_dir="${10}"
    local network_xml="${TMP_DIR}/${name}.xml"
    local remote_xml="${remote_work_dir}/network.xml"

    echo "[hypervisor-prepare] ${name} (${ip}) network=${network_name} bridge=${bridge_name}"
    python3 "${HELPER}" --config "${CONFIG_PATH}" write-host-network-xml \
        --host "${name}" \
        --output "${network_xml}" >/dev/null

    runHostCommand "${name}" "${ip}" "${connection}" "${ssh_user}" "${ssh_key}" \
        "sudo -n true && command -v virsh >/dev/null && command -v virt-install >/dev/null && command -v qemu-img >/dev/null && command -v docker >/dev/null && command -v curl >/dev/null && command -v ssh >/dev/null"
    runHostCommand "${name}" "${ip}" "${connection}" "${ssh_user}" "${ssh_key}" \
        "mkdir -p $(printf '%q' "${remote_work_dir}")"
    copyFileToHost "${name}" "${ip}" "${connection}" "${ssh_user}" "${ssh_key}" "${network_xml}" "${remote_xml}"

    runHostCommand "${name}" "${ip}" "${connection}" "${ssh_user}" "${ssh_key}" "
        set -euo pipefail
        virsh net-info $(printf '%q' "${network_name}") >/dev/null 2>&1 || virsh net-define $(printf '%q' "${remote_xml}") >/dev/null
        virsh net-start $(printf '%q' "${network_name}") >/dev/null 2>&1 || true
        virsh net-autostart $(printf '%q' "${network_name}") >/dev/null 2>&1 || true
        sudo -n sysctl -w net.ipv4.ip_forward=1 >/dev/null
        if command -v iptables >/dev/null 2>&1; then
            sudo -n iptables -C FORWARD -i $(printf '%q' "${bridge_name}") -j ACCEPT >/dev/null 2>&1 || sudo -n iptables -I FORWARD -i $(printf '%q' "${bridge_name}") -j ACCEPT
            sudo -n iptables -C FORWARD -o $(printf '%q' "${bridge_name}") -j ACCEPT >/dev/null 2>&1 || sudo -n iptables -I FORWARD -o $(printf '%q' "${bridge_name}") -j ACCEPT
            sudo -n iptables -t nat -C POSTROUTING -s $(printf '%q' "${cidr}") ! -d 10.0.0.0/8 -j MASQUERADE >/dev/null 2>&1 || sudo -n iptables -t nat -A POSTROUTING -s $(printf '%q' "${cidr}") ! -d 10.0.0.0/8 -j MASQUERADE
        fi
    "

    while IFS=$'\t' read -r tunnel_name vni dst_port local_ip peer_ip local_tunnel_cidr peer_tunnel_ip peer_name; do
        [ -n "${tunnel_name}" ] || continue
        echo "  tunnel ${tunnel_name}: ${local_tunnel_cidr} -> ${peer_tunnel_ip} (${peer_name})"
        runHostCommand "${name}" "${ip}" "${connection}" "${ssh_user}" "${ssh_key}" "
            set -euo pipefail
            underlay_dev=\$(ip route get $(printf '%q' "${peer_ip}") | awk '{for (i=1;i<=NF;i++) if (\$i==\"dev\") {print \$(i+1); exit}}')
            [ -n \"\${underlay_dev}\" ] || { echo 'Cannot determine underlay dev for peer $(printf '%q' "${peer_ip}")' >&2; exit 1; }
            sudo -n ip link del $(printf '%q' "${tunnel_name}") >/dev/null 2>&1 || true
            sudo -n ip link add $(printf '%q' "${tunnel_name}") type vxlan id $(printf '%q' "${vni}") local $(printf '%q' "${local_ip}") remote $(printf '%q' "${peer_ip}") dstport $(printf '%q' "${dst_port}") dev \"\${underlay_dev}\"
            sudo -n ip addr add $(printf '%q' "${local_tunnel_cidr}") dev $(printf '%q' "${tunnel_name}")
            sudo -n ip link set $(printf '%q' "${tunnel_name}") up
        "
    done < <(python3 "${HELPER}" --config "${CONFIG_PATH}" host-tunnels-tsv --host "${name}")

    while IFS=$'\t' read -r remote_cidr peer_ip peer_name route_dev; do
        [ -n "${remote_cidr}" ] || continue
        if [ -n "${route_dev}" ]; then
            echo "  route ${remote_cidr} via ${peer_ip} dev ${route_dev} (${peer_name})"
            runHostCommand "${name}" "${ip}" "${connection}" "${ssh_user}" "${ssh_key}" \
                "sudo -n ip route replace $(printf '%q' "${remote_cidr}") via $(printf '%q' "${peer_ip}") dev $(printf '%q' "${route_dev}")"
        else
            echo "  route ${remote_cidr} via ${peer_ip} (${peer_name})"
            runHostCommand "${name}" "${ip}" "${connection}" "${ssh_user}" "${ssh_key}" \
                "sudo -n ip route replace $(printf '%q' "${remote_cidr}") via $(printf '%q' "${peer_ip}")"
        fi
    done < <(python3 "${HELPER}" --config "${CONFIG_PATH}" host-routes-tsv --host "${name}")
}

main() {
    if [ "${1:-}" = "-h" ] || [ "${1:-}" = "--help" ]; then
        usage
        exit 0
    fi
    requireCommand python3
    requireCommand ssh
    requireCommand scp
    requireCommand cp
    requireCommand mktemp

    [ -s "${CONFIG_PATH}" ] || {
        echo "Missing config: ${CONFIG_PATH}" >&2
        exit 1
    }

    TMP_DIR="$(mktemp -d "${SETUP_DIR}/tmp.multi-host-kvm.XXXXXX")"
    trap cleanupTmp EXIT

    validateConfig
    while IFS=$'\t' read -r name ip connection ssh_user ssh_key network_name bridge_name cidr gateway remote_work_dir; do
        prepareHost "${name}" "${ip}" "${connection}" "${ssh_user}" "${ssh_key}" \
            "${network_name}" "${bridge_name}" "${cidr}" "${gateway}" "${remote_work_dir}"
    done < <(python3 "${HELPER}" --config "${CONFIG_PATH}" hosts-tsv)

    echo "KVM hypervisors are ready."
}

main "$@"
'''


def main(argv: list[str] | None = None) -> int:
    """Run this entrypoint with optional argv override for tests."""
    return runEmbeddedShell(Path(__file__), list(sys.argv[1:] if argv is None else argv), SHELL_BODY)


if __name__ == "__main__":
    raise SystemExit(main())
