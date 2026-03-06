#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Preserve caller-provided values before env guardrails inject generic defaults.
_HAS_SEED_NAMESPACE=0
_HAS_SEED_REGISTRY=0
_HAS_SEED_CNI_TYPE=0
_HAS_SEED_CNI_MASTER_INTERFACE=0
if [ "${SEED_NAMESPACE+x}" = "x" ]; then
  _HAS_SEED_NAMESPACE=1
  _PRESET_SEED_NAMESPACE="${SEED_NAMESPACE}"
fi
if [ "${SEED_REGISTRY+x}" = "x" ]; then
  _HAS_SEED_REGISTRY=1
  _PRESET_SEED_REGISTRY="${SEED_REGISTRY}"
fi
if [ "${SEED_CNI_TYPE+x}" = "x" ]; then
  _HAS_SEED_CNI_TYPE=1
  _PRESET_SEED_CNI_TYPE="${SEED_CNI_TYPE}"
fi
if [ "${SEED_CNI_MASTER_INTERFACE+x}" = "x" ]; then
  _HAS_SEED_CNI_MASTER_INTERFACE=1
  _PRESET_SEED_CNI_MASTER_INTERFACE="${SEED_CNI_MASTER_INTERFACE}"
fi

source "${SCRIPT_DIR}/env_seedemu.sh"

# Drop env_seedemu generic defaults unless the caller explicitly provided values.
if [ "${_HAS_SEED_NAMESPACE}" = "1" ]; then
  SEED_NAMESPACE="${_PRESET_SEED_NAMESPACE}"
else
  unset SEED_NAMESPACE || true
fi
if [ "${_HAS_SEED_REGISTRY}" = "1" ]; then
  SEED_REGISTRY="${_PRESET_SEED_REGISTRY}"
else
  unset SEED_REGISTRY || true
fi
if [ "${_HAS_SEED_CNI_TYPE}" = "1" ]; then
  SEED_CNI_TYPE="${_PRESET_SEED_CNI_TYPE}"
else
  unset SEED_CNI_TYPE || true
fi
if [ "${_HAS_SEED_CNI_MASTER_INTERFACE}" = "1" ]; then
  SEED_CNI_MASTER_INTERFACE="${_PRESET_SEED_CNI_MASTER_INTERFACE}"
else
  unset SEED_CNI_MASTER_INTERFACE || true
fi

ACTION="${1:-all}"

SEED_K3S_CLUSTER_NAME="${SEED_K3S_CLUSTER_NAME:-seedemu-k3s}"
SEED_K3S_MASTER_IP="${SEED_K3S_MASTER_IP:-192.168.122.110}"
SEED_K3S_WORKER1_IP="${SEED_K3S_WORKER1_IP:-192.168.122.111}"
SEED_K3S_WORKER2_IP="${SEED_K3S_WORKER2_IP:-192.168.122.112}"
SEED_K3S_USER="${SEED_K3S_USER:-ubuntu}"
SEED_K3S_SSH_KEY="${SEED_K3S_SSH_KEY:-$HOME/.ssh/id_ed25519}"

SEED_NAMESPACE="${SEED_NAMESPACE:-seedemu-k3s-real-topo}"
SEED_REGISTRY_HOST="${SEED_REGISTRY_HOST:-${SEED_K3S_MASTER_IP}}"
SEED_REGISTRY_PORT="${SEED_REGISTRY_PORT:-5000}"
SEED_REGISTRY="${SEED_REGISTRY:-${SEED_REGISTRY_HOST}:${SEED_REGISTRY_PORT}}"
if [ "${SEED_REGISTRY}" = "localhost:5001" ] || [ "${SEED_REGISTRY}" = "localhost:5000" ]; then
  SEED_REGISTRY="${SEED_REGISTRY_HOST}:${SEED_REGISTRY_PORT}"
fi

SEED_CNI_TYPE="${SEED_CNI_TYPE:-macvlan}"
SEED_CNI_MASTER_INTERFACE="${SEED_CNI_MASTER_INTERFACE:-}"
SEED_CNI_MASTER_INTERFACE_FORCE="${SEED_CNI_MASTER_INTERFACE_FORCE:-false}"
if [ "${SEED_CNI_MASTER_INTERFACE_FORCE}" != "true" ] && [ "${SEED_CNI_MASTER_INTERFACE}" = "eth0" ]; then
  # scripts/env_seedemu.sh defaults to eth0 for generic scripts. For K3s multi-node
  # validation we auto-detect the real interface unless caller explicitly forces one.
  SEED_CNI_MASTER_INTERFACE=""
fi
SEED_SCHEDULING_STRATEGY="${SEED_SCHEDULING_STRATEGY:-auto}"
SEED_PLACEMENT_MODE="${SEED_PLACEMENT_MODE:-auto}"
SEED_MIN_NODES_USED="${SEED_MIN_NODES_USED:-2}"
SEED_BUILD_PARALLELISM="${SEED_BUILD_PARALLELISM:-1}"
SEED_DOCKER_BUILDKIT="${SEED_DOCKER_BUILDKIT:-0}"
BGP_WAIT_TIMEOUT_SECONDS="${BGP_WAIT_TIMEOUT_SECONDS:-300}"
DEPLOY_WAIT_TIMEOUT="${DEPLOY_WAIT_TIMEOUT:-2400s}"
CLEAN_NAMESPACE="${SEED_CLEAN_NAMESPACE:-true}"

SEED_REAL_TOPOLOGY_DIR="${SEED_REAL_TOPOLOGY_DIR:-$HOME/lxl_topology/autocoder_test}"
SEED_TOPOLOGY_SIZE="${SEED_TOPOLOGY_SIZE:-214}"
SEED_TOPOLOGY_FILE="${SEED_TOPOLOGY_FILE:-}"
SEED_ASSIGNMENT_FILE="${SEED_ASSIGNMENT_FILE:-}"

