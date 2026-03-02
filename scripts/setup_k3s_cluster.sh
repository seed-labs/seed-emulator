#!/bin/bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${SCRIPT_DIR}/env_seedemu.sh"

PROJECT_ROOT="${REPO_ROOT}"
INVENTORY_TEMPLATE="${PROJECT_ROOT}/ansible/inventory.yml"
PLAYBOOK_PATH="${PROJECT_ROOT}/ansible/k3s-install.yml"

SEED_K3S_MASTER_IP="${SEED_K3S_MASTER_IP:-192.168.64.10}"
SEED_K3S_WORKER1_IP="${SEED_K3S_WORKER1_IP:-192.168.64.11}"
SEED_K3S_WORKER2_IP="${SEED_K3S_WORKER2_IP:-192.168.64.12}"
SEED_K3S_USER="${SEED_K3S_USER:-parallels}"
SEED_K3S_SSH_KEY="${SEED_K3S_SSH_KEY:-$HOME/.ssh/id_rsa}"
SEED_K3S_VERSION="${SEED_K3S_VERSION:-v1.28.5+k3s1}"
SEED_REGISTRY_HOST="${SEED_REGISTRY_HOST:-${SEED_K3S_MASTER_IP}}"
SEED_REGISTRY_PORT="${SEED_REGISTRY_PORT:-5000}"
SEED_K3S_CLUSTER_NAME="${SEED_K3S_CLUSTER_NAME:-seedemu-k3s}"
SEED_CNI_MASTER_INTERFACE="${SEED_CNI_MASTER_INTERFACE:-eth0}"

SSH_CONNECT_TIMEOUT_SECONDS="${SEED_SSH_CONNECT_TIMEOUT_SECONDS:-10}"
ANSIBLE_TIMEOUT="${SEED_ANSIBLE_TIMEOUT:-1800s}"
SSH_OPTS=(
    -o StrictHostKeyChecking=no
    -o UserKnownHostsFile=/dev/null
    -o BatchMode=yes
    -o ConnectTimeout="${SSH_CONNECT_TIMEOUT_SECONDS}"
    -o ServerAliveInterval=30
    -o ServerAliveCountMax=3
    -i "${SEED_K3S_SSH_KEY}"
)

OUTPUT_KUBECONFIG_DIR="${PROJECT_ROOT}/output/kubeconfigs"
OUTPUT_KUBECONFIG="${OUTPUT_KUBECONFIG_DIR}/${SEED_K3S_CLUSTER_NAME}.yaml"

echo "=============================================="
echo "SEED Emulator - K3s Multi-Node Cluster Setup"
echo "=============================================="
echo "master=${SEED_K3S_MASTER_IP} worker1=${SEED_K3S_WORKER1_IP} worker2=${SEED_K3S_WORKER2_IP}"
echo "user=${SEED_K3S_USER} k3s_version=${SEED_K3S_VERSION}"
echo "registry=${SEED_REGISTRY_HOST}:${SEED_REGISTRY_PORT}"
echo ""

require_cmd() {
    if ! command -v "$1" >/dev/null 2>&1; then
        echo "Missing required command: $1" >&2
        exit 1
    fi
}

run_with_timeout() {
    local duration="$1"
    shift
    if command -v timeout >/dev/null 2>&1; then
        timeout "${duration}" "$@"
    else
        "$@"
    fi
}

check_prerequisites() {
    echo "[1/7] Checking prerequisites"
    require_cmd ansible-playbook
    require_cmd ssh
    require_cmd ping
    require_cmd kubectl
    require_cmd sed

    if [ ! -f "${SEED_K3S_SSH_KEY}" ]; then
        echo "SSH key not found: ${SEED_K3S_SSH_KEY}" >&2
        exit 1
    fi
}

verify_connectivity() {
    echo "[2/7] Verifying VM connectivity"
    local host
    for host in "${SEED_K3S_MASTER_IP}" "${SEED_K3S_WORKER1_IP}" "${SEED_K3S_WORKER2_IP}"; do
        if ping -c 1 -W 2 "${host}" >/dev/null 2>&1; then
            echo "  reachable: ${host}"
        else
            echo "  unreachable: ${host}" >&2
            exit 1
        fi

        if ! run_with_timeout 12s ssh "${SSH_OPTS[@]}" "${SEED_K3S_USER}@${host}" "echo ssh-ok" >/dev/null 2>&1; then
            echo "  ssh failed (non-interactive): ${SEED_K3S_USER}@${host}" >&2
            echo "  Hint: ensure key-based SSH works (no password prompt) and security group allows 22/tcp." >&2
            exit 1
        fi
    done

    if ! run_with_timeout 12s ssh "${SSH_OPTS[@]}" "${SEED_K3S_USER}@${SEED_K3S_MASTER_IP}" "sudo -n true" >/dev/null 2>&1; then
        echo "sudo on master requires password: ${SEED_K3S_USER}@${SEED_K3S_MASTER_IP}" >&2
        echo "This script requires passwordless sudo on remote nodes to avoid hanging." >&2
        exit 1
    fi
}

