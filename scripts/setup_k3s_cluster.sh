#!/bin/bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${SCRIPT_DIR}/env_seedemu.sh"
source "${SCRIPT_DIR}/seed_k8s_cluster_inventory.sh"
seed_load_cluster_inventory

PROJECT_ROOT="${REPO_ROOT}"
INVENTORY_TEMPLATE="${PROJECT_ROOT}/ansible/inventory.yml"
PLAYBOOK_PATH="${PROJECT_ROOT}/ansible/k3s-install.yml"

SEED_K3S_MASTER_IP="${SEED_K3S_MASTER_IP:-192.168.122.110}"
SEED_K3S_WORKER1_IP="${SEED_K3S_WORKER1_IP:-192.168.122.111}"
SEED_K3S_WORKER2_IP="${SEED_K3S_WORKER2_IP:-192.168.122.112}"
SEED_K3S_USER="${SEED_K3S_USER:-ubuntu}"
SEED_K3S_SSH_KEY="${SEED_K3S_SSH_KEY:-$HOME/.ssh/id_ed25519}"
SEED_K3S_VERSION="${SEED_K3S_VERSION:-v1.28.5+k3s1}"
SEED_REGISTRY_HOST="${SEED_REGISTRY_HOST:-${SEED_K3S_MASTER_IP}}"
SEED_REGISTRY_PORT="${SEED_REGISTRY_PORT:-5000}"
SEED_K3S_CLUSTER_NAME="${SEED_K3S_CLUSTER_NAME:-seedemu-k3s}"
SEED_CNI_MASTER_INTERFACE="${SEED_CNI_MASTER_INTERFACE:-}"
SEED_DOCKER_IO_MIRROR_ENDPOINT="${SEED_DOCKER_IO_MIRROR_ENDPOINT:-https://docker.m.daocloud.io}"

SSH_CONNECT_TIMEOUT_SECONDS="${SEED_SSH_CONNECT_TIMEOUT_SECONDS:-10}"
ANSIBLE_TIMEOUT="${SEED_ANSIBLE_TIMEOUT:-1800s}"
SSH_OPTS=(
    -o StrictHostKeyChecking=no
    -o UserKnownHostsFile=/dev/null
    -o LogLevel=ERROR
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
        if ! run_with_timeout 12s ssh "${SSH_OPTS[@]}" "${SEED_K3S_USER}@${host}" "sudo -n true" >/dev/null 2>&1; then
            echo "sudo requires password: ${SEED_K3S_USER}@${host}" >&2
            echo "This script requires passwordless sudo on remote nodes to avoid hanging." >&2
            exit 1
        fi
    done

    if [ -z "${SEED_CNI_MASTER_INTERFACE}" ]; then
        local master_iface worker1_iface worker2_iface
        master_iface="$(run_with_timeout 12s ssh "${SSH_OPTS[@]}" "${SEED_K3S_USER}@${SEED_K3S_MASTER_IP}" "ip -o -4 route show to default | sed -n '1{s/.* dev \\([^ ]*\\).*/\\1/p}'" || true)"
        worker1_iface="$(run_with_timeout 12s ssh "${SSH_OPTS[@]}" "${SEED_K3S_USER}@${SEED_K3S_WORKER1_IP}" "ip -o -4 route show to default | sed -n '1{s/.* dev \\([^ ]*\\).*/\\1/p}'" || true)"
        worker2_iface="$(run_with_timeout 12s ssh "${SSH_OPTS[@]}" "${SEED_K3S_USER}@${SEED_K3S_WORKER2_IP}" "ip -o -4 route show to default | sed -n '1{s/.* dev \\([^ ]*\\).*/\\1/p}'" || true)"
        if [ -z "${master_iface}" ] || [ -z "${worker1_iface}" ] || [ -z "${worker2_iface}" ]; then
            echo "Failed to detect default-route interface on one or more nodes; set SEED_CNI_MASTER_INTERFACE manually." >&2
            exit 1
        fi
        if [ "${master_iface}" != "${worker1_iface}" ] || [ "${master_iface}" != "${worker2_iface}" ]; then
            echo "Default-route interface mismatch across nodes: master=${master_iface} worker1=${worker1_iface} worker2=${worker2_iface}" >&2
            echo "Set SEED_CNI_MASTER_INTERFACE manually and ensure it exists on all nodes." >&2
            exit 1
        fi
        SEED_CNI_MASTER_INTERFACE="${master_iface}"
    fi
    echo "  cni_master_interface=${SEED_CNI_MASTER_INTERFACE}"
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
        -e "s|__SEED_DOCKER_IO_MIRROR_ENDPOINT__|${SEED_DOCKER_IO_MIRROR_ENDPOINT}|g" \
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
        "set -euo pipefail; sudo -n docker rm -f registry >/dev/null 2>&1 || true; \
         if ! sudo -n docker image inspect registry:2 >/dev/null 2>&1; then \
           sudo -n docker pull registry:2 >/dev/null 2>&1 || (sudo -n docker pull docker.m.daocloud.io/library/registry:2 >/dev/null && sudo -n docker tag docker.m.daocloud.io/library/registry:2 registry:2 >/dev/null); \
         fi; \
         sudo -n docker run -d --network host --restart=always --name registry \
           -e REGISTRY_HTTP_ADDR=0.0.0.0:${SEED_REGISTRY_PORT} registry:2 >/dev/null"
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
    patch_multus_atomic_shim_install
    patch_multus_k3s_hostpaths
    patch_multus_rbac
    ensure_cni_plugins
    kubectl --kubeconfig "${OUTPUT_KUBECONFIG}" -n kube-system rollout status daemonset/kube-multus-ds --timeout=300s
    kubectl --kubeconfig "${OUTPUT_KUBECONFIG}" get nodes -o wide
}