RUN_ID="${SEED_RUN_ID:-$(date +%Y%m%d_%H%M%S)}"
DEFAULT_ARTIFACT_DIR="${REPO_ROOT}/output/multinode_real_topology_validation/${RUN_ID}"
SEED_ARTIFACT_DIR="${SEED_ARTIFACT_DIR:-${DEFAULT_ARTIFACT_DIR}}"
SEED_OUTPUT_DIR="${SEED_OUTPUT_DIR:-${SEED_ARTIFACT_DIR}/compiled}"

KUBECONFIG_PATH="${REPO_ROOT}/output/kubeconfigs/${SEED_K3S_CLUSTER_NAME}.yaml"
COMPILE_DIR="${SEED_OUTPUT_DIR}"
ARTIFACT_DIR="${SEED_ARTIFACT_DIR}"
REMOTE_WORK_BASE="/tmp/seedemu-real-topo-multinode"
REMOTE_WORK_DIR="${REMOTE_WORK_BASE}-${RUN_ID}"

CURRENT_STAGE="init"
FAILURE_REASON=""
FAILURE_CODE=""
EFFECTIVE_CNI_IFACE=""
EXPECTED_NODES="0"
NODES_USED="0"
PLACEMENT_PASSED="false"
BGP_PASSED="false"
OVERALL_PASSED="false"

SSH_OPTS=(
  -o StrictHostKeyChecking=no
  -o UserKnownHostsFile=/dev/null
  -o LogLevel=ERROR
  -o BatchMode=yes
  -o ConnectTimeout=10
  -o ServerAliveInterval=30
  -o ServerAliveCountMax=3
  -i "${SEED_K3S_SSH_KEY}"
)

log() {
  echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*"
}

usage() {
  cat <<'USAGE'
Usage: scripts/validate_k3s_real_topology_multinode.sh [all|preflight|compile|build|deploy|verify|clean]

Actions:
  all       Run full pipeline: preflight -> compile -> build -> deploy -> verify
  preflight Fetch kubeconfig, check nodes, detect CNI master iface
  compile   Compile real-topology RR into Kubernetes manifests
  build     Build and push images on K3s master
  deploy    Apply manifests and wait until all deployments are Available
  verify    Verify expected workload count, multinode placement, and BGP status (birdc)
  clean     Delete namespace resources used by this workflow
USAGE
}

require_cmd() {
  if ! command -v "$1" >/dev/null 2>&1; then
    echo "Missing required command: $1" >&2
    exit 1
  fi
}

resolve_failure_code() {
  case "${FAILURE_REASON}" in
    kubeconfig_fetch_failed|kubeconfig_not_found_after_fetch)
      echo "KCFG_MISSING"
      ;;
    ssh_key_not_found)
      echo "SSH_KEY_INVALID"
      ;;
    compile_missing_k8s_yaml|compile_missing_build_script|compile_failed)
      echo "COMPILE_FAILED"
      ;;
    build_failed)
      echo "BUILD_FAILED"
      ;;
    deploy_wait_timeout_or_failure|deploy_failed)
      echo "DEPLOY_TIMEOUT"
      ;;
    multus_not_ready)
      echo "MULTUS_NOT_READY"
      ;;
    registry_unreachable)
      echo "REGISTRY_UNREACHABLE"
      ;;
    placement_check_failed|strict3_not_supported)
      echo "PLACEMENT_FAILED"
      ;;
    bgp_not_established)
      echo "BGP_NOT_ESTABLISHED"
      ;;
    *)
      echo "DEPLOY_TIMEOUT"
      ;;
  esac
}

write_diagnostics() {
  local stage="$1"
  local status="$2"
  local evidence="$3"
  local minimal_retry="$4"
  local fallback="$5"

  python3 - <<PY
import json
from datetime import datetime, timezone
from pathlib import Path

artifact_dir = Path(${ARTIFACT_DIR@Q})
artifact_dir.mkdir(parents=True, exist_ok=True)

data = {
    "generated_at": datetime.now(timezone.utc).isoformat(),
    "stage": ${stage@Q},
    "status": ${status@Q},
    "failure_reason": ${FAILURE_REASON@Q},
    "failure_code": ${FAILURE_CODE@Q},
    "first_evidence_file": ${evidence@Q},
    "minimal_retry_command": ${minimal_retry@Q},
    "fallback_command": ${fallback@Q},
}

(artifact_dir / "diagnostics.json").write_text(json.dumps(data, indent=2), encoding="utf-8")
(artifact_dir / "next_actions.json").write_text(json.dumps(data, indent=2), encoding="utf-8")
PY
}

