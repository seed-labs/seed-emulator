#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${SCRIPT_DIR}/env_seedemu.sh"

ACTION="${1:-up}"
SEED_KVM_NETWORK="${SEED_KVM_NETWORK:-default}"
SEED_KUBECTL_VERSION="${SEED_KUBECTL_VERSION:-}"

usage() {
    cat <<'EOF'
Usage: scripts/kvm_quickstart.sh [prereq|up|down|status]

Actions:
  prereq  Install host dependencies and prepare libvirt access
  up      prereq + create 3 VMs + install k3s cluster
  down    Destroy/undefine the KVM lab VMs
  status  Show VM status from scripts/kvm_lab.sh

Optional env vars:
  SEED_K3S_CLUSTER_NAME
  SEED_K3S_MASTER_IP / SEED_K3S_WORKER1_IP / SEED_K3S_WORKER2_IP
  SEED_K3S_USER / SEED_K3S_SSH_KEY / SEED_K3S_VERSION
  SEED_REGISTRY_HOST / SEED_REGISTRY_PORT
  SEED_KVM_NETWORK (default: default)
  SEED_KUBECTL_VERSION (example: v1.32.2, default: upstream stable)
EOF
}

require_cmd() {
    if ! command -v "$1" >/dev/null 2>&1; then
        echo "Missing required command: $1" >&2
        exit 1
    fi
}

require_sudo() {
    if [ "${EUID}" -eq 0 ]; then
        return
    fi
    require_cmd sudo
    if sudo -n true >/dev/null 2>&1; then
        return
    fi
    if [ ! -t 0 ]; then
        echo "sudo requires an interactive terminal." >&2
        echo "Run this script directly in your shell session." >&2
        exit 1
    fi
    sudo -v
}

require_apt() {
    if ! command -v apt-get >/dev/null 2>&1; then
        echo "Only apt-based systems are supported by this quickstart." >&2
        echo "Install dependencies manually, then run scripts/kvm_lab.sh and scripts/setup_k3s_cluster.sh." >&2
        exit 1
    fi
}

install_apt_packages() {
    require_apt
    local packages=(
        qemu-kvm
        libvirt-daemon-system
        libvirt-clients
        virtinst
        cloud-image-utils
        curl
        openssh-client
        ca-certificates
        ansible
    )
    local missing=()
    local package_name
    for package_name in "${packages[@]}"; do
        if ! dpkg-query -W -f='${Status}' "${package_name}" 2>/dev/null | grep -q "install ok installed"; then
            missing+=("${package_name}")
        fi
    done

    if [ "${#missing[@]}" -eq 0 ]; then
        echo "[prereq] Host packages already installed."
        return
    fi

    require_sudo
    echo "[prereq] Installing host packages via apt: ${missing[*]}"
    sudo apt-get update
    sudo DEBIAN_FRONTEND=noninteractive apt-get install -y "${missing[@]}"
}

install_kubectl_if_missing() {
    if command -v kubectl >/dev/null 2>&1; then
        return
    fi

    require_sudo
    require_cmd curl
    local version="${SEED_KUBECTL_VERSION}"
    if [ -z "${version}" ]; then
        version="$(curl -fsSL https://dl.k8s.io/release/stable.txt)"
    fi
    echo "[prereq] Installing kubectl ${version} to /usr/local/bin..."
    local tmpdir
    tmpdir="$(mktemp -d)"
    trap 'rm -rf "${tmpdir}"' RETURN
    curl -fsSL -o "${tmpdir}/kubectl" "https://dl.k8s.io/release/${version}/bin/linux/amd64/kubectl"
    chmod +x "${tmpdir}/kubectl"
    sudo install -m 0755 "${tmpdir}/kubectl" /usr/local/bin/kubectl
    trap - RETURN
    rm -rf "${tmpdir}"
}

enable_libvirt_services() {
    require_sudo
    if systemctl list-unit-files | grep -q '^libvirtd.service'; then
        sudo systemctl enable --now libvirtd
    elif systemctl list-unit-files | grep -q '^virtqemud.service'; then
        sudo systemctl enable --now virtqemud
    fi

    sudo virsh net-start "${SEED_KVM_NETWORK}" >/dev/null 2>&1 || true
    sudo virsh net-autostart "${SEED_KVM_NETWORK}" >/dev/null 2>&1 || true
}

ensure_user_in_groups() {
    if [ "${EUID}" -eq 0 ]; then
        return
    fi

    local groups=(libvirt kvm)
    local changed=0
    local group_name
    for group_name in "${groups[@]}"; do
        if getent group "${group_name}" >/dev/null 2>&1 && ! id -nG "${USER}" | tr ' ' '\n' | grep -qx "${group_name}"; then
            echo "[prereq] Adding ${USER} to group ${group_name}"
            sudo usermod -aG "${group_name}" "${USER}"
            changed=1
        fi
    done

    if [ "${changed}" -eq 1 ]; then
        echo ""
        echo "Group membership changed. Run this once and retry:"
        echo "  newgrp libvirt"
        echo "or open a new shell/session before running quickstart up."
    fi
}

check_libvirt_access() {
    if ! virsh net-info "${SEED_KVM_NETWORK}" >/dev/null 2>&1; then
        echo "Current user cannot access libvirt network '${SEED_KVM_NETWORK}' yet." >&2
        echo "If groups were just updated, run 'newgrp libvirt' or re-login and retry." >&2
        exit 1
    fi
}

action_prereq() {
    install_apt_packages
    install_kubectl_if_missing
    enable_libvirt_services
    ensure_user_in_groups
    check_libvirt_access
    echo "[prereq] Host is ready."
}

action_up() {
    action_prereq

    echo "[up] Creating or starting KVM lab VMs..."
    "${REPO_ROOT}/scripts/kvm_lab.sh" up

    local env_file="${REPO_ROOT}/output/kvm_lab/k3s_vm_env.sh"
    if [ ! -f "${env_file}" ]; then
        echo "Missing VM env file: ${env_file}" >&2
        exit 1
    fi

    echo "[up] Installing K3s cluster..."
    set -a
    source "${env_file}"
    set +a
    "${REPO_ROOT}/scripts/setup_k3s_cluster.sh"

    echo ""
    echo "Quickstart completed."
    echo "Kubeconfig: ${REPO_ROOT}/output/kubeconfigs/${SEED_K3S_CLUSTER_NAME:-seedemu-k3s}.yaml"
}

action_down() {
    "${REPO_ROOT}/scripts/kvm_lab.sh" down
}

action_status() {
    "${REPO_ROOT}/scripts/kvm_lab.sh" status
}

case "${ACTION}" in
    prereq)
        action_prereq
        ;;
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
