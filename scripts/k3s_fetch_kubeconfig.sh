#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${SCRIPT_DIR}/env_seedemu.sh"
source "${SCRIPT_DIR}/seed_k8s_cluster_inventory.sh"
seed_load_cluster_inventory

SEED_K3S_MASTER_IP="${SEED_K3S_MASTER_IP:-192.168.122.110}"
SEED_K3S_USER="${SEED_K3S_USER:-ubuntu}"
SEED_K3S_SSH_KEY="${SEED_K3S_SSH_KEY:-$HOME/.ssh/id_ed25519}"
SEED_K3S_CLUSTER_NAME="${SEED_K3S_CLUSTER_NAME:-seedemu-k3s}"

OUTPUT_DIR="${REPO_ROOT}/output/kubeconfigs"
OUTPUT_KUBECONFIG="${OUTPUT_DIR}/${SEED_K3S_CLUSTER_NAME}.yaml"
TMP_KUBECONFIG="${OUTPUT_KUBECONFIG}.tmp"

SSH_OPTS=(
  -o StrictHostKeyChecking=no
  -o UserKnownHostsFile=/dev/null
  -o BatchMode=yes
  -o IdentitiesOnly=yes
  -o IdentityAgent=none
  -o ConnectTimeout=10
  -o ServerAliveInterval=30
  -o ServerAliveCountMax=3
  -i "${SEED_K3S_SSH_KEY}"
)

require_cmd() {
  if ! command -v "$1" >/dev/null 2>&1; then
    echo "Missing required command: $1" >&2
    exit 1
  fi
}

require_cmd ssh
require_cmd sed
require_cmd kubectl

if [ ! -f "${SEED_K3S_SSH_KEY}" ]; then
  echo "SSH key not found: ${SEED_K3S_SSH_KEY}" >&2
  exit 1
fi

mkdir -p "${OUTPUT_DIR}"

if ! ssh "${SSH_OPTS[@]}" "${SEED_K3S_USER}@${SEED_K3S_MASTER_IP}" "sudo -n true" >/dev/null 2>&1; then
  echo "Cannot run passwordless sudo on master: ${SEED_K3S_USER}@${SEED_K3S_MASTER_IP}" >&2
  exit 1
fi

ssh "${SSH_OPTS[@]}" "${SEED_K3S_USER}@${SEED_K3S_MASTER_IP}" \
  "sudo -n cat /etc/rancher/k3s/k3s.yaml" > "${TMP_KUBECONFIG}"

sed "s|127.0.0.1|${SEED_K3S_MASTER_IP}|g" "${TMP_KUBECONFIG}" > "${OUTPUT_KUBECONFIG}"
rm -f "${TMP_KUBECONFIG}"

kubectl --kubeconfig "${OUTPUT_KUBECONFIG}" get nodes -o wide >/dev/null

echo "Kubeconfig fetched: ${OUTPUT_KUBECONFIG}"