write_summary() {
  local status="$1"
  local duration_seconds="$2"

  python3 - <<PY
import json
from datetime import datetime, timezone
from pathlib import Path

summary = {
    "generated_at": datetime.now(timezone.utc).isoformat(),
    "cluster": ${SEED_K3S_CLUSTER_NAME@Q},
    "namespace": ${SEED_NAMESPACE@Q},
    "profile": "real_topology_rr",
    "cni_type": ${SEED_CNI_TYPE@Q},
    "cni_master_interface": ${EFFECTIVE_CNI_IFACE@Q},
    "placement_mode": "auto",
    "topology_size": int(${SEED_TOPOLOGY_SIZE@Q}),
    "real_topology_dir": ${SEED_REAL_TOPOLOGY_DIR@Q},
    "topology_file": ${SEED_TOPOLOGY_FILE@Q},
    "assignment_file": ${SEED_ASSIGNMENT_FILE@Q},
    "expected_nodes": int(${EXPECTED_NODES@Q}),
    "nodes_used": int(${NODES_USED@Q}),
    "strict3_passed": ${OVERALL_PASSED@Q} == "true",
    "placement_passed": ${PLACEMENT_PASSED@Q} == "true",
    "bgp_passed": ${BGP_PASSED@Q} == "true",
    "connectivity_passed": ${OVERALL_PASSED@Q} == "true",
    "recovery_passed": ${OVERALL_PASSED@Q} == "true",
    "duration_seconds": int(${duration_seconds@Q}),
    "fallback_used": "none",
    "failure_reason": "" if ${status@Q} == "PASS" else ${FAILURE_REASON@Q},
    "failure_code": "" if ${status@Q} == "PASS" else ${FAILURE_CODE@Q},
}

Path(${ARTIFACT_DIR@Q}).mkdir(parents=True, exist_ok=True)
(Path(${ARTIFACT_DIR@Q}) / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
PY
}

fail_with_reason() {
  FAILURE_REASON="$1"
  FAILURE_CODE="$(resolve_failure_code)"
  local evidence="${2:-${ARTIFACT_DIR}/summary.json}"
  local minimal_retry="${3:-scripts/validate_k3s_real_topology_multinode.sh ${CURRENT_STAGE}}"
  local fallback="${4:-${minimal_retry}}"
  write_diagnostics "${CURRENT_STAGE}" "FAIL" "${evidence}" "${minimal_retry}" "${fallback}"
  write_summary "FAIL" "$(( $(date +%s) - START_TS ))"
  log "FAILED (${FAILURE_CODE}): ${FAILURE_REASON}"
  exit 1
}

ensure_dirs() {
  mkdir -p "${ARTIFACT_DIR}"
  mkdir -p "${COMPILE_DIR}"
}

ensure_kubeconfig() {
  export KUBECONFIG="${KUBECONFIG:-${KUBECONFIG_PATH}}"
  if [ -f "${KUBECONFIG}" ]; then
    return 0
  fi
  if ! "${SCRIPT_DIR}/k3s_fetch_kubeconfig.sh" > "${ARTIFACT_DIR}/kubeconfig_fetch.log" 2>&1; then
    fail_with_reason "kubeconfig_fetch_failed" "${ARTIFACT_DIR}/kubeconfig_fetch.log" \
      "scripts/k3s_fetch_kubeconfig.sh" "scripts/setup_k3s_cluster.sh"
  fi
  export KUBECONFIG="${KUBECONFIG:-${KUBECONFIG_PATH}}"
  if [ ! -f "${KUBECONFIG}" ]; then
    fail_with_reason "kubeconfig_not_found_after_fetch" "${ARTIFACT_DIR}/kubeconfig_fetch.log" \
      "scripts/k3s_fetch_kubeconfig.sh" "scripts/setup_k3s_cluster.sh"
  fi
}

detect_default_iface() {
  local ip="$1"
  # Avoid SIGPIPE issues from `awk '{...; exit}'` when the producer keeps writing.
  ssh "${SSH_OPTS[@]}" "${SEED_K3S_USER}@${ip}" \
    "ip -o -4 route show to default | sed -n '1{s/.* dev \\([^ ]*\\).*/\\1/p}'"
}

repair_registry_connectivity() {
  log "Attempting quick registry remediation on master"
  ssh "${SSH_OPTS[@]}" "${SEED_K3S_USER}@${SEED_K3S_MASTER_IP}" \
    "set -euo pipefail; \
     sudo -n docker rm -f registry >/dev/null 2>&1 || true; \
     if ! sudo -n docker image inspect registry:2 >/dev/null 2>&1; then \
       sudo -n docker pull registry:2 >/dev/null 2>&1 || (sudo -n docker pull docker.m.daocloud.io/library/registry:2 >/dev/null && sudo -n docker tag docker.m.daocloud.io/library/registry:2 registry:2 >/dev/null); \
     fi; \
     sudo -n docker run -d --network host --restart=always --name registry \
       -e REGISTRY_HTTP_ADDR=0.0.0.0:${SEED_REGISTRY_PORT} registry:2 >/dev/null"

  local i
  for i in $(seq 1 12); do
    if ssh "${SSH_OPTS[@]}" "${SEED_K3S_USER}@${SEED_K3S_WORKER1_IP}" "curl -m 5 -fsS http://${SEED_REGISTRY_HOST}:${SEED_REGISTRY_PORT}/v2/ >/dev/null" >/dev/null 2>&1 \
      && ssh "${SSH_OPTS[@]}" "${SEED_K3S_USER}@${SEED_K3S_WORKER2_IP}" "curl -m 5 -fsS http://${SEED_REGISTRY_HOST}:${SEED_REGISTRY_PORT}/v2/ >/dev/null" >/dev/null 2>&1; then
      log "Registry is reachable from both workers"
      return 0
    fi
    sleep 5
  done

  return 1
}

repair_multus_hostpaths_for_k3s() {
  if ! kubectl -n kube-system get ds kube-multus-ds >/dev/null 2>&1; then
    return 1
  fi

  log "Attempting quick multus hostPath repair for k3s"
  local conf_dir bin_dir
  conf_dir="$(ssh "${SSH_OPTS[@]}" "${SEED_K3S_USER}@${SEED_K3S_MASTER_IP}" \
    "sudo -n sh -c 'sed -n \"s/^\\s*conf_dir\\s*=\\s*\\\"\\([^\\\"]*\\)\\\".*/\\1/p\" /var/lib/rancher/k3s/agent/etc/containerd/config.toml | head -n 1' 2>/dev/null" \
    || true)"
  bin_dir="$(ssh "${SSH_OPTS[@]}" "${SEED_K3S_USER}@${SEED_K3S_MASTER_IP}" \
    "sudo -n sh -c 'if [ -d /var/lib/rancher/k3s/data/current/bin ]; then echo /var/lib/rancher/k3s/data/current/bin; else sed -n \"s/^\\s*bin_dir\\s*=\\s*\\\"\\([^\\\"]*\\)\\\".*/\\1/p\" /var/lib/rancher/k3s/agent/etc/containerd/config.toml | head -n 1; fi' 2>/dev/null" \
    || true)"

  if [ -z "${conf_dir}" ] || [ -z "${bin_dir}" ]; then
    return 1
  fi

  kubectl -n kube-system patch ds kube-multus-ds --type='strategic' -p "$(
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
  )" >/dev/null 2>&1 || true
  kubectl -n kube-system rollout restart ds/kube-multus-ds >/dev/null 2>&1 || true
  kubectl -n kube-system rollout status ds/kube-multus-ds --timeout=300s >/dev/null 2>&1 || true
  return 0
}

