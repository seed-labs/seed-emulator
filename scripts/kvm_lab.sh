#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${SCRIPT_DIR}/env_seedemu.sh"

ACTION="${1:-up}"

SEED_KVM_NETWORK="${SEED_KVM_NETWORK:-default}"
SEED_KVM_STORAGE_DIR="${SEED_KVM_STORAGE_DIR:-${REPO_ROOT}/output/kvm_lab}"
SEED_KVM_BASE_IMAGE_URL="${SEED_KVM_BASE_IMAGE_URL:-https://cloud-images.ubuntu.com/jammy/current/jammy-server-cloudimg-amd64.img}"
SEED_KVM_BASE_IMAGE_PATH="${SEED_KVM_BASE_IMAGE_PATH:-${SEED_KVM_STORAGE_DIR}/base/jammy-server-cloudimg-amd64.img}"
SEED_KVM_DISK_GB="${SEED_KVM_DISK_GB:-50}"
SEED_KVM_BOOT_TIMEOUT_SECONDS="${SEED_KVM_BOOT_TIMEOUT_SECONDS:-300}"

SEED_K3S_USER="${SEED_K3S_USER:-ubuntu}"
SEED_K3S_SSH_KEY="${SEED_K3S_SSH_KEY:-$HOME/.ssh/id_ed25519}"
SEED_K3S_CLUSTER_NAME="${SEED_K3S_CLUSTER_NAME:-seedemu-k3s}"

SEED_K3S_MASTER_NAME="${SEED_K3S_MASTER_NAME:-seed-k3s-master}"
SEED_K3S_WORKER1_NAME="${SEED_K3S_WORKER1_NAME:-seed-k3s-worker1}"
SEED_K3S_WORKER2_NAME="${SEED_K3S_WORKER2_NAME:-seed-k3s-worker2}"

SEED_K3S_MASTER_IP="${SEED_K3S_MASTER_IP:-192.168.122.110}"
SEED_K3S_WORKER1_IP="${SEED_K3S_WORKER1_IP:-192.168.122.111}"
SEED_K3S_WORKER2_IP="${SEED_K3S_WORKER2_IP:-192.168.122.112}"

SEED_K3S_MASTER_MAC="${SEED_K3S_MASTER_MAC:-52:54:00:64:10:10}"
SEED_K3S_WORKER1_MAC="${SEED_K3S_WORKER1_MAC:-52:54:00:64:10:11}"
SEED_K3S_WORKER2_MAC="${SEED_K3S_WORKER2_MAC:-52:54:00:64:10:12}"

SEED_K3S_MASTER_VCPUS="${SEED_K3S_MASTER_VCPUS:-4}"
SEED_K3S_WORKER1_VCPUS="${SEED_K3S_WORKER1_VCPUS:-2}"
SEED_K3S_WORKER2_VCPUS="${SEED_K3S_WORKER2_VCPUS:-2}"

SEED_K3S_MASTER_MEMORY_MB="${SEED_K3S_MASTER_MEMORY_MB:-6144}"
SEED_K3S_WORKER1_MEMORY_MB="${SEED_K3S_WORKER1_MEMORY_MB:-4096}"
SEED_K3S_WORKER2_MEMORY_MB="${SEED_K3S_WORKER2_MEMORY_MB:-4096}"

VM_NAMES=(
    "${SEED_K3S_MASTER_NAME}"
    "${SEED_K3S_WORKER1_NAME}"
    "${SEED_K3S_WORKER2_NAME}"
)
VM_IPS=(
    "${SEED_K3S_MASTER_IP}"
    "${SEED_K3S_WORKER1_IP}"
    "${SEED_K3S_WORKER2_IP}"
)
VM_MACS=(
    "${SEED_K3S_MASTER_MAC}"
    "${SEED_K3S_WORKER1_MAC}"
    "${SEED_K3S_WORKER2_MAC}"
)
VM_VCPUS=(
    "${SEED_K3S_MASTER_VCPUS}"
    "${SEED_K3S_WORKER1_VCPUS}"
    "${SEED_K3S_WORKER2_VCPUS}"
)
VM_MEMS=(
    "${SEED_K3S_MASTER_MEMORY_MB}"
    "${SEED_K3S_WORKER1_MEMORY_MB}"
    "${SEED_K3S_WORKER2_MEMORY_MB}"
)

