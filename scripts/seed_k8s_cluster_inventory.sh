#!/usr/bin/env bash

if [ -n "${_SEED_K8S_CLUSTER_INVENTORY_SH:-}" ]; then
  return 0 2>/dev/null || exit 0
fi
_SEED_K8S_CLUSTER_INVENTORY_SH=1

seed_load_cluster_inventory() {
  local inventory_name inventory_path helper_dir helper_py
  helper_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
  helper_py="${helper_dir}/seed_k8s_cluster_inventory.py"

  inventory_name="${1:-${SEED_CLUSTER_INVENTORY:-${SEED_K3S_CLUSTER_NAME:-seedemu-k3s}}}"
  inventory_path="${SEED_CLUSTER_INVENTORY_PATH:-${REPO_ROOT}/configs/clusters/${inventory_name}.yaml}"

  if [ ! -f "${inventory_path}" ]; then
    export SEED_CLUSTER_INVENTORY_LOADED="${SEED_CLUSTER_INVENTORY_LOADED:-false}"
    export SEED_CLUSTER_INVENTORY_PATH="${inventory_path}"
    return 0
  fi

  eval "$(python3 "${helper_py}" --inventory "${inventory_path}" --name "${inventory_name}" --export-shell)"
}