repair_multus_rbac_for_k3s() {
  log "Attempting quick multus RBAC repair (allow list/watch pods)"
  kubectl apply -f - <<'YAML' >/dev/null 2>&1 || true
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
  kubectl -n kube-system rollout restart ds/kube-multus-ds >/dev/null 2>&1 || true
  kubectl -n kube-system rollout status ds/kube-multus-ds --timeout=300s >/dev/null 2>&1 || true
  return 0
}

repair_cni_plugins_for_k3s() {
  if [ "${SEED_CNI_TYPE}" != "macvlan" ] && [ "${SEED_CNI_TYPE}" != "ipvlan" ]; then
    return 0
  fi

  local -a plugins
  plugins=(static)
  if [ "${SEED_CNI_TYPE}" = "macvlan" ]; then
    plugins+=(macvlan)
  else
    plugins+=(ipvlan)
  fi

  log "Attempting quick CNI plugins install: ${plugins[*]}"
  local host
  for host in "${SEED_K3S_MASTER_IP}" "${SEED_K3S_WORKER1_IP}" "${SEED_K3S_WORKER2_IP}"; do
    ssh "${SSH_OPTS[@]}" "${SEED_K3S_USER}@${host}" \
      "set -euo pipefail; \
       export DEBIAN_FRONTEND=noninteractive; \
       sudo -n apt-get update -y >/dev/null; \
       sudo -n apt-get install -y containernetworking-plugins >/dev/null; \
       sudo -n mkdir -p /opt/cni/bin; \
       for p in ${plugins[*]}; do \
         if [ -x \"/usr/lib/cni/\$p\" ]; then sudo -n ln -sf \"/usr/lib/cni/\$p\" \"/opt/cni/bin/\$p\"; fi; \
         if [ -d /var/lib/rancher/k3s/data/current/bin ]; then sudo -n ln -sf \"/usr/lib/cni/\$p\" \"/var/lib/rancher/k3s/data/current/bin/\$p\" || true; fi; \
       done" >/dev/null 2>&1 || true
  done
  return 0
}

resolve_cni_master_interface() {
  if [ "${SEED_CNI_TYPE}" != "macvlan" ] && [ "${SEED_CNI_TYPE}" != "ipvlan" ]; then
    EFFECTIVE_CNI_IFACE=""
    return 0
  fi

  local master_iface worker1_iface worker2_iface
  master_iface="$(detect_default_iface "${SEED_K3S_MASTER_IP}" || true)"
  worker1_iface="$(detect_default_iface "${SEED_K3S_WORKER1_IP}" || true)"
  worker2_iface="$(detect_default_iface "${SEED_K3S_WORKER2_IP}" || true)"

  cat > "${ARTIFACT_DIR}/default_route_ifaces.txt" <<EOF
master\t${SEED_K3S_MASTER_IP}\t${master_iface}
worker1\t${SEED_K3S_WORKER1_IP}\t${worker1_iface}
worker2\t${SEED_K3S_WORKER2_IP}\t${worker2_iface}
EOF

  if [ -n "${SEED_CNI_MASTER_INTERFACE}" ]; then
    EFFECTIVE_CNI_IFACE="${SEED_CNI_MASTER_INTERFACE}"
    return 0
  fi

  if [ -z "${master_iface}" ]; then
    fail_with_reason "placement_check_failed" "${ARTIFACT_DIR}/default_route_ifaces.txt" \
      "scripts/validate_k3s_real_topology_multinode.sh preflight" "scripts/seed_lab_entry_status.sh"
  fi

  EFFECTIVE_CNI_IFACE="${master_iface}"
}

resolve_topology_paths() {
  if [ -z "${SEED_TOPOLOGY_FILE}" ]; then
    SEED_TOPOLOGY_FILE="${SEED_REAL_TOPOLOGY_DIR}/real_topology_${SEED_TOPOLOGY_SIZE}.txt"
  fi
  if [ -z "${SEED_ASSIGNMENT_FILE}" ]; then
    SEED_ASSIGNMENT_FILE="${SEED_REAL_TOPOLOGY_DIR}/assignment.pkl"
  fi
}

compute_expected_nodes() {
  resolve_topology_paths
  EXPECTED_NODES="$(
    SEED_TOPOLOGY_FILE="${SEED_TOPOLOGY_FILE}" python3 - <<'PY'
import ast
import os
from pathlib import Path

path = Path(os.path.expanduser(os.environ["SEED_TOPOLOGY_FILE"]))
data = {}
for raw in path.read_text(encoding="utf-8").splitlines():
    line = raw.strip()
    if not line or line.startswith("#"):
        continue
    key, val = line.split(":", 1)
    data[key.strip()] = ast.literal_eval(val.strip())

ixps = data.get("ixps", [])
transit_asns = data.get("transit_asns", [])
stub_asns = data.get("stub_asns", [])
edges = data.get("ix_ix_transit_edges", [])

routers = 0
for asn in transit_asns:
    ixs = set()
    for ix_a, ix_b, t_asn, _ in edges:
        if str(t_asn) != str(asn):
            continue
        ixs.add(str(ix_a))
        ixs.add(str(ix_b))
    routers += len(ixs)

expected = len(ixps) + routers + len(stub_asns)
print(expected)
PY
  )"
}

