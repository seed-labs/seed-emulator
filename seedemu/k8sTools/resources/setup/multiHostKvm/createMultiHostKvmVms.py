#!/usr/bin/env python3
"""Python entrypoint for createMultiHostKvmVms with its shell body embedded."""
from __future__ import annotations

import sys
from pathlib import Path

from _embeddedShell import runEmbeddedShell


SHELL_BODY = r'''#!/usr/bin/env bash
# Create KVM VMs across multiple physical hypervisors.
#
# Inputs:
#   $1: global multi-host kvm.yaml. Defaults to ../kvm.yaml.
#
# Outputs:
#   - Host-local kvm.yaml files under setup/tmp/multiHostKvm/.
#   - Remote host-local setup directories under hypervisors[].remoteWorkDir.
#   - Global configK3s.yaml for applyK3sCluster.py.
#   - Global multiHostKvmState.yaml for destroyMultiHostKvmVms.py.
#
# Execution context:
#   Run after prepareKvmHypervisors.py. This script creates VMs on the target
#   hypervisors but does not install K3s.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${SEED_K8S_ENTRYPOINT}")" && pwd)"
SETUP_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
CONFIG_PATH="${1:-${SETUP_DIR}/kvm.yaml}"
HELPER="${SCRIPT_DIR}/manageMultiHostKvmConfig.py"
LOCAL_WORK_DIR=""

eval "$(python3 "${HELPER}" --config "${CONFIG_PATH}" shell-vars)"

usage() {
    cat <<EOF
Usage: $0 [kvm.yaml]

Create KVM VMs on all hypervisors described by the global kvm.yaml.
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

syncDirToHost() {
    # Args:
    #   $1=name, $2=ip, $3=connection, $4=ssh_user, $5=ssh_key,
    #   $6=local_dir, $7=remote_dir.
    local name="$1"
    local ip="$2"
    local connection="$3"
    local ssh_user="$4"
    local ssh_key="$5"
    local local_dir="$6"
    local remote_dir="$7"

    if [ "${connection}" = "local" ]; then
        mkdir -p "${remote_dir}"
        rsync -a --delete "${local_dir}/" "${remote_dir}/"
        return
    fi

    runHostCommand "${name}" "${ip}" "${connection}" "${ssh_user}" "${ssh_key}" \
        "mkdir -p $(printf '%q' "${remote_dir}")"
    # shellcheck disable=SC2046
    rsync -az --delete -e "ssh $(sshOptions "${ssh_key}" | tr '\n' ' ')" \
        "${local_dir}/" "${ssh_user}@${ip}:${remote_dir}/"
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

copyVmSshKeyToHost() {
    # Args:
    #   $1=name, $2=ip, $3=connection, $4=ssh_user, $5=ssh_key.
    #
    # Remote hypervisors run kvm/createKvmVms.py locally, so they need a local
    # copy of the VM SSH private key to inject its public key into cloud-init
    # and wait for SSH readiness. The global configK3s.yaml still keeps the
    # original control-host key path for later K3s installation.
    local name="$1"
    local ip="$2"
    local connection="$3"
    local ssh_user="$4"
    local ssh_key="$5"
    local source_key target_key source_pub target_pub

    IFS=$'\t' read -r source_key target_key source_pub target_pub < <(
        python3 "${HELPER}" --config "${CONFIG_PATH}" host-vm-ssh-key-tsv --host "${name}"
    )
    [ -f "${source_key}" ] || {
        echo "VM SSH key not found on control host: ${source_key}" >&2
        exit 1
    }
    if [ "${connection}" = "local" ]; then
        return
    fi

    runHostCommand "${name}" "${ip}" "${connection}" "${ssh_user}" "${ssh_key}" \
        "mkdir -p $(printf '%q' "$(dirname "${target_key}")")"
    # shellcheck disable=SC2046
    scp $(sshOptions "${ssh_key}") "${source_key}" "${ssh_user}@${ip}:${target_key}" >/dev/null
    runHostCommand "${name}" "${ip}" "${connection}" "${ssh_user}" "${ssh_key}" \
        "chmod 600 $(printf '%q' "${target_key}")"
    if [ -f "${source_pub}" ]; then
        # shellcheck disable=SC2046
        scp $(sshOptions "${ssh_key}") "${source_pub}" "${ssh_user}@${ip}:${target_pub}" >/dev/null
        runHostCommand "${name}" "${ip}" "${connection}" "${ssh_user}" "${ssh_key}" \
            "chmod 644 $(printf '%q' "${target_pub}")"
    fi
}

prepareLocalWorkDir() {
    mkdir -p "${outputTmpDir}"
    LOCAL_WORK_DIR="${outputTmpDir}/multiHostKvm"
    rm -rf "${LOCAL_WORK_DIR}"
    mkdir -p "${LOCAL_WORK_DIR}"
}

createHostVms() {
    # Args are read from one hosts-tsv row.
    local name="$1"
    local ip="$2"
    local connection="$3"
    local ssh_user="$4"
    local ssh_key="$5"
    local remote_work_dir="${10}"
    local host_dir="${LOCAL_WORK_DIR}/${name}"
    local host_kvm_yaml="${host_dir}/kvm.yaml"

    echo "[multi-host-create] ${name} (${ip})"
    mkdir -p "${host_dir}"
    python3 "${HELPER}" --config "${CONFIG_PATH}" write-host-local-kvm \
        --host "${name}" \
        --output "${host_kvm_yaml}" >/dev/null

    syncDirToHost "${name}" "${ip}" "${connection}" "${ssh_user}" "${ssh_key}" \
        "${SETUP_DIR}/kvm" "${remote_work_dir}/kvm"
    copyFileToHost "${name}" "${ip}" "${connection}" "${ssh_user}" "${ssh_key}" \
        "${host_kvm_yaml}" "${remote_work_dir}/kvm.yaml"
    copyVmSshKeyToHost "${name}" "${ip}" "${connection}" "${ssh_user}" "${ssh_key}"

    runHostCommand "${name}" "${ip}" "${connection}" "${ssh_user}" "${ssh_key}" "
        set -euo pipefail
        cd $(printf '%q' "${remote_work_dir}")
        python3 ./kvm/prepareHostAssets.py ./kvm.yaml
        python3 ./kvm/createKvmVms.py ./kvm.yaml
    "
}

writeGlobalOutputs() {
    python3 "${HELPER}" --config "${CONFIG_PATH}" write-global-k3s-config \
        --output "${outputConfigK3s}" >/dev/null
    python3 "${HELPER}" --config "${CONFIG_PATH}" write-state \
        --output "${outputMultiHostKvmState}" >/dev/null
    echo "K3s config: ${outputConfigK3s}"
    echo "Multi-host KVM state: ${outputMultiHostKvmState}"
}

main() {
    if [ "${1:-}" = "-h" ] || [ "${1:-}" = "--help" ]; then
        usage
        exit 0
    fi
    requireCommand python3
    requireCommand ssh
    requireCommand scp
    requireCommand rsync
    requireCommand cp

    [ -s "${CONFIG_PATH}" ] || {
        echo "Missing config: ${CONFIG_PATH}" >&2
        exit 1
    }

    prepareLocalWorkDir
    python3 "${HELPER}" --config "${CONFIG_PATH}" validate
    while IFS=$'\t' read -r name ip connection ssh_user ssh_key network_name bridge_name cidr gateway remote_work_dir; do
        createHostVms "${name}" "${ip}" "${connection}" "${ssh_user}" "${ssh_key}" \
            "${network_name}" "${bridge_name}" "${cidr}" "${gateway}" "${remote_work_dir}"
    done < <(python3 "${HELPER}" --config "${CONFIG_PATH}" hosts-tsv)
    writeGlobalOutputs
    echo "Multi-host KVM VMs are ready."
}

main "$@"
'''


def main(argv: list[str] | None = None) -> int:
    """Run this entrypoint with optional argv override for tests."""
    return runEmbeddedShell(Path(__file__), list(sys.argv[1:] if argv is None else argv), SHELL_BODY)


if __name__ == "__main__":
    raise SystemExit(main())