SSH_PUB_KEY=""
ENV_FILE="${SEED_KVM_STORAGE_DIR}/k3s_vm_env.sh"

usage() {
    cat <<'EOF'
Usage: scripts/kvm_lab.sh [up|down|status]

Actions:
  up      Create/start 3 KVM VMs for K3s (master + 2 workers)
  down    Destroy and undefine those VMs
  status  Show VM state and current IP leases

Important env vars (optional):
  SEED_K3S_MASTER_IP / SEED_K3S_WORKER1_IP / SEED_K3S_WORKER2_IP
  SEED_K3S_USER
  SEED_K3S_SSH_KEY
  SEED_KVM_NETWORK (default: libvirt network "default")
  SEED_KVM_STORAGE_DIR
EOF
}

require_cmd() {
    if ! command -v "$1" >/dev/null 2>&1; then
        echo "Missing required command: $1" >&2
        exit 1
    fi
}

domain_exists() {
    local domain="$1"
    virsh dominfo "${domain}" >/dev/null 2>&1
}

domain_running() {
    local domain="$1"
    virsh domstate "${domain}" 2>/dev/null | grep -qi "running"
}

ensure_network() {
    if ! virsh net-info "${SEED_KVM_NETWORK}" >/dev/null 2>&1; then
        echo "Libvirt network not found: ${SEED_KVM_NETWORK}" >&2
        exit 1
    fi

    virsh net-start "${SEED_KVM_NETWORK}" >/dev/null 2>&1 || true
    virsh net-autostart "${SEED_KVM_NETWORK}" >/dev/null 2>&1 || true
}

prepare_dirs() {
    mkdir -p "${SEED_KVM_STORAGE_DIR}/base"
    mkdir -p "${SEED_KVM_STORAGE_DIR}/disks"
    mkdir -p "${SEED_KVM_STORAGE_DIR}/cloud-init"
}

load_ssh_pubkey() {
    if [ -f "${SEED_K3S_SSH_KEY}.pub" ]; then
        SSH_PUB_KEY="$(tr -d '\n' < "${SEED_K3S_SSH_KEY}.pub")"
        return
    fi

    if [ -f "${SEED_K3S_SSH_KEY}" ]; then
        SSH_PUB_KEY="$(ssh-keygen -y -f "${SEED_K3S_SSH_KEY}" 2>/dev/null | tr -d '\n')"
        if [ -n "${SSH_PUB_KEY}" ]; then
            return
        fi
    fi

    echo "Cannot read SSH key. Set SEED_K3S_SSH_KEY to a valid private key path." >&2
    exit 1
}

download_base_image() {
    if [ -f "${SEED_KVM_BASE_IMAGE_PATH}" ]; then
        return
    fi

    echo "Downloading Ubuntu cloud image to ${SEED_KVM_BASE_IMAGE_PATH}"
    curl -fL "${SEED_KVM_BASE_IMAGE_URL}" -o "${SEED_KVM_BASE_IMAGE_PATH}"
}

update_dhcp_host() {
    local vm_name="$1"
    local vm_ip="$2"
    local vm_mac="$3"
    local host_xml
    host_xml="<host mac='${vm_mac}' name='${vm_name}' ip='${vm_ip}'/>"

    virsh net-update "${SEED_KVM_NETWORK}" delete ip-dhcp-host "${host_xml}" --live --config >/dev/null 2>&1 || true
    if ! virsh net-update "${SEED_KVM_NETWORK}" add ip-dhcp-host "${host_xml}" --live --config >/dev/null 2>&1; then
        echo "Warning: failed to add DHCP lease for ${vm_name} (${vm_ip}) on network ${SEED_KVM_NETWORK}" >&2
    fi
}