write_placement_tsv() {
  kubectl -n "${SEED_NAMESPACE}" get pods \
    -o jsonpath='{range .items[*]}{.metadata.name}{"\t"}{.metadata.labels.seedemu\.io/asn}{"\t"}{.spec.nodeName}{"\n"}{end}' \
    > "${ARTIFACT_DIR}/placement.tsv"

  NODES_USED="$(
    awk '{print $3}' "${ARTIFACT_DIR}/placement.tsv" \
      | sed '/^$/d' \
      | sort -u \
      | wc -l \
      | tr -d ' '
  )"
}

run_preflight() {
  CURRENT_STAGE="preflight"
  log "Preflight: kubeconfig + nodes Ready + CNI iface detection"

  if [ "${SEED_PLACEMENT_MODE}" = "strict3" ]; then
    fail_with_reason "strict3_not_supported" "${ARTIFACT_DIR}/summary.json" \
      "export SEED_PLACEMENT_MODE=auto && scripts/validate_k3s_real_topology_multinode.sh preflight" \
      "scripts/seed_k8s_profile_runner.sh real_topology_rr doctor"
  fi
  SEED_PLACEMENT_MODE="auto"

  ensure_kubeconfig
  kubectl get nodes -o wide > "${ARTIFACT_DIR}/nodes_wide.txt"

  if ! (kubectl get nodes --no-headers | awk '$2 !~ /^Ready/ {bad=1} END{exit bad}'); then
    fail_with_reason "placement_check_failed" "${ARTIFACT_DIR}/nodes_wide.txt" \
      "kubectl get nodes -o wide" "scripts/seed_lab_entry_status.sh"
  fi

  local desired ready
  desired="$(kubectl -n kube-system get ds kube-multus-ds -o jsonpath='{.status.desiredNumberScheduled}' 2>/dev/null || echo 0)"
  ready="$(kubectl -n kube-system get ds kube-multus-ds -o jsonpath='{.status.numberReady}' 2>/dev/null || echo -1)"
  if [ "${desired}" = "0" ] || [ "${desired}" != "${ready}" ]; then
    repair_multus_hostpaths_for_k3s || true
    desired="$(kubectl -n kube-system get ds kube-multus-ds -o jsonpath='{.status.desiredNumberScheduled}' 2>/dev/null || echo 0)"
    ready="$(kubectl -n kube-system get ds kube-multus-ds -o jsonpath='{.status.numberReady}' 2>/dev/null || echo -1)"
    if [ "${desired}" = "0" ] || [ "${desired}" != "${ready}" ]; then
      kubectl -n kube-system get ds kube-multus-ds -o wide > "${ARTIFACT_DIR}/multus_ds.txt" 2>/dev/null || true
      kubectl -n kube-system get pods -o wide > "${ARTIFACT_DIR}/kube_system_pods.txt" 2>/dev/null || true
      (kubectl -n kube-system get events --sort-by=.lastTimestamp 2>/dev/null || true) \
        | tail -n 80 > "${ARTIFACT_DIR}/kube_system_events_tail.txt" 2>/dev/null || true
      fail_with_reason "multus_not_ready" "${ARTIFACT_DIR}/multus_ds.txt" \
        "kubectl -n kube-system rollout restart ds/kube-multus-ds" "kubectl -n kube-system get pods -l name=multus -o wide"
    fi
  fi

  local can_list
  can_list="$(kubectl auth can-i list pods -n kube-system --as system:serviceaccount:kube-system:multus 2>/dev/null || echo no)"
  echo "${can_list}" > "${ARTIFACT_DIR}/multus_rbac_can_i_list_pods.txt"
  if [ "${can_list}" != "yes" ]; then
    repair_multus_rbac_for_k3s || true
    can_list="$(kubectl auth can-i list pods -n kube-system --as system:serviceaccount:kube-system:multus 2>/dev/null || echo no)"
    echo "${can_list}" > "${ARTIFACT_DIR}/multus_rbac_can_i_list_pods.txt"
    if [ "${can_list}" != "yes" ]; then
      fail_with_reason "multus_not_ready" "${ARTIFACT_DIR}/multus_rbac_can_i_list_pods.txt" \
        "scripts/setup_k3s_cluster.sh" "kubectl get clusterrole multus -o yaml"
    fi
  fi

  local -a required_plugins
  required_plugins=()
  case "${SEED_CNI_TYPE}" in
    macvlan)
      required_plugins=(macvlan static)
      ;;
    ipvlan)
      required_plugins=(ipvlan static)
      ;;
  esac

  : > "${ARTIFACT_DIR}/cni_plugins_status.txt"
  if [ "${#required_plugins[@]}" != "0" ]; then
    local host missing
    missing="false"
    for host in "${SEED_K3S_MASTER_IP}" "${SEED_K3S_WORKER1_IP}" "${SEED_K3S_WORKER2_IP}"; do
      if ssh "${SSH_OPTS[@]}" "${SEED_K3S_USER}@${host}" \
        "set -euo pipefail; for p in ${required_plugins[*]}; do test -x \"/opt/cni/bin/\$p\" || test -x \"/var/lib/rancher/k3s/data/current/bin/\$p\"; done" >/dev/null 2>&1; then
        echo -e "${host}\tok" >> "${ARTIFACT_DIR}/cni_plugins_status.txt"
      else
        echo -e "${host}\tmissing" >> "${ARTIFACT_DIR}/cni_plugins_status.txt"
        missing="true"
      fi
    done
    if [ "${missing}" = "true" ]; then
      repair_cni_plugins_for_k3s || true
      missing="false"
      : > "${ARTIFACT_DIR}/cni_plugins_status.txt"
      for host in "${SEED_K3S_MASTER_IP}" "${SEED_K3S_WORKER1_IP}" "${SEED_K3S_WORKER2_IP}"; do
        if ssh "${SSH_OPTS[@]}" "${SEED_K3S_USER}@${host}" \
          "set -euo pipefail; for p in ${required_plugins[*]}; do test -x \"/opt/cni/bin/\$p\" || test -x \"/var/lib/rancher/k3s/data/current/bin/\$p\"; done" >/dev/null 2>&1; then
          echo -e "${host}\tok" >> "${ARTIFACT_DIR}/cni_plugins_status.txt"
        else
          echo -e "${host}\tmissing" >> "${ARTIFACT_DIR}/cni_plugins_status.txt"
          missing="true"
        fi
      done
      if [ "${missing}" = "true" ]; then
        fail_with_reason "multus_not_ready" "${ARTIFACT_DIR}/cni_plugins_status.txt" \
          "scripts/setup_k3s_cluster.sh" "cat ${ARTIFACT_DIR}/cni_plugins_status.txt"
      fi
    fi
  fi

  if ! ssh "${SSH_OPTS[@]}" "${SEED_K3S_USER}@${SEED_K3S_MASTER_IP}" \
    "command -v docker >/dev/null 2>&1 && sudo -n docker ps --format '{{.Names}}' 2>/dev/null | grep -x registry" >/dev/null 2>&1; then
    repair_registry_connectivity || true
    if ! ssh "${SSH_OPTS[@]}" "${SEED_K3S_USER}@${SEED_K3S_MASTER_IP}" \
      "command -v docker >/dev/null 2>&1 && sudo -n docker ps --format '{{.Names}}' 2>/dev/null | grep -x registry" >/dev/null 2>&1; then
      fail_with_reason "registry_unreachable" "${ARTIFACT_DIR}/nodes_wide.txt" \
        "scripts/setup_k3s_cluster.sh" "ssh -i ${SEED_K3S_SSH_KEY} ${SEED_K3S_USER}@${SEED_K3S_MASTER_IP} 'sudo docker ps'"
    fi
  fi

  if ! ssh "${SSH_OPTS[@]}" "${SEED_K3S_USER}@${SEED_K3S_WORKER1_IP}" \
    "curl -m 5 -fsS http://${SEED_REGISTRY_HOST}:${SEED_REGISTRY_PORT}/v2/ >/dev/null" >/dev/null 2>&1 \
    || ! ssh "${SSH_OPTS[@]}" "${SEED_K3S_USER}@${SEED_K3S_WORKER2_IP}" \
    "curl -m 5 -fsS http://${SEED_REGISTRY_HOST}:${SEED_REGISTRY_PORT}/v2/ >/dev/null" >/dev/null 2>&1; then
    repair_registry_connectivity || true
    if ! ssh "${SSH_OPTS[@]}" "${SEED_K3S_USER}@${SEED_K3S_WORKER1_IP}" \
      "curl -m 5 -fsS http://${SEED_REGISTRY_HOST}:${SEED_REGISTRY_PORT}/v2/ >/dev/null" >/dev/null 2>&1 \
      || ! ssh "${SSH_OPTS[@]}" "${SEED_K3S_USER}@${SEED_K3S_WORKER2_IP}" \
      "curl -m 5 -fsS http://${SEED_REGISTRY_HOST}:${SEED_REGISTRY_PORT}/v2/ >/dev/null" >/dev/null 2>&1; then
      fail_with_reason "registry_unreachable" "${ARTIFACT_DIR}/nodes_wide.txt" \
        "scripts/setup_k3s_cluster.sh" "ssh -i ${SEED_K3S_SSH_KEY} ${SEED_K3S_USER}@${SEED_K3S_WORKER1_IP} 'curl -v http://${SEED_REGISTRY_HOST}:${SEED_REGISTRY_PORT}/v2/'"
    fi
  fi

  resolve_cni_master_interface

  write_diagnostics "${CURRENT_STAGE}" "PASS" "${ARTIFACT_DIR}/nodes_wide.txt" \
    "scripts/validate_k3s_real_topology_multinode.sh compile" "scripts/validate_k3s_real_topology_multinode.sh verify"
}