patch_multus_atomic_shim_install() {
    if ! kubectl --kubeconfig "${OUTPUT_KUBECONFIG}" -n kube-system get daemonset/kube-multus-ds >/dev/null 2>&1; then
        return
    fi

    local cmd0
    cmd0="$(kubectl --kubeconfig "${OUTPUT_KUBECONFIG}" -n kube-system get daemonset/kube-multus-ds -o jsonpath='{.spec.template.spec.initContainers[?(@.name=="install-multus-binary")].command[0]}' 2>/dev/null || true)"
    if [ "${cmd0}" = "/bin/sh" ] || [ "${cmd0}" = "sh" ]; then
        echo "  multus shim installer already uses atomic install"
        return
    fi

    echo "  patching multus shim installer to avoid 'Text file busy' (atomic mv)"
    kubectl --kubeconfig "${OUTPUT_KUBECONFIG}" -n kube-system patch daemonset/kube-multus-ds --type='strategic' -p "$(
        cat <<'JSON'
{
  "spec": {
    "template": {
      "spec": {
        "initContainers": [
          {
            "name": "install-multus-binary",
            "command": ["/bin/sh", "-c"],
            "args": [
              "set -eu; src=/usr/src/multus-cni/bin/multus-shim; dst=/host/opt/cni/bin/multus-shim; tmp=/host/opt/cni/bin/.multus-shim.tmp.$$; cp \"$src\" \"$tmp\"; chmod 0755 \"$tmp\"; mv -f \"$tmp\" \"$dst\";"
            ]
          }
        ]
      }
    }
  }
}

JSON
    )" >/dev/null || true
}

patch_multus_k3s_hostpaths() {
    if ! kubectl --kubeconfig "${OUTPUT_KUBECONFIG}" -n kube-system get daemonset/kube-multus-ds >/dev/null 2>&1; then
        return
    fi

    local conf_dir bin_dir
    conf_dir="$(run_with_timeout 12s ssh "${SSH_OPTS[@]}" "${SEED_K3S_USER}@${SEED_K3S_MASTER_IP}" \
        "sudo -n sh -c 'sed -n \"s/^\\s*conf_dir\\s*=\\s*\\\"\\([^\\\"]*\\)\\\".*/\\1/p\" /var/lib/rancher/k3s/agent/etc/containerd/config.toml | head -n 1' 2>/dev/null" \
        || true)"
    bin_dir="$(run_with_timeout 12s ssh "${SSH_OPTS[@]}" "${SEED_K3S_USER}@${SEED_K3S_MASTER_IP}" \
        "sudo -n sh -c 'if [ -d /var/lib/rancher/k3s/data/current/bin ]; then echo /var/lib/rancher/k3s/data/current/bin; else sed -n \"s/^\\s*bin_dir\\s*=\\s*\\\"\\([^\\\"]*\\)\\\".*/\\1/p\" /var/lib/rancher/k3s/agent/etc/containerd/config.toml | head -n 1; fi' 2>/dev/null" \
        || true)"

    if [ -z "${conf_dir}" ] || [ -z "${bin_dir}" ]; then
        echo "  warning: unable to detect k3s CNI conf/bin dirs; skipping multus hostpath patch" >&2
        return
    fi

    local current_cni current_cnibin
    current_cni="$(kubectl --kubeconfig "${OUTPUT_KUBECONFIG}" -n kube-system get daemonset/kube-multus-ds \
        -o jsonpath='{.spec.template.spec.volumes[?(@.name=="cni")].hostPath.path}' 2>/dev/null || true)"
    current_cnibin="$(kubectl --kubeconfig "${OUTPUT_KUBECONFIG}" -n kube-system get daemonset/kube-multus-ds \
        -o jsonpath='{.spec.template.spec.volumes[?(@.name=="cnibin")].hostPath.path}' 2>/dev/null || true)"

    if [ "${current_cni}" = "${conf_dir}" ] && [ "${current_cnibin}" = "${bin_dir}" ]; then
        echo "  multus hostpaths already match k3s: cni=${conf_dir} cnibin=${bin_dir}"
        return
    fi

    echo "  patching multus hostpaths for k3s: cni=${conf_dir} cnibin=${bin_dir}"
    kubectl --kubeconfig "${OUTPUT_KUBECONFIG}" -n kube-system patch daemonset/kube-multus-ds --type='strategic' -p "$(
        cat <<JSON
{
  "spec": {
    "template": {
      "spec": {
        "volumes": [
          {"name": "cni", "hostPath": {"path": "${conf_dir}"}},
          {"name": "cnibin", "hostPath": {"path": "${bin_dir}"}}
        ]
      }
    }
  }
}
JSON
    )" >/dev/null || true
    kubectl --kubeconfig "${OUTPUT_KUBECONFIG}" -n kube-system rollout restart daemonset/kube-multus-ds >/dev/null 2>&1 || true
}