remove_dhcp_host() {
    local vm_name="$1"
    local vm_ip="$2"
    local vm_mac="$3"
    local host_xml
    host_xml="<host mac='${vm_mac}' name='${vm_name}' ip='${vm_ip}'/>"
    virsh net-update "${SEED_KVM_NETWORK}" delete ip-dhcp-host "${host_xml}" --live --config >/dev/null 2>&1 || true
}

create_vm_cloud_init() {
    local vm_name="$1"
    local vm_dir="${SEED_KVM_STORAGE_DIR}/cloud-init/${vm_name}"
    local user_data="${vm_dir}/user-data.yaml"
    local meta_data="${vm_dir}/meta-data.yaml"

    mkdir -p "${vm_dir}"

    cat > "${user_data}" <<EOF
#cloud-config
users:
  - default
  - name: ${SEED_K3S_USER}
    shell: /bin/bash
    sudo: ALL=(ALL) NOPASSWD:ALL
    groups: [sudo]
    ssh_authorized_keys:
      - ${SSH_PUB_KEY}
package_update: true
packages:
  - qemu-guest-agent
runcmd:
  - [ systemctl, enable, --now, qemu-guest-agent ]
EOF

    cat > "${meta_data}" <<EOF
instance-id: ${vm_name}
local-hostname: ${vm_name}
EOF
}

create_vm_disk() {
    local vm_name="$1"
    local vm_disk="${SEED_KVM_STORAGE_DIR}/disks/${vm_name}.qcow2"

    if [ -f "${vm_disk}" ]; then
        return
    fi

    qemu-img create -f qcow2 -F qcow2 -b "${SEED_KVM_BASE_IMAGE_PATH}" "${vm_disk}" "${SEED_KVM_DISK_GB}G" >/dev/null
}

create_vm() {
    local vm_name="$1"
    local vm_ip="$2"
    local vm_mac="$3"
    local vm_vcpus="$4"
    local vm_mem="$5"
    local vm_disk="${SEED_KVM_STORAGE_DIR}/disks/${vm_name}.qcow2"
    local vm_cloud_dir="${SEED_KVM_STORAGE_DIR}/cloud-init/${vm_name}"

    if domain_exists "${vm_name}"; then
        echo "VM exists: ${vm_name}"
        if ! domain_running "${vm_name}"; then
            virsh start "${vm_name}" >/dev/null
        fi
        return
    fi

    echo "Creating VM: ${vm_name} (${vm_ip})"
    virt-install \
        --name "${vm_name}" \
        --memory "${vm_mem}" \
        --vcpus "${vm_vcpus}" \
        --cpu host-passthrough \
        --import \
        --os-variant generic \
        --network "network=${SEED_KVM_NETWORK},model=virtio,mac=${vm_mac}" \
        --disk "path=${vm_disk},format=qcow2,bus=virtio" \
        --graphics none \
        --noautoconsole \
        --cloud-init "user-data=${vm_cloud_dir}/user-data.yaml,meta-data=${vm_cloud_dir}/meta-data.yaml" >/dev/null
}

wait_for_ssh() {
    local vm_name="$1"
    local vm_ip="$2"
    local timeout="${SEED_KVM_BOOT_TIMEOUT_SECONDS}"
    local elapsed=0

    while [ "${elapsed}" -lt "${timeout}" ]; do
        if ssh -o StrictHostKeyChecking=no \
               -o UserKnownHostsFile=/dev/null \
               -o BatchMode=yes \
               -o ConnectTimeout=3 \
               -i "${SEED_K3S_SSH_KEY}" \
               "${SEED_K3S_USER}@${vm_ip}" "echo ok" >/dev/null 2>&1; then
            echo "SSH ready: ${vm_name} (${vm_ip})"
            return 0
        fi
        sleep 5
        elapsed=$((elapsed + 5))
    done

    echo "Timeout waiting for SSH on ${vm_name} (${vm_ip})" >&2
    return 1
}