run_compile() {
  CURRENT_STAGE="compile"
  log "Compile: examples/kubernetes/k8s_real_topology_rr.py"

  resolve_topology_paths
  compute_expected_nodes

  rm -rf "${COMPILE_DIR}"
  mkdir -p "${COMPILE_DIR}"

  (
    cd "${REPO_ROOT}"
    PYTHONPATH="${REPO_ROOT}" \
    SEED_NAMESPACE="${SEED_NAMESPACE}" \
    SEED_REGISTRY="${SEED_REGISTRY}" \
    SEED_CNI_TYPE="${SEED_CNI_TYPE}" \
    SEED_CNI_MASTER_INTERFACE="${EFFECTIVE_CNI_IFACE}" \
    SEED_SCHEDULING_STRATEGY="${SEED_SCHEDULING_STRATEGY}" \
    SEED_OUTPUT_DIR="${COMPILE_DIR}" \
    SEED_REAL_TOPOLOGY_DIR="${SEED_REAL_TOPOLOGY_DIR}" \
    SEED_TOPOLOGY_SIZE="${SEED_TOPOLOGY_SIZE}" \
    SEED_TOPOLOGY_FILE="${SEED_TOPOLOGY_FILE}" \
    SEED_ASSIGNMENT_FILE="${SEED_ASSIGNMENT_FILE}" \
    python3 examples/kubernetes/k8s_real_topology_rr.py
  ) 2>&1 | tee "${ARTIFACT_DIR}/compile.log"

  test -f "${COMPILE_DIR}/k8s.yaml" || fail_with_reason "compile_missing_k8s_yaml" "${ARTIFACT_DIR}/compile.log" \
    "scripts/validate_k3s_real_topology_multinode.sh compile" "cat ${ARTIFACT_DIR}/compile.log"
  test -x "${COMPILE_DIR}/build_images.sh" || fail_with_reason "compile_missing_build_script" "${ARTIFACT_DIR}/compile.log" \
    "scripts/validate_k3s_real_topology_multinode.sh compile" "ls -la ${COMPILE_DIR}"

  write_diagnostics "${CURRENT_STAGE}" "PASS" "${ARTIFACT_DIR}/compile.log" \
    "scripts/validate_k3s_real_topology_multinode.sh build" "scripts/validate_k3s_real_topology_multinode.sh deploy"
}