patch_multus_rbac() {
    if ! kubectl --kubeconfig "${OUTPUT_KUBECONFIG}" -n kube-system get daemonset/kube-multus-ds >/dev/null 2>&1; then
        return
    fi

    local can_list
    can_list="$(kubectl --kubeconfig "${OUTPUT_KUBECONFIG}" auth can-i list pods -n kube-system --as system:serviceaccount:kube-system:multus 2>/dev/null || echo no)"
    if [ "${can_list}" = "yes" ]; then
        echo "  multus RBAC ok (can list pods)"
        return
    fi

    echo "  patching multus RBAC (allow list/watch pods)"
    kubectl --kubeconfig "${OUTPUT_KUBECONFIG}" apply -f - <<'YAML' >/dev/null
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRole
metadata:
  name: multus
rules:
- apiGroups:
  - k8s.cni.cncf.io
  resources:
  - '*'
  verbs:
  - '*'
- apiGroups:
  - ""
  resources:
  - pods
  - pods/status
  verbs:
  - get
  - list
  - watch
  - update
- apiGroups:
  - ""
  - events.k8s.io
  resources:
  - events
  verbs:
  - create
  - patch
  - update
YAML
    kubectl --kubeconfig "${OUTPUT_KUBECONFIG}" -n kube-system rollout restart daemonset/kube-multus-ds >/dev/null 2>&1 || true
}

ensure_cni_plugins() {
    local -a required_plugins
    required_plugins=(macvlan ipvlan static)

    echo "  ensuring CNI plugins: ${required_plugins[*]}"
    local host
    for host in "${SEED_K3S_MASTER_IP}" "${SEED_K3S_WORKER1_IP}" "${SEED_K3S_WORKER2_IP}"; do
        if run_with_timeout 12s ssh "${SSH_OPTS[@]}" "${SEED_K3S_USER}@${host}" \
            "set -euo pipefail; for p in ${required_plugins[*]}; do test -x \"/opt/cni/bin/\$p\"; done" >/dev/null 2>&1; then
            echo "  ${host}: plugins already present"
            continue
        fi

        echo "  ${host}: installing containernetworking-plugins + linking /opt/cni/bin"
        run_with_timeout 240s ssh "${SSH_OPTS[@]}" "${SEED_K3S_USER}@${host}" \
            "set -euo pipefail; \
             export DEBIAN_FRONTEND=noninteractive; \
             sudo -n apt-get update -y >/dev/null; \
             sudo -n apt-get install -y containernetworking-plugins >/dev/null; \
             sudo -n mkdir -p /opt/cni/bin; \
             for p in ${required_plugins[*]}; do \
               if [ -x \"/usr/lib/cni/\$p\" ]; then sudo -n ln -sf \"/usr/lib/cni/\$p\" \"/opt/cni/bin/\$p\"; fi; \
             done"
    done
}

validate_registry_pull_chain() {
    echo "[7/7] Validating registry pull chain"
    local check_image="${SEED_REGISTRY_HOST}:${SEED_REGISTRY_PORT}/seedemu/registry-check:latest"

    run_with_timeout 120s ssh "${SSH_OPTS[@]}" "${SEED_K3S_USER}@${SEED_K3S_MASTER_IP}" \
        "set -euo pipefail; \
         if ! sudo -n docker pull --quiet busybox:1.36 >/dev/null 2>&1; then \
           sudo -n docker pull --quiet docker.m.daocloud.io/library/busybox:1.36 >/dev/null && sudo -n docker tag docker.m.daocloud.io/library/busybox:1.36 busybox:1.36 >/dev/null; \
         fi; \
         sudo -n docker tag busybox:1.36 ${check_image} >/dev/null && sudo -n docker push ${check_image} >/dev/null"

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
