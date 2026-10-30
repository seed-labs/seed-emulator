#!/usr/bin/env python3
"""Python entrypoint for tuneVmLimits with its shell body embedded."""
from __future__ import annotations

import sys
from pathlib import Path

from _embeddedShell import runEmbeddedShell


SHELL_BODY = r'''#!/usr/bin/env bash
# Tune OS-level limits on each VM listed in configK3s.yaml.
# Inputs: configK3s.yaml with nodes and SSH settings.
# Outputs/side effects: writes sysctl, limits, systemd drop-ins, and cni0
# hash_max service on each VM through SSH. No K3s installation is performed.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${SEED_K8S_ENTRYPOINT}")" && pwd)"
SETUP_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
CONFIG_PATH="${1:-${SETUP_DIR}/configK3s.yaml}"
HELPER="${SETUP_DIR}/manageK3sConfig.py"

eval "$(python3 "${HELPER}" --config "${CONFIG_PATH}" shell-vars)"

# Keep these defaults in the script, not in configK3s.yaml. The YAML describes VMs;
# this script describes the current high-density OS limit policy.
vmLimitNofile="10485760"
vmLimitNproc="4194304"
vmLimitMaxNetNamespaces="65536"
vmLimitNeighGcThresh1="1048576"
vmLimitNeighGcThresh2="4194304"
vmLimitNeighGcThresh3="8388608"
vmLimitNetdevMaxBacklog="1000000"
vmLimitOptmemMax="25165824"
vmLimitCni0HashMax="16384"
vmLimitReboot="false"

NODE_SSH_OPTS=()
nodeSshUser=""
nodeSshKey=""
nodeConnection=""

usage() {
    cat <<EOF
Usage: $0 [configK3s.yaml]

Open OS-level limits on every VM listed in the YAML.
Only SSH access is required, so the implementation is VM-provider neutral.
The current setup flow only creates KVM guests, but this script can also tune
other VM types if the YAML lists reachable IPs and the SSH user/key is valid.

Limit policy is fixed in this script. Change the variables near the top only
when intentionally changing the cluster tuning policy.
EOF
}

nodesInput() {
    python3 "${HELPER}" --config "${CONFIG_PATH}" nodes-tsv
}

loadNodeSshContext() {
    # Args:
    #   $1: node name from configK3s.yaml.
    # Reads per-node ssh.user/key through manageK3sConfig.py and prepares the
    # SSH options used by waitForSsh and unlockOneVm. If the node is marked or
    # auto-detected as local, no SSH key is required.
    local name="$1"
    eval "$(python3 "${HELPER}" --config "${CONFIG_PATH}" node-ssh-vars --name "${name}")"
    if [ "${nodeConnection:-ssh}" = "local" ]; then
        NODE_SSH_OPTS=()
        return 0
    fi
    [ -f "${nodeSshKey}" ] || {
        echo "SSH key not found for ${name}: ${nodeSshKey}" >&2
        exit 1
    }
    NODE_SSH_OPTS=(
        -i "${nodeSshKey}"
        -o StrictHostKeyChecking=no
        -o UserKnownHostsFile=/dev/null
        -o LogLevel=ERROR
        -o BatchMode=yes
        -o IdentitiesOnly=yes
        -o IdentityAgent=none
        -o ConnectTimeout=10
        -o ServerAliveInterval=30
        -o ServerAliveCountMax=3
    )
}

requireCommand() {
    command -v "$1" >/dev/null 2>&1 || {
        echo "Missing required command: $1" >&2
        exit 1
    }
}

waitForSsh() {
    local name="$1"
    local ip="$2"
    loadNodeSshContext "${name}"
    if [ "${nodeConnection:-ssh}" = "local" ]; then
        sudo -n true >/dev/null 2>&1 || {
            echo "Local sudo failed for ${name} (${ip})" >&2
            return 1
        }
        return 0
    fi
    if ssh -n "${NODE_SSH_OPTS[@]}" "${nodeSshUser}@${ip}" "echo ok" >/dev/null 2>&1; then
        return 0
    fi
    echo "SSH failed for ${name} (${ip})" >&2
    return 1
}

unlockOneVm() {
    local name="$1"
    local ip="$2"
    local remote_runner=()
    echo "Unlocking VM limits: ${name} (${ip})"
    loadNodeSshContext "${name}"
    if [ "${nodeConnection:-ssh}" = "local" ]; then
        remote_runner=(sudo -n bash -s --)
    else
        remote_runner=(ssh "${NODE_SSH_OPTS[@]}" "${nodeSshUser}@${ip}" "sudo -n bash -s" --)
    fi
    "${remote_runner[@]}" \
        "${vmLimitNofile}" \
        "${vmLimitNproc}" \
        "${vmLimitMaxNetNamespaces}" \
        "${vmLimitNeighGcThresh1}" \
        "${vmLimitNeighGcThresh2}" \
        "${vmLimitNeighGcThresh3}" \
        "${vmLimitNetdevMaxBacklog}" \
        "${vmLimitOptmemMax}" \
        "${vmLimitCni0HashMax}" \
        "${vmLimitReboot}" <<'EOF_REMOTE'
set -euo pipefail

LIMIT_NOFILE="$1"
LIMIT_NPROC="$2"
MAX_NET_NS="$3"
NEIGH1="$4"
NEIGH2="$5"
NEIGH3="$6"
NETDEV_BACKLOG="$7"
OPTMEM_MAX="$8"
CNI0_HASH_MAX="$9"
DO_REBOOT="${10}"

appendIfMissing() {
    local file="$1"
    local pattern="$2"
    local line="$3"
    touch "${file}"
    if ! grep -qF "${pattern}" "${file}"; then
        printf '%s\n' "${line}" >> "${file}"
    fi
}

echo ">> limits.conf"
appendIfMissing /etc/security/limits.conf "* soft nofile" "* soft    nofile          ${LIMIT_NOFILE}"
appendIfMissing /etc/security/limits.conf "* hard nofile" "* hard    nofile          ${LIMIT_NOFILE}"
appendIfMissing /etc/security/limits.conf "* soft nproc" "* soft    nproc           ${LIMIT_NPROC}"
appendIfMissing /etc/security/limits.conf "* hard nproc" "* hard    nproc           ${LIMIT_NPROC}"
appendIfMissing /etc/security/limits.conf "root soft nofile" "root            soft    nofile          ${LIMIT_NOFILE}"
appendIfMissing /etc/security/limits.conf "root hard nofile" "root            hard    nofile          ${LIMIT_NOFILE}"

echo ">> sysctl"
cat > /etc/sysctl.d/99-seed-vm-limits.conf <<EOF_SYSCTL
user.max_net_namespaces = ${MAX_NET_NS}
net.ipv4.neigh.default.gc_thresh1 = ${NEIGH1}
net.ipv4.neigh.default.gc_thresh2 = ${NEIGH2}
net.ipv4.neigh.default.gc_thresh3 = ${NEIGH3}
fs.inotify.max_user_watches = 52428800
fs.inotify.max_user_instances = 5242880
kernel.pid_max = 4194304
kernel.threads-max = 4194304
net.core.somaxconn = 65535
net.core.netdev_max_backlog = ${NETDEV_BACKLOG}
net.core.optmem_max = ${OPTMEM_MAX}
net.core.rmem_max = 134217728
net.core.wmem_max = 134217728
net.ipv4.tcp_rmem = 4096 87380 134217728
net.ipv4.tcp_wmem = 4096 65536 134217728
net.ipv4.ip_forward = 1
net.netfilter.nf_conntrack_max = 33554432
net.netfilter.nf_conntrack_buckets = 8388608
net.ipv4.ipfrag_high_thresh = 268435456
net.ipv4.ipfrag_low_thresh = 134217728
EOF_SYSCTL

modprobe nf_conntrack || true
sysctl --system >/dev/null 2>&1 || true
ip -s -s neigh flush all >/dev/null 2>&1 || true

echo ">> systemd default limits"
mkdir -p /etc/systemd/system.conf.d /etc/systemd/user.conf.d
cat > /etc/systemd/system.conf.d/99-seed-vm-limits.conf <<EOF_SYSTEMD_DEFAULTS
[Manager]
DefaultLimitNOFILE=${LIMIT_NOFILE}
DefaultLimitNPROC=${LIMIT_NPROC}
DefaultTasksMax=infinity
EOF_SYSTEMD_DEFAULTS
cat > /etc/systemd/user.conf.d/99-seed-vm-limits.conf <<EOF_SYSTEMD_USER
[Manager]
DefaultLimitNOFILE=${LIMIT_NOFILE}
DefaultLimitNPROC=${LIMIT_NPROC}
DefaultTasksMax=infinity
EOF_SYSTEMD_USER

echo ">> known service drop-ins if present"
for service in k3s k3s-agent containerd docker; do
    if systemctl list-unit-files | grep -q "^${service}.service"; then
        mkdir -p "/etc/systemd/system/${service}.service.d"
        cat > "/etc/systemd/system/${service}.service.d/99-seed-vm-limits.conf" <<EOF_SERVICE
[Service]
LimitNOFILE=${LIMIT_NOFILE}
LimitNPROC=${LIMIT_NPROC}
TasksMax=infinity
EOF_SERVICE
    fi
done
systemctl daemon-reload

echo ">> cni0 hash_max service for future K3s/flannel bridge"
cat > /usr/local/sbin/seed-vm-cni0-hashmax.sh <<'EOF_TUNE'
#!/usr/bin/env bash
set -euo pipefail
target="${1:-16384}"
for _ in $(seq 1 60); do
    if [ -w /sys/class/net/cni0/bridge/hash_max ]; then
        printf '%s\n' "${target}" > /sys/class/net/cni0/bridge/hash_max
        exit 0
    fi
    sleep 2
done
exit 0
EOF_TUNE
chmod +x /usr/local/sbin/seed-vm-cni0-hashmax.sh

cat > /etc/systemd/system/seed-vm-cni0-hashmax.service <<EOF_UNIT
[Unit]
Description=Apply SEED cni0 bridge hash_max when cni0 exists
After=network-online.target k3s.service k3s-agent.service
Wants=network-online.target

[Service]
Type=oneshot
ExecStart=/usr/local/sbin/seed-vm-cni0-hashmax.sh ${CNI0_HASH_MAX}
RemainAfterExit=yes

[Install]
WantedBy=multi-user.target
EOF_UNIT
systemctl daemon-reload
systemctl enable seed-vm-cni0-hashmax.service >/dev/null 2>&1 || true
if [ -w /sys/class/net/cni0/bridge/hash_max ]; then
    /usr/local/sbin/seed-vm-cni0-hashmax.sh "${CNI0_HASH_MAX}" >/dev/null 2>&1 || true
fi

if [ "${DO_REBOOT}" = "true" ]; then
    systemd-run --on-active=2 /bin/bash -c "reboot" >/dev/null 2>&1 || true
fi

echo "VM limit unlock completed on $(hostname)"
EOF_REMOTE
}

main() {
    if [ "${1:-}" = "-h" ] || [ "${1:-}" = "--help" ]; then
        usage
        exit 0
    fi
    requireCommand python3
    requireCommand ssh
    echo "Using K3s config: ${CONFIG_PATH}"

    while IFS=$'\t' read -r name role ip mac vcpus memory_mb disk_gb; do
        waitForSsh "${name}" "${ip}"
    done < <(nodesInput)

    while IFS=$'\t' read -r name role ip mac vcpus memory_mb disk_gb; do
        unlockOneVm "${name}" "${ip}"
    done < <(nodesInput)

    echo "VM limit unlock completed for all nodes in ${CONFIG_PATH}"
}

main "$@"
'''


def main(argv: list[str] | None = None) -> int:
    """Run this entrypoint with optional argv override for tests."""
    return runEmbeddedShell(Path(__file__), list(sys.argv[1:] if argv is None else argv), SHELL_BODY)


if __name__ == "__main__":
    raise SystemExit(main())