write_env_file() {
    cat > "${ENV_FILE}" <<EOF
#!/usr/bin/env bash
export SEED_K3S_CLUSTER_NAME="${SEED_K3S_CLUSTER_NAME}"
export SEED_K3S_MASTER_IP="${SEED_K3S_MASTER_IP}"
export SEED_K3S_WORKER1_IP="${SEED_K3S_WORKER1_IP}"
export SEED_K3S_WORKER2_IP="${SEED_K3S_WORKER2_IP}"
export SEED_K3S_USER="${SEED_K3S_USER}"
export SEED_K3S_SSH_KEY="${SEED_K3S_SSH_KEY}"
export SEED_REGISTRY_HOST="${SEED_K3S_MASTER_IP}"
export SEED_REGISTRY_PORT="\${SEED_REGISTRY_PORT:-5000}"
EOF
    chmod +x "${ENV_FILE}"
}

action_up() {
    require_cmd virsh
    require_cmd virt-install
    require_cmd qemu-img
    require_cmd curl
    require_cmd ssh
    require_cmd ssh-keygen

    prepare_dirs
    load_ssh_pubkey
    ensure_network
    download_base_image

    local i
    for i in "${!VM_NAMES[@]}"; do
        update_dhcp_host "${VM_NAMES[$i]}" "${VM_IPS[$i]}" "${VM_MACS[$i]}"
        create_vm_cloud_init "${VM_NAMES[$i]}"
        create_vm_disk "${VM_NAMES[$i]}"
        create_vm "${VM_NAMES[$i]}" "${VM_IPS[$i]}" "${VM_MACS[$i]}" "${VM_VCPUS[$i]}" "${VM_MEMS[$i]}"
    done

    echo "Waiting for SSH availability..."
    for i in "${!VM_NAMES[@]}"; do
        wait_for_ssh "${VM_NAMES[$i]}" "${VM_IPS[$i]}"
    done

    write_env_file
    echo ""
    echo "KVM lab is ready."
    echo "Environment file: ${ENV_FILE}"
    echo ""
    echo "Next:"
    echo "  source ${ENV_FILE}"
    echo "  cd ${REPO_ROOT}"
    echo "  ./scripts/setup_k3s_cluster.sh"
}

action_down() {
    require_cmd virsh

    local i vm_name vm_ip vm_mac vm_disk vm_cloud_dir
    for i in "${!VM_NAMES[@]}"; do
        vm_name="${VM_NAMES[$i]}"
        vm_ip="${VM_IPS[$i]}"
        vm_mac="${VM_MACS[$i]}"
        vm_disk="${SEED_KVM_STORAGE_DIR}/disks/${vm_name}.qcow2"
        vm_cloud_dir="${SEED_KVM_STORAGE_DIR}/cloud-init/${vm_name}"

        if domain_exists "${vm_name}"; then
            virsh destroy "${vm_name}" >/dev/null 2>&1 || true
            virsh undefine "${vm_name}" --nvram >/dev/null 2>&1 || virsh undefine "${vm_name}" >/dev/null 2>&1 || true
        fi

        remove_dhcp_host "${vm_name}" "${vm_ip}" "${vm_mac}"
        rm -f "${vm_disk}"
        rm -rf "${vm_cloud_dir}"
    done

    echo "KVM lab VMs removed."
}

action_status() {
    require_cmd virsh

    local i vm_name
    for i in "${!VM_NAMES[@]}"; do
        vm_name="${VM_NAMES[$i]}"
        if domain_exists "${vm_name}"; then
            echo "=== ${vm_name} ==="
            virsh domstate "${vm_name}" | sed 's/^/state: /'
            virsh domifaddr "${vm_name}" --source lease | sed 's/^/  /' || true
        else
            echo "=== ${vm_name} ==="
            echo "state: not-defined"
        fi
    done
}

case "${ACTION}" in
    up)
        action_up
        ;;
    down)
        action_down
        ;;
    status)
        action_status
        ;;
    -h|--help|help)
        usage
        ;;
    *)
        echo "Unknown action: ${ACTION}" >&2
        usage
        exit 1
        ;;
esac