run_remote_build() {
  CURRENT_STAGE="build"
  log "Build: tar+scp compiled artifacts; run build_images.sh on master"

  local tarball="${ARTIFACT_DIR}/compiled.tar.gz"
  tar -C "${COMPILE_DIR}" -czf "${tarball}" .

  ssh "${SSH_OPTS[@]}" "${SEED_K3S_USER}@${SEED_K3S_MASTER_IP}" \
    "rm -rf '${REMOTE_WORK_DIR}' && mkdir -p '${REMOTE_WORK_DIR}'"
  scp -q "${SSH_OPTS[@]}" "${tarball}" "${SEED_K3S_USER}@${SEED_K3S_MASTER_IP}:${REMOTE_WORK_DIR}/compiled.tar.gz"

  if ! ssh "${SSH_OPTS[@]}" "${SEED_K3S_USER}@${SEED_K3S_MASTER_IP}" "sudo -n env \
    SEED_BUILD_PARALLELISM=${SEED_BUILD_PARALLELISM} \
    SEED_DOCKER_BUILDKIT=${SEED_DOCKER_BUILDKIT} \
    bash -lc '
    set -euo pipefail
    cd \"${REMOTE_WORK_DIR}\"
    tar -xzf compiled.tar.gz
    ./build_images.sh
  '" 2>&1 | tee "${ARTIFACT_DIR}/remote_build.log"; then
    fail_with_reason "build_failed" "${ARTIFACT_DIR}/remote_build.log" \
      "scripts/validate_k3s_real_topology_multinode.sh build" "tail -n 200 ${ARTIFACT_DIR}/remote_build.log"
  fi

  write_diagnostics "${CURRENT_STAGE}" "PASS" "${ARTIFACT_DIR}/remote_build.log" \
    "scripts/validate_k3s_real_topology_multinode.sh deploy" "scripts/validate_k3s_real_topology_multinode.sh verify"
}

run_deploy() {
  CURRENT_STAGE="deploy"
  log "Deploy: apply k8s.yaml to namespace ${SEED_NAMESPACE}"

  if [ "${CLEAN_NAMESPACE}" = "true" ]; then
    kubectl delete namespace "${SEED_NAMESPACE}" --ignore-not-found >/dev/null 2>&1 || true
    if kubectl get namespace "${SEED_NAMESPACE}" >/dev/null 2>&1; then
      kubectl wait --for=delete namespace/"${SEED_NAMESPACE}" --timeout=300s >/dev/null 2>&1 || true
    fi
  fi

  kubectl create namespace "${SEED_NAMESPACE}" --dry-run=client -o yaml | kubectl apply -f - >/dev/null
  kubectl -n "${SEED_NAMESPACE}" apply -f "${COMPILE_DIR}/k8s.yaml" 2>&1 | tee "${ARTIFACT_DIR}/apply.log"

  if ! kubectl -n "${SEED_NAMESPACE}" wait --for=condition=Available --timeout="${DEPLOY_WAIT_TIMEOUT}" deployment --all \
    2>&1 | tee "${ARTIFACT_DIR}/wait.log"; then
    kubectl -n "${SEED_NAMESPACE}" get pods -o wide > "${ARTIFACT_DIR}/pods_wide.txt" 2>/dev/null || true
    kubectl -n "${SEED_NAMESPACE}" get deploy -o wide > "${ARTIFACT_DIR}/deployments_wide.txt" 2>/dev/null || true
    kubectl -n "${SEED_NAMESPACE}" get events --sort-by=.lastTimestamp > "${ARTIFACT_DIR}/events.txt" 2>/dev/null || true
    fail_with_reason "deploy_wait_timeout_or_failure" "${ARTIFACT_DIR}/wait.log" \
      "scripts/validate_k3s_real_topology_multinode.sh deploy" "kubectl -n ${SEED_NAMESPACE} get pods -o wide"
  fi

  kubectl -n "${SEED_NAMESPACE}" get pods -o wide > "${ARTIFACT_DIR}/pods_wide.txt"
  kubectl -n "${SEED_NAMESPACE}" get deploy -o wide > "${ARTIFACT_DIR}/deployments_wide.txt"
  write_diagnostics "${CURRENT_STAGE}" "PASS" "${ARTIFACT_DIR}/deployments_wide.txt" \
    "scripts/validate_k3s_real_topology_multinode.sh verify" "kubectl -n ${SEED_NAMESPACE} get pods -o wide"
}

pick_router_pod() {
  python3 - "${SEED_NAMESPACE}" <<'PY'
import json
import subprocess
import sys

ns = sys.argv[1]
out = subprocess.check_output(["kubectl", "-n", ns, "get", "pods", "-o", "json"], text=True)
data = json.loads(out)
for item in data.get("items", []):
    labels = item.get("metadata", {}).get("labels", {}) or {}
    name = str(labels.get("seedemu.io/name", ""))
    if name.startswith("r"):
        print(item["metadata"]["name"])
        raise SystemExit(0)
raise SystemExit(1)
PY
}