render_inventory() {
    local output_path="$1"
    sed \
        -e "s|__SEED_K3S_USER__|${SEED_K3S_USER}|g" \
        -e "s|__SEED_K3S_SSH_KEY__|${SEED_K3S_SSH_KEY}|g" \
        -e "s|__SEED_K3S_VERSION__|${SEED_K3S_VERSION}|g" \
        -e "s|__SEED_K3S_MASTER_IP__|${SEED_K3S_MASTER_IP}|g" \
        -e "s|__SEED_K3S_WORKER1_IP__|${SEED_K3S_WORKER1_IP}|g" \
        -e "s|__SEED_K3S_WORKER2_IP__|${SEED_K3S_WORKER2_IP}|g" \
        -e "s|__SEED_REGISTRY_HOST__|${SEED_REGISTRY_HOST}|g" \
        -e "s|__SEED_REGISTRY_PORT__|${SEED_REGISTRY_PORT}|g" \
        -e "s|__SEED_CNI_MASTER_INTERFACE__|${SEED_CNI_MASTER_INTERFACE}|g" \
        "${INVENTORY_TEMPLATE}" > "${output_path}"
}

run_ansible() {
    echo "[3/7] Installing K3s cluster via Ansible"
    local inventory_tmp
    inventory_tmp="$(mktemp)"
    trap 'rm -f "${inventory_tmp}"' RETURN
    render_inventory "${inventory_tmp}"
    ANSIBLE_HOST_KEY_CHECKING=False \
        run_with_timeout "${ANSIBLE_TIMEOUT}" \
        ansible-playbook \
        -i "${inventory_tmp}" \
        "${PLAYBOOK_PATH}" \
        --ssh-common-args="-o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null -o ConnectTimeout=${SSH_CONNECT_TIMEOUT_SECONDS} -o ServerAliveInterval=30 -o ServerAliveCountMax=3 -o BatchMode=yes"
    trap - RETURN
    rm -f "${inventory_tmp}"
}

setup_registry() {
    echo "[4/7] Ensuring private registry on master"
    run_with_timeout 60s ssh "${SSH_OPTS[@]}" "${SEED_K3S_USER}@${SEED_K3S_MASTER_IP}" \
        "docker rm -f registry >/dev/null 2>&1 || true; docker run -d -p ${SEED_REGISTRY_PORT}:5000 --restart=always --name registry registry:2 >/dev/null"
}

fetch_kubeconfig() {
    echo "[5/7] Fetching kubeconfig"
    mkdir -p "${OUTPUT_KUBECONFIG_DIR}"
    run_with_timeout 30s ssh "${SSH_OPTS[@]}" "${SEED_K3S_USER}@${SEED_K3S_MASTER_IP}" \
        "sudo -n cat /etc/rancher/k3s/k3s.yaml" > "${OUTPUT_KUBECONFIG}"
    sed -i "s|127.0.0.1|${SEED_K3S_MASTER_IP}|g" "${OUTPUT_KUBECONFIG}"
    echo "kubeconfig: ${OUTPUT_KUBECONFIG}"
}

verify_cluster_readiness() {
    echo "[6/7] Verifying cluster readiness"
    kubectl --kubeconfig "${OUTPUT_KUBECONFIG}" wait --for=condition=Ready node --all --timeout=300s
    kubectl --kubeconfig "${OUTPUT_KUBECONFIG}" -n kube-system rollout status daemonset/kube-multus-ds --timeout=300s
    kubectl --kubeconfig "${OUTPUT_KUBECONFIG}" get nodes -o wide
}

validate_registry_pull_chain() {
    echo "[7/7] Validating registry pull chain"
    local check_image="${SEED_REGISTRY_HOST}:${SEED_REGISTRY_PORT}/seedemu/registry-check:latest"

    run_with_timeout 120s ssh "${SSH_OPTS[@]}" "${SEED_K3S_USER}@${SEED_K3S_MASTER_IP}" \
        "docker pull --quiet busybox:1.36 >/dev/null && docker tag busybox:1.36 ${check_image} && docker push ${check_image} >/dev/null"

    kubectl --kubeconfig "${OUTPUT_KUBECONFIG}" -n kube-system delete pod registry-self-check --ignore-not-found >/dev/null || true
    kubectl --kubeconfig "${OUTPUT_KUBECONFIG}" -n kube-system run registry-self-check \
        --image="${check_image}" --restart=Never --command -- sh -c 'echo registry-ok' >/dev/null
    kubectl --kubeconfig "${OUTPUT_KUBECONFIG}" -n kube-system wait --for=jsonpath='{.status.phase}'=Succeeded --timeout=180s pod/registry-self-check
    kubectl --kubeconfig "${OUTPUT_KUBECONFIG}" -n kube-system logs pod/registry-self-check
    kubectl --kubeconfig "${OUTPUT_KUBECONFIG}" -n kube-system delete pod registry-self-check --ignore-not-found >/dev/null
}

check_prerequisites
verify_connectivity
run_ansible
setup_registry
fetch_kubeconfig
verify_cluster_readiness
validate_registry_pull_chain

echo ""
echo "K3s cluster is ready."
echo "Use kubeconfig: ${OUTPUT_KUBECONFIG}"