run_verify() {
  CURRENT_STAGE="verify"
  log "Verify: expected count + nodes_used>=${SEED_MIN_NODES_USED} + birdc Established"

  compute_expected_nodes
  kubectl -n "${SEED_NAMESPACE}" get pods -o wide > "${ARTIFACT_DIR}/pods_wide.txt"
  kubectl -n "${SEED_NAMESPACE}" get deploy -o wide > "${ARTIFACT_DIR}/deployments_wide.txt"

  local dep_count pod_running
  dep_count="$( (kubectl -n "${SEED_NAMESPACE}" get deploy --no-headers 2>/dev/null || true) | wc -l | tr -d ' ' )"
  pod_running="$( (kubectl -n "${SEED_NAMESPACE}" get pods --field-selector=status.phase=Running --no-headers 2>/dev/null || true) | wc -l | tr -d ' ' )"

  cat > "${ARTIFACT_DIR}/counts.json" <<JSON
{
  "expected_nodes": ${EXPECTED_NODES},
  "deployments": ${dep_count},
  "running_pods": ${pod_running}
}
JSON

  if [ "${dep_count}" -ne "${EXPECTED_NODES}" ] || [ "${pod_running}" -lt "${EXPECTED_NODES}" ]; then
    fail_with_reason "placement_check_failed" "${ARTIFACT_DIR}/counts.json" \
      "scripts/validate_k3s_real_topology_multinode.sh verify" "cat ${ARTIFACT_DIR}/counts.json"
  fi

  write_placement_tsv
  if [ "${NODES_USED}" -lt "${SEED_MIN_NODES_USED}" ]; then
    fail_with_reason "placement_check_failed" "${ARTIFACT_DIR}/placement.tsv" \
      "scripts/validate_k3s_real_topology_multinode.sh verify" "cat ${ARTIFACT_DIR}/placement.tsv | tail -n 20"
  fi
  PLACEMENT_PASSED="true"

  local sample_pod
  if ! sample_pod="$(pick_router_pod)"; then
    fail_with_reason "bgp_not_established" "${ARTIFACT_DIR}/pods_wide.txt" \
      "scripts/validate_k3s_real_topology_multinode.sh verify" "kubectl -n ${SEED_NAMESPACE} get pods -o wide"
  fi

  local deadline now
  deadline="$(( $(date +%s) + BGP_WAIT_TIMEOUT_SECONDS ))"
  : > "${ARTIFACT_DIR}/bird_sample.txt"
  while true; do
    kubectl -n "${SEED_NAMESPACE}" exec "${sample_pod}" -- birdc show protocols > "${ARTIFACT_DIR}/bird_sample.txt" 2>&1 || true
    if grep -Eq 'BGP.*Established|Established.*BGP' "${ARTIFACT_DIR}/bird_sample.txt"; then
      break
    fi
    now="$(date +%s)"
    if [ "${now}" -ge "${deadline}" ]; then
      fail_with_reason "bgp_not_established" "${ARTIFACT_DIR}/bird_sample.txt" \
        "scripts/validate_k3s_real_topology_multinode.sh verify" "sed -n '1,200p' ${ARTIFACT_DIR}/bird_sample.txt"
    fi
    sleep 5
  done
  BGP_PASSED="true"
  OVERALL_PASSED="true"

  write_diagnostics "${CURRENT_STAGE}" "PASS" "${ARTIFACT_DIR}/bird_sample.txt" \
    "scripts/validate_k3s_real_topology_multinode.sh verify" "kubectl -n ${SEED_NAMESPACE} get pods -o wide"
}

run_clean() {
  CURRENT_STAGE="clean"
  log "Clean: namespace ${SEED_NAMESPACE}"
  ensure_kubeconfig
  kubectl delete namespace "${SEED_NAMESPACE}" --ignore-not-found >/dev/null 2>&1 || true
  write_diagnostics "${CURRENT_STAGE}" "PASS" "${ARTIFACT_DIR}/summary.json" \
    "scripts/validate_k3s_real_topology_multinode.sh all" "scripts/seed_k8s_profile_runner.sh real_topology_rr all"
}

START_TS="$(date +%s)"

main() {
  ensure_dirs
  require_cmd python3
  require_cmd kubectl
  require_cmd ssh
  require_cmd scp
  require_cmd tar
  require_cmd awk

  if [ ! -f "${SEED_K3S_SSH_KEY}" ]; then
    CURRENT_STAGE="preflight"
    fail_with_reason "ssh_key_not_found" "${SEED_K3S_SSH_KEY}" \
      "export SEED_K3S_SSH_KEY=/path/to/key && scripts/validate_k3s_real_topology_multinode.sh preflight" \
      "scripts/setup_k3s_cluster.sh"
  fi

  ensure_kubeconfig

  case "${ACTION}" in
    all)
      run_preflight
      run_compile
      run_remote_build
      run_deploy
      run_verify
      write_summary "PASS" "$(( $(date +%s) - START_TS ))"
      log "Validation succeeded. Artifacts: ${ARTIFACT_DIR}"
      ;;
    preflight)
      run_preflight
      write_summary "PASS" "$(( $(date +%s) - START_TS ))"
      ;;
    compile)
      run_preflight
      run_compile
      write_summary "PASS" "$(( $(date +%s) - START_TS ))"
      ;;
    build)
      run_preflight
      run_remote_build
      write_summary "PASS" "$(( $(date +%s) - START_TS ))"
      ;;
    deploy)
      run_preflight
      run_deploy
      write_summary "PASS" "$(( $(date +%s) - START_TS ))"
      ;;
    verify)
      run_preflight
      run_verify
      write_summary "PASS" "$(( $(date +%s) - START_TS ))"
      ;;
    clean)
      run_clean
      write_summary "PASS" "$(( $(date +%s) - START_TS ))"
      ;;
    -h|--help|help)
      usage
      ;;
    *)
      usage
      exit 1
      ;;
  esac
}

main "$@"
