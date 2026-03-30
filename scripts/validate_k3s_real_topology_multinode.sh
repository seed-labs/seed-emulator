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
source "${SCRIPT_DIR}/seed_k8s_cluster_inventory.sh"
seed_load_cluster_inventory

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
SEED_SCHEDULING_STRATEGY="${SEED_SCHEDULING_STRATEGY:-by_as_hard}"
SEED_PLACEMENT_MODE="${SEED_PLACEMENT_MODE:-by_as_hard}"
SEED_MIN_NODES_USED="${SEED_MIN_NODES_USED:-2}"
SEED_BUILD_PARALLELISM="${SEED_BUILD_PARALLELISM:-1}"
SEED_DOCKER_BUILDKIT="${SEED_DOCKER_BUILDKIT:-0}"
SEED_REGISTRY_PUSH_RETRIES="${SEED_REGISTRY_PUSH_RETRIES:-5}"
SEED_REGISTRY_PUSH_BACKOFF_SECONDS="${SEED_REGISTRY_PUSH_BACKOFF_SECONDS:-5}"
SEED_DOCKER_MAX_CONCURRENT_UPLOADS="${SEED_DOCKER_MAX_CONCURRENT_UPLOADS:-1}"
SEED_REGISTRY_PUSH_TIMEOUT_SECONDS="${SEED_REGISTRY_PUSH_TIMEOUT_SECONDS:-180}"
SEED_PRELOAD_FALLBACK_MODE="${SEED_PRELOAD_FALLBACK_MODE:-registry}"
SEED_IMAGE_DISTRIBUTION_MODE="${SEED_IMAGE_DISTRIBUTION_MODE:-preload}"
case "${SEED_IMAGE_DISTRIBUTION_MODE}" in
  registry|preload) ;;
  *)
    echo "Unsupported SEED_IMAGE_DISTRIBUTION_MODE: ${SEED_IMAGE_DISTRIBUTION_MODE} (expected: registry or preload)" >&2
    exit 1
    ;;
esac
SEED_IMAGE_PULL_POLICY="${SEED_IMAGE_PULL_POLICY:-}"
if [ -z "${SEED_IMAGE_PULL_POLICY}" ]; then
  if [ "${SEED_IMAGE_DISTRIBUTION_MODE}" = "preload" ]; then
    SEED_IMAGE_PULL_POLICY="IfNotPresent"
  else
    SEED_IMAGE_PULL_POLICY="Always"
  fi
fi
SEED_KUBECTL_EXEC_TIMEOUT_SECONDS="${SEED_KUBECTL_EXEC_TIMEOUT_SECONDS:-20}"
BGP_HEALTH_PARALLELISM="${SEED_BGP_HEALTH_PARALLELISM:-8}"
BGP_WAIT_TIMEOUT_SECONDS="${BGP_WAIT_TIMEOUT_SECONDS:-300}"
DEPLOY_WAIT_TIMEOUT="${DEPLOY_WAIT_TIMEOUT:-2400s}"
CLEAN_NAMESPACE="${SEED_CLEAN_NAMESPACE:-true}"
SEED_EXPERIMENT_PROFILE="${SEED_EXPERIMENT_PROFILE:-real_topology_rr}"
SEED_PROFILE_KIND="${SEED_PROFILE_KIND:-baseline}"
SEED_PROFILE_SUPPORT_TIER="${SEED_PROFILE_SUPPORT_TIER:-tier1}"
SEED_PROFILE_ACCEPTANCE_LEVEL="${SEED_PROFILE_ACCEPTANCE_LEVEL:-runtime_strict}"
SEED_PROFILE_CAPACITY_GATE="${SEED_PROFILE_CAPACITY_GATE:-none}"
SEED_BGP_STARTUP_MODE="${SEED_BGP_STARTUP_MODE:-phased}"
SEED_IBGP_REFLECTION_MODE="${SEED_IBGP_REFLECTION_MODE:-simple}"
SEED_ROUTING_KERNEL_EXPORT_MODE="${SEED_ROUTING_KERNEL_EXPORT_MODE:-default}"
SEED_OSPF_TIMING_PROFILE="${SEED_OSPF_TIMING_PROFILE:-default}"

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
CONNECTIVITY_PASSED="false"
RECOVERY_PASSED="false"
OVERALL_PASSED="false"
CAPACITY_GATE_STATUS="open"
SEED_NODE_LABELS_JSON_EFFECTIVE=""
BUILD_DURATION_SECONDS="0"
UP_DURATION_SECONDS="0"
PHASE_START_DURATION_SECONDS="0"
TIMING_PATH="${ARTIFACT_DIR}/timing.json"
SEED_PHASE_START_DRIVER="${SEED_PHASE_START_DRIVER:-${SCRIPT_DIR}/seed_k8s_senior_phase_start.py}"
FALLBACK_USED="none"

SSH_OPTS=(
  -o StrictHostKeyChecking=no
  -o UserKnownHostsFile=/dev/null
  -o LogLevel=ERROR
  -o BatchMode=yes
  -o IdentitiesOnly=yes
  -o IdentityAgent=none
  -o ConnectTimeout=10
  -o ServerAliveInterval=30
  -o ServerAliveCountMax=3
  -i "${SEED_K3S_SSH_KEY}"
)
SSH_EXEC_OPTS=("${SSH_OPTS[@]}" -n)
SEED_SSH_PROBE_TIMEOUT_SECONDS="${SEED_SSH_PROBE_TIMEOUT_SECONDS:-20}"
SEED_SSH_LONG_PROBE_TIMEOUT_SECONDS="${SEED_SSH_LONG_PROBE_TIMEOUT_SECONDS:-90}"

run_ssh_probe() {
  if command -v timeout >/dev/null 2>&1; then
    timeout "${SEED_SSH_PROBE_TIMEOUT_SECONDS}" ssh "$@"
  else
    ssh "$@"
  fi
}

run_ssh_probe_with_timeout() {
  local probe_timeout="$1"
  shift
  if command -v timeout >/dev/null 2>&1; then
    timeout "${probe_timeout}" ssh "$@"
  else
    ssh "$@"
  fi
}

log() {
  echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*"
}

tail_log_on_failure() {
  local log_file="$1"
  local lines="${2:-120}"
  if [ -f "${log_file}" ]; then
    log "Last ${lines} lines from ${log_file}:"
    tail -n "${lines}" "${log_file}" >&2 || true
  fi
}

run_kubectl_exec() {
  if command -v timeout >/dev/null 2>&1; then
    timeout "${SEED_KUBECTL_EXEC_TIMEOUT_SECONDS}" kubectl "$@"
  else
    kubectl "$@"
  fi
}

usage() {
  cat <<'USAGE'
Usage: scripts/validate_k3s_real_topology_multinode.sh [all|preflight|compile|build|deploy|phase-start|start-bird|start-kernel|verify|clean]

Actions:
  all          Run full pipeline: preflight -> compile -> build -> deploy -> phase-start -> verify
  preflight    Fetch kubeconfig, check nodes, detect CNI master iface
  compile      Compile real-topology RR into Kubernetes manifests
  build        Build and push images on K3s master
  deploy       Apply manifests and wait until all deployments are Available (does not start bird)
  phase-start  Run the separate bird/iBGP/eBGP startup stage after deploy
  start-bird   Start bird routing processes only
  start-kernel Switch bird to kernel mode
  verify       Verify expected workload count, multinode placement, and BGP status (birdc)
  clean        Delete namespace resources used by this workflow
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
    ssh_access_failed)
      echo "SSH_ACCESS_FAILED"
      ;;
    capacity_gated)
      echo "CAPACITY_GATED"
      ;;
    compile_missing_k8s_yaml|compile_missing_build_script|compile_missing_image_refs|compile_failed)
      echo "COMPILE_FAILED"
      ;;
    registry_timeout)
      echo "REGISTRY_TIMEOUT"
      ;;
    build_failed)
      echo "BUILD_FAILED"
      ;;
    image_preload_failed)
      echo "IMAGE_PRELOAD_FAILED"
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
    asn_split_across_nodes|as_assignment_mismatch)
      echo "AS_PLACEMENT_SPLIT"
      ;;
    bird_not_started)
      echo "BIRD_NOT_STARTED"
      ;;
    ibgp_phase_failed|ebgp_phase_failed)
      echo "PHASED_START_FAILED"
      ;;
    bgp_not_established|ibgp_incomplete|ebgp_incomplete|kubectl_exec_failed|no_bgp_protocols_found)
      echo "BGP_NOT_ESTABLISHED"
      ;;
    ospf_incomplete|artifact_materialization_failed|artifact_contract_failed)
      echo "PROTOCOL_HEALTH_FAILED"
      ;;
    connectivity_check_failed)
      echo "CONNECTIVITY_FAILED"
      ;;
    recovery_check_failed)
      echo "RECOVERY_FAILED"
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

write_stage_timing() {
  local key="$1"
  local seconds="$2"

  STAGE_TIMING_PATH="${TIMING_PATH}" \
  STAGE_TIMING_KEY="${key}" \
  STAGE_TIMING_SECONDS="${seconds}" \
  python3 - <<'PY'
import json
import os
from pathlib import Path

path = Path(os.environ["STAGE_TIMING_PATH"])
if path.exists():
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        data = {}
else:
    data = {}

if not isinstance(data, dict):
    data = {}

data[os.environ["STAGE_TIMING_KEY"]] = int(float(os.environ["STAGE_TIMING_SECONDS"]))
path.write_text(json.dumps(data, indent=2), encoding="utf-8")
PY
}

write_summary() {
  local status="$1"
  local duration_seconds="$2"

  python3 - <<PY
import json
from datetime import datetime, timezone
from pathlib import Path

artifact_dir = Path(${ARTIFACT_DIR@Q})
timing_path = Path(${TIMING_PATH@Q})
if timing_path.exists():
    try:
        timing = json.loads(timing_path.read_text(encoding="utf-8"))
    except Exception:
        timing = {}
else:
    timing = {}
if not isinstance(timing, dict):
    timing = {}

summary = {
    "generated_at": datetime.now(timezone.utc).isoformat(),
    "cluster": ${SEED_K3S_CLUSTER_NAME@Q},
    "namespace": ${SEED_NAMESPACE@Q},
    "profile": ${SEED_EXPERIMENT_PROFILE@Q},
    "profile_id": ${SEED_EXPERIMENT_PROFILE@Q},
    "profile_kind": ${SEED_PROFILE_KIND@Q},
    "support_tier": ${SEED_PROFILE_SUPPORT_TIER@Q},
    "acceptance_level": ${SEED_PROFILE_ACCEPTANCE_LEVEL@Q},
    "capacity_gate": ${SEED_PROFILE_CAPACITY_GATE@Q},
    "capacity_gate_status": ${CAPACITY_GATE_STATUS@Q},
    "runner_status": ${status@Q},
    "bird_autostart": False,
    "bgp_startup_mode": ${SEED_BGP_STARTUP_MODE@Q},
    "as_placement_mode": ${SEED_PLACEMENT_MODE@Q},
    "cni_type": ${SEED_CNI_TYPE@Q},
    "cni_master_interface": ${EFFECTIVE_CNI_IFACE@Q},
    "placement_mode": ${SEED_PLACEMENT_MODE@Q},
    "registry_host": ${SEED_REGISTRY_HOST@Q},
    "registry_port": int(${SEED_REGISTRY_PORT@Q}),
    "registry": ${SEED_REGISTRY@Q},
    "image_distribution_mode": ${SEED_IMAGE_DISTRIBUTION_MODE@Q},
    "image_pull_policy": ${SEED_IMAGE_PULL_POLICY@Q},
    "ospf_default_mode": "legacy_large_scale",
    "topology_size": int(${SEED_TOPOLOGY_SIZE@Q}),
    "real_topology_dir": ${SEED_REAL_TOPOLOGY_DIR@Q},
    "topology_file": ${SEED_TOPOLOGY_FILE@Q},
    "assignment_file": ${SEED_ASSIGNMENT_FILE@Q},
    "expected_nodes": int(${EXPECTED_NODES@Q}),
    "nodes_used": int(${NODES_USED@Q}),
    "strict3_passed": ${OVERALL_PASSED@Q} == "true",
    "placement_passed": ${PLACEMENT_PASSED@Q} == "true",
    "bgp_passed": ${BGP_PASSED@Q} == "true",
    "connectivity_passed": ${CONNECTIVITY_PASSED@Q} == "true",
    "recovery_passed": ${RECOVERY_PASSED@Q} == "true",
    "build_duration_seconds": int(timing.get("build_duration_seconds", 0)),
    "up_duration_seconds": int(timing.get("up_duration_seconds", 0)),
    "phase_start_duration_seconds": int(timing.get("phase_start_duration_seconds", 0)),
    "start_bird_duration_seconds": int(timing.get("start_bird_duration_seconds", 0)),
    "start_kernel_duration_seconds": int(timing.get("start_kernel_duration_seconds", 0)),
    "validation_duration_seconds": int(timing.get("validation_duration_seconds", 0)),
    "pipeline_duration_seconds": max(
        int(${duration_seconds@Q}),
        int(timing.get("build_duration_seconds", 0))
        + int(timing.get("up_duration_seconds", 0))
        + int(timing.get("phase_start_duration_seconds", 0))
        + int(timing.get("start_bird_duration_seconds", 0))
        + int(timing.get("start_kernel_duration_seconds", 0))
        + int(timing.get("validation_duration_seconds", 0)),
    ),
    "duration_seconds": max(
        int(${duration_seconds@Q}),
        int(timing.get("build_duration_seconds", 0))
        + int(timing.get("up_duration_seconds", 0))
        + int(timing.get("phase_start_duration_seconds", 0))
        + int(timing.get("start_bird_duration_seconds", 0))
        + int(timing.get("start_kernel_duration_seconds", 0))
        + int(timing.get("validation_duration_seconds", 0)),
    ),
    "fallback_used": ${FALLBACK_USED@Q},
    "failure_reason": "" if ${status@Q} == "PASS" else ${FAILURE_REASON@Q},
    "failure_code": "" if ${status@Q} == "PASS" else ${FAILURE_CODE@Q},
}

artifact_dir.mkdir(parents=True, exist_ok=True)
(artifact_dir / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
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

check_ssh_access() {
  python3 "${SCRIPT_DIR}/seed_k8s_ssh_probe.py" \
    --user "${SEED_K3S_USER}" \
    --key "${SEED_K3S_SSH_KEY}" \
    --timeout "${SEED_SSH_PROBE_TIMEOUT_SECONDS}" \
    --json-output "${ARTIFACT_DIR}/ssh_access.json" \
    --node "${SEED_K3S_MASTER_NAME}=${SEED_K3S_MASTER_IP}" \
    --node "${SEED_K3S_WORKER1_NAME}=${SEED_K3S_WORKER1_IP}" \
    --node "${SEED_K3S_WORKER2_NAME}=${SEED_K3S_WORKER2_IP}" \
    --strict >/dev/null
}

detect_default_iface() {
  local ip="$1"
  # Avoid SIGPIPE issues from `awk '{...; exit}'` when the producer keeps writing.
  run_ssh_probe "${SSH_EXEC_OPTS[@]}" "${SEED_K3S_USER}@${ip}" \
    "ip -o -4 route show to default | sed -n '1{s/.* dev \\([^ ]*\\).*/\\1/p}'"
}

write_capacity_gate_artifact() {
  local reference_cluster
  reference_cluster="${SEED_CLUSTER_REFERENCE:-false}"
  local max_validated_topology_size
  max_validated_topology_size="${SEED_CLUSTER_MAX_VALIDATED_TOPOLOGY_SIZE:-0}"
  python3 - <<PY
import json
from datetime import datetime, timezone
from pathlib import Path

artifact_path = Path(${ARTIFACT_DIR@Q}) / "capacity_gate.json"
payload = {
    "generated_at": datetime.now(timezone.utc).isoformat(),
    "profile_id": ${SEED_EXPERIMENT_PROFILE@Q},
    "cluster": ${SEED_K3S_CLUSTER_NAME@Q},
    "reference_cluster": ${reference_cluster@Q} == "true",
    "topology_size": int(${SEED_TOPOLOGY_SIZE@Q}),
    "max_validated_topology_size": int(${max_validated_topology_size@Q}),
    "expected_nodes": int(${EXPECTED_NODES@Q}),
    "capacity_gate": ${SEED_PROFILE_CAPACITY_GATE@Q},
    "capacity_gate_status": ${CAPACITY_GATE_STATUS@Q},
    "next_step": (
        f"Use SEED_TOPOLOGY_SIZE={int(${max_validated_topology_size@Q})} on the current reference cluster, "
        "or switch to a larger cluster inventory for bigger runs."
    ),
}
artifact_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
PY
}

enforce_capacity_gate() {
  local max_validated_topology_size
  max_validated_topology_size="${SEED_CLUSTER_MAX_VALIDATED_TOPOLOGY_SIZE:-0}"

  if [ "${max_validated_topology_size}" -gt 0 ] && [ "${SEED_TOPOLOGY_SIZE}" -le "${max_validated_topology_size}" ]; then
    CAPACITY_GATE_STATUS="open"
    return 0
  fi

  if [ "${max_validated_topology_size}" -gt 0 ] && [ "${SEED_TOPOLOGY_SIZE}" -gt "${max_validated_topology_size}" ]; then
    CAPACITY_GATE_STATUS="gated"
    write_capacity_gate_artifact
    fail_with_reason "capacity_gated" "${ARTIFACT_DIR}/capacity_gate.json" \
      "SEED_TOPOLOGY_SIZE=${max_validated_topology_size} scripts/seed_k8s_profile_runner.sh ${SEED_EXPERIMENT_PROFILE} doctor" \
      "Select a larger cluster inventory and rerun with SEED_TOPOLOGY_SIZE=${SEED_TOPOLOGY_SIZE}"
  fi

  CAPACITY_GATE_STATUS="open"
  return 0
}

repair_registry_connectivity() {
  log "Attempting quick registry remediation on master"
  run_ssh_probe "${SSH_EXEC_OPTS[@]}" "${SEED_K3S_USER}@${SEED_K3S_MASTER_IP}" \
    "set -euo pipefail; \
     sudo -n docker rm -f registry >/dev/null 2>&1 || true; \
     if ! sudo -n docker image inspect registry:2 >/dev/null 2>&1; then \
       sudo -n docker pull registry:2 >/dev/null 2>&1 || (sudo -n docker pull docker.m.daocloud.io/library/registry:2 >/dev/null && sudo -n docker tag docker.m.daocloud.io/library/registry:2 registry:2 >/dev/null); \
     fi; \
     sudo -n docker run -d --network host --restart=always --name registry \
       -e REGISTRY_HTTP_ADDR=0.0.0.0:${SEED_REGISTRY_PORT} registry:2 >/dev/null"

  local i
  for i in $(seq 1 12); do
    if run_ssh_probe "${SSH_EXEC_OPTS[@]}" "${SEED_K3S_USER}@${SEED_K3S_WORKER1_IP}" "curl -m 5 -fsS http://${SEED_REGISTRY_HOST}:${SEED_REGISTRY_PORT}/v2/ >/dev/null" >/dev/null 2>&1 \
      && run_ssh_probe "${SSH_EXEC_OPTS[@]}" "${SEED_K3S_USER}@${SEED_K3S_WORKER2_IP}" "curl -m 5 -fsS http://${SEED_REGISTRY_HOST}:${SEED_REGISTRY_PORT}/v2/ >/dev/null" >/dev/null 2>&1; then
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
  conf_dir="$(run_ssh_probe "${SSH_EXEC_OPTS[@]}" "${SEED_K3S_USER}@${SEED_K3S_MASTER_IP}" \
    "sudo -n sh -c 'sed -n \"s/^\\s*conf_dir\\s*=\\s*\\\"\\([^\\\"]*\\)\\\".*/\\1/p\" /var/lib/rancher/k3s/agent/etc/containerd/config.toml | head -n 1' 2>/dev/null" \
    || true)"
  bin_dir="$(run_ssh_probe "${SSH_EXEC_OPTS[@]}" "${SEED_K3S_USER}@${SEED_K3S_MASTER_IP}" \
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

repair_multus_kubeconfig_bridge_for_k3s() {
  log "Ensuring Multus kubeconfig compatibility path on K3s nodes"
  local host
  for host in "${SEED_K3S_MASTER_IP}" "${SEED_K3S_WORKER1_IP}" "${SEED_K3S_WORKER2_IP}"; do
    run_ssh_probe_with_timeout "${SEED_SSH_LONG_PROBE_TIMEOUT_SECONDS}" "${SSH_EXEC_OPTS[@]}" "${SEED_K3S_USER}@${host}" \
      "set -euo pipefail; \
       sudo -n mkdir -p /etc/cni/net.d; \
       if [ ! -L /etc/cni/net.d/multus.d ] || [ \"\$(readlink -f /etc/cni/net.d/multus.d 2>/dev/null || true)\" != \"/var/lib/rancher/k3s/agent/etc/cni/net.d/multus.d\" ]; then \
         sudo -n rm -rf /etc/cni/net.d/multus.d; \
         sudo -n ln -s /var/lib/rancher/k3s/agent/etc/cni/net.d/multus.d /etc/cni/net.d/multus.d; \
       fi; \
       for i in \$(seq 1 30); do \
         if sudo -n test -f /etc/cni/net.d/multus.d/multus.kubeconfig; then \
           exit 0; \
         fi; \
         sleep 2; \
       done; \
       exit 1" >/dev/null 2>&1 || return 1
  done
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
    run_ssh_probe "${SSH_EXEC_OPTS[@]}" "${SEED_K3S_USER}@${host}" \
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

write_image_refs_artifact() {
  if [ -s "${COMPILE_DIR}/images.txt" ]; then
    cp "${COMPILE_DIR}/images.txt" "${ARTIFACT_DIR}/image_refs.txt"
  else
    awk '/^seedemu_build_and_push / {print $2}' "${COMPILE_DIR}/build_images.sh" > "${ARTIFACT_DIR}/image_refs.txt"
  fi

  if [ ! -s "${ARTIFACT_DIR}/image_refs.txt" ]; then
    fail_with_reason "compile_missing_image_refs" "${COMPILE_DIR}/build_images.sh"       "scripts/validate_k3s_real_topology_multinode.sh compile" "sed -n '1,120p' ${COMPILE_DIR}/build_images.sh"
  fi
}

node_has_all_preloaded_images() {
  local node_ip="$1"
  local log_file="$2"
  local remote_list="/tmp/seedemu-image-refs-${RANDOM}.txt"

  : > "${log_file}"
  if ! scp "${SSH_OPTS[@]}" "${ARTIFACT_DIR}/image_refs.txt" "${SEED_K3S_USER}@${node_ip}:${remote_list}" >/dev/null 2>>"${log_file}"; then
    return 1
  fi

  if ssh "${SSH_EXEC_OPTS[@]}" "${SEED_K3S_USER}@${node_ip}" 'sudo -n bash -s' > "${log_file}" 2>&1 <<EOF
set -euo pipefail
present_file=$(mktemp)
trap 'rm -f "$present_file" "${remote_list}"' EXIT
sudo -n k3s ctr images list | awk 'NR > 1 {print $1}' | sort -u > "$present_file"
while IFS= read -r image; do
  [ -n "$image" ] || continue
  grep -Fx -- "$image" "$present_file" >/dev/null || exit 3
done < "${remote_list}"
echo all_images_present
EOF
  then
    return 0
  fi

  return 1
}
preload_images_on_node() {
  local node_ip="$1"
  local node_label="$2"
  local sample_image="$3"
  local log_file="${ARTIFACT_DIR}/preload_${node_label}.log"

  log "Preload: import images into ${node_label} (${node_ip})"
  if node_has_all_preloaded_images "${node_ip}" "${log_file}"; then
    echo "[preload] skip import: all images already present on ${node_label}" | tee -a "${log_file}"
  elif [ "${node_ip}" = "${SEED_K3S_MASTER_IP}" ]; then
    if ! ssh "${SSH_EXEC_OPTS[@]}" "${SEED_K3S_USER}@${SEED_K3S_MASTER_IP}" "sudo -n bash -lc '
      set -euo pipefail
      cd "${REMOTE_WORK_DIR}"
      xargs -r sudo -n docker save < images.txt | sudo -n k3s ctr images import -
    '" 2>&1 | tee "${log_file}"; then
      FAILURE_REASON="image_preload_failed"
      return 1
    fi
  else
    if ! ssh "${SSH_EXEC_OPTS[@]}" "${SEED_K3S_USER}@${SEED_K3S_MASTER_IP}" "sudo -n bash -lc '
      set -euo pipefail
      cd "${REMOTE_WORK_DIR}"
      xargs -r sudo -n docker save < images.txt
    '" | ssh "${SSH_OPTS[@]}" "${SEED_K3S_USER}@${node_ip}" "sudo -n k3s ctr images import -" 2>&1 | tee "${log_file}"; then
      FAILURE_REASON="image_preload_failed"
      return 1
    fi
  fi

  if ! ssh "${SSH_EXEC_OPTS[@]}" "${SEED_K3S_USER}@${node_ip}" "sudo -n k3s ctr images list | grep -F '${sample_image}'"     > "${ARTIFACT_DIR}/preload_${node_label}_sample.txt" 2>&1; then
    FAILURE_REASON="image_preload_failed"
    return 1
  fi
}

preload_images_to_cluster() {
  write_image_refs_artifact
  local sample_image
  sample_image="$(head -n 1 "${ARTIFACT_DIR}/image_refs.txt")"
  if [ -z "${sample_image}" ]; then
    FAILURE_REASON="compile_missing_image_refs"
    return 1
  fi

  preload_images_on_node "${SEED_K3S_MASTER_IP}" "master" "${sample_image}" || return 1
  preload_images_on_node "${SEED_K3S_WORKER1_IP}" "worker1" "${sample_image}" || return 1
  preload_images_on_node "${SEED_K3S_WORKER2_IP}" "worker2" "${sample_image}" || return 1
}

ensure_registry_ready_for_fallback() {
  repair_registry_connectivity || true

  if ! run_ssh_probe "${SSH_EXEC_OPTS[@]}" "${SEED_K3S_USER}@${SEED_K3S_MASTER_IP}" \
    "command -v docker >/dev/null 2>&1 && sudo -n docker ps --format '{{.Names}}' 2>/dev/null | grep -x registry" >/dev/null 2>&1; then
    return 1
  fi

  if ! run_ssh_probe "${SSH_EXEC_OPTS[@]}" "${SEED_K3S_USER}@${SEED_K3S_WORKER1_IP}" \
    "curl -m 5 -fsS http://${SEED_REGISTRY_HOST}:${SEED_REGISTRY_PORT}/v2/ >/dev/null" >/dev/null 2>&1; then
    return 1
  fi

  if ! run_ssh_probe "${SSH_EXEC_OPTS[@]}" "${SEED_K3S_USER}@${SEED_K3S_WORKER2_IP}" \
    "curl -m 5 -fsS http://${SEED_REGISTRY_HOST}:${SEED_REGISTRY_PORT}/v2/ >/dev/null" >/dev/null 2>&1; then
    return 1
  fi
}

switch_compiled_manifests_to_registry_pull() {
  if [ ! -f "${COMPILE_DIR}/k8s.yaml" ]; then
    return 0
  fi

  python3 - <<PY
from pathlib import Path

path = Path(${COMPILE_DIR@Q}) / "k8s.yaml"
text = path.read_text(encoding="utf-8")
text = text.replace('"imagePullPolicy": "IfNotPresent"', '"imagePullPolicy": "Always"')
text = text.replace('imagePullPolicy: IfNotPresent', 'imagePullPolicy: Always')
path.write_text(text, encoding="utf-8")
PY
  SEED_IMAGE_PULL_POLICY="Always"
}

run_registry_fallback_after_preload_failure() {
  if [ "${SEED_PRELOAD_FALLBACK_MODE}" != "registry" ]; then
    return 1
  fi

  log "Preload failed; retry build stage with registry push fallback"
  ensure_registry_ready_for_fallback || return 1

  if ! ssh "${SSH_EXEC_OPTS[@]}" "${SEED_K3S_USER}@${SEED_K3S_MASTER_IP}" "sudo -n env \
    SEED_BUILD_PARALLELISM=${SEED_BUILD_PARALLELISM} \
    SEED_DOCKER_BUILDKIT=${SEED_DOCKER_BUILDKIT} \
    SEED_REGISTRY_PUSH_RETRIES=${SEED_REGISTRY_PUSH_RETRIES} \
    SEED_REGISTRY_PUSH_BACKOFF_SECONDS=${SEED_REGISTRY_PUSH_BACKOFF_SECONDS} \
    SEED_DOCKER_MAX_CONCURRENT_UPLOADS=${SEED_DOCKER_MAX_CONCURRENT_UPLOADS} \
    SEED_REGISTRY_PUSH_TIMEOUT_SECONDS=${SEED_REGISTRY_PUSH_TIMEOUT_SECONDS} \
    SEED_IMAGE_DISTRIBUTION_MODE=registry \
    bash -lc '
    set -euo pipefail
    cd \"${REMOTE_WORK_DIR}\"
    ./build_images.sh
  '" 2>&1 | tee "${ARTIFACT_DIR}/remote_build_registry_fallback.log"; then
    FAILURE_REASON="registry_timeout"
    if ! grep -Eiq 'i/o timeout|Client\.Timeout|TLS handshake timeout|context deadline exceeded' "${ARTIFACT_DIR}/remote_build_registry_fallback.log"; then
      FAILURE_REASON="build_failed"
    fi
    return 1
  fi

  switch_compiled_manifests_to_registry_pull
  write_image_refs_artifact
  SEED_IMAGE_DISTRIBUTION_MODE="registry"
  FALLBACK_USED="preload_to_registry"
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

generate_effective_node_labels_json() {
  resolve_topology_paths

  if [ -n "${SEED_NODE_LABELS_JSON:-}" ]; then
    SEED_NODE_LABELS_JSON_EFFECTIVE="${SEED_NODE_LABELS_JSON}"
    printf '%s\n' "${SEED_NODE_LABELS_JSON_EFFECTIVE}" > "${ARTIFACT_DIR}/placement_expected.json"
    return 0
  fi

  SEED_CURRENT_PODS_JSON_PATH="${ARTIFACT_DIR}/cluster_pods.json" \
  SEED_NAMESPACE="${SEED_NAMESPACE}" \
  SEED_EXCLUDED_NAMESPACES="${SEED_NAMESPACE}" \
    python3 "${SCRIPT_DIR}/seed_k8s_plan_real_topology_by_as.py" \
      "${SEED_TOPOLOGY_FILE}" "${SEED_ASSIGNMENT_FILE}" "${ARTIFACT_DIR}/nodes.json" \
      "${ARTIFACT_DIR}/placement_expected.json" "${ARTIFACT_DIR}/placement_plan.json"
  SEED_NODE_LABELS_JSON_EFFECTIVE="$(cat "${ARTIFACT_DIR}/placement_expected.json")"
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
      "export SEED_PLACEMENT_MODE=by_as_hard && scripts/validate_k3s_real_topology_multinode.sh preflight" \
      "scripts/seed_k8s_profile_runner.sh ${SEED_EXPERIMENT_PROFILE} doctor"
  fi
  SEED_PLACEMENT_MODE="by_as_hard"
  SEED_SCHEDULING_STRATEGY="by_as_hard"

  if ! check_ssh_access; then
    fail_with_reason "ssh_access_failed" "${ARTIFACT_DIR}/ssh_access.json" \
      "export SEED_K3S_SSH_KEY=/path/to/key && scripts/validate_k3s_real_topology_multinode.sh preflight" \
      "python3 scripts/seed_k8s_ssh_probe.py --user ${SEED_K3S_USER} --key ${SEED_K3S_SSH_KEY} --node ${SEED_K3S_MASTER_NAME}=${SEED_K3S_MASTER_IP} --node ${SEED_K3S_WORKER1_NAME}=${SEED_K3S_WORKER1_IP} --node ${SEED_K3S_WORKER2_NAME}=${SEED_K3S_WORKER2_IP}"
  fi

  ensure_kubeconfig
  kubectl get nodes -o wide > "${ARTIFACT_DIR}/nodes_wide.txt"
  kubectl get nodes -o json > "${ARTIFACT_DIR}/nodes.json"
  kubectl get pods -A -o json > "${ARTIFACT_DIR}/cluster_pods.json"
  compute_expected_nodes
  enforce_capacity_gate

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

  if ! repair_multus_kubeconfig_bridge_for_k3s; then
    kubectl -n kube-system logs -l name=multus --tail=80 > "${ARTIFACT_DIR}/multus_logs_tail.txt" 2>/dev/null || true
    fail_with_reason "multus_not_ready" "${ARTIFACT_DIR}/multus_logs_tail.txt" \
      "scripts/setup_k3s_cluster.sh" "kubectl -n kube-system logs -l name=multus --tail=80"
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
      if run_ssh_probe "${SSH_EXEC_OPTS[@]}" "${SEED_K3S_USER}@${host}" \
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
        if run_ssh_probe "${SSH_EXEC_OPTS[@]}" "${SEED_K3S_USER}@${host}" \
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

  if [ "${SEED_IMAGE_DISTRIBUTION_MODE}" != "preload" ]; then
    if ! run_ssh_probe "${SSH_EXEC_OPTS[@]}" "${SEED_K3S_USER}@${SEED_K3S_MASTER_IP}"       "command -v docker >/dev/null 2>&1 && sudo -n docker ps --format '{{.Names}}' 2>/dev/null | grep -x registry" >/dev/null 2>&1; then
      repair_registry_connectivity || true
      if ! run_ssh_probe "${SSH_EXEC_OPTS[@]}" "${SEED_K3S_USER}@${SEED_K3S_MASTER_IP}"         "command -v docker >/dev/null 2>&1 && sudo -n docker ps --format '{{.Names}}' 2>/dev/null | grep -x registry" >/dev/null 2>&1; then
        fail_with_reason "registry_unreachable" "${ARTIFACT_DIR}/nodes_wide.txt"           "scripts/setup_k3s_cluster.sh" "ssh -i ${SEED_K3S_SSH_KEY} ${SEED_K3S_USER}@${SEED_K3S_MASTER_IP} 'sudo docker ps'"
      fi
    fi

    if ! run_ssh_probe "${SSH_EXEC_OPTS[@]}" "${SEED_K3S_USER}@${SEED_K3S_WORKER1_IP}"       "curl -m 5 -fsS http://${SEED_REGISTRY_HOST}:${SEED_REGISTRY_PORT}/v2/ >/dev/null" >/dev/null 2>&1       || ! run_ssh_probe "${SSH_EXEC_OPTS[@]}" "${SEED_K3S_USER}@${SEED_K3S_WORKER2_IP}"       "curl -m 5 -fsS http://${SEED_REGISTRY_HOST}:${SEED_REGISTRY_PORT}/v2/ >/dev/null" >/dev/null 2>&1; then
      repair_registry_connectivity || true
      if ! run_ssh_probe "${SSH_EXEC_OPTS[@]}" "${SEED_K3S_USER}@${SEED_K3S_WORKER1_IP}"         "curl -m 5 -fsS http://${SEED_REGISTRY_HOST}:${SEED_REGISTRY_PORT}/v2/ >/dev/null" >/dev/null 2>&1         || ! run_ssh_probe "${SSH_EXEC_OPTS[@]}" "${SEED_K3S_USER}@${SEED_K3S_WORKER2_IP}"         "curl -m 5 -fsS http://${SEED_REGISTRY_HOST}:${SEED_REGISTRY_PORT}/v2/ >/dev/null" >/dev/null 2>&1; then
        fail_with_reason "registry_unreachable" "${ARTIFACT_DIR}/nodes_wide.txt"           "scripts/setup_k3s_cluster.sh" "ssh -i ${SEED_K3S_SSH_KEY} ${SEED_K3S_USER}@${SEED_K3S_WORKER1_IP} 'curl -v http://${SEED_REGISTRY_HOST}:${SEED_REGISTRY_PORT}/v2/'"
      fi
    fi
  else
    log "Preflight: registry hard-check skipped because SEED_IMAGE_DISTRIBUTION_MODE=preload"
  fi

  resolve_cni_master_interface
  generate_effective_node_labels_json || fail_with_reason "placement_check_failed" "${ARTIFACT_DIR}/placement_plan.json" \
    "scripts/validate_k3s_real_topology_multinode.sh preflight" "cat ${ARTIFACT_DIR}/placement_plan.json"

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
    SEED_IMAGE_PULL_POLICY="${SEED_IMAGE_PULL_POLICY}" \
    SEED_NODE_LABELS_JSON="${SEED_NODE_LABELS_JSON_EFFECTIVE}" \
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

  local stage_start stage_duration
  stage_start="$(date +%s)"
  local tarball="${ARTIFACT_DIR}/compiled.tar.gz"
  tar -C "${COMPILE_DIR}" -czf "${tarball}" .

  run_ssh_probe "${SSH_EXEC_OPTS[@]}" "${SEED_K3S_USER}@${SEED_K3S_MASTER_IP}"     "rm -rf '${REMOTE_WORK_DIR}' && mkdir -p '${REMOTE_WORK_DIR}'"
  scp -q "${SSH_OPTS[@]}" "${tarball}" "${SEED_K3S_USER}@${SEED_K3S_MASTER_IP}:${REMOTE_WORK_DIR}/compiled.tar.gz"

  log "Build logs -> ${ARTIFACT_DIR}/remote_build.log"
  if ! ssh "${SSH_EXEC_OPTS[@]}" "${SEED_K3S_USER}@${SEED_K3S_MASTER_IP}" "sudo -n env     SEED_BUILD_PARALLELISM=${SEED_BUILD_PARALLELISM}     SEED_DOCKER_BUILDKIT=${SEED_DOCKER_BUILDKIT}     SEED_REGISTRY_PUSH_RETRIES=${SEED_REGISTRY_PUSH_RETRIES}     SEED_REGISTRY_PUSH_BACKOFF_SECONDS=${SEED_REGISTRY_PUSH_BACKOFF_SECONDS}     SEED_DOCKER_MAX_CONCURRENT_UPLOADS=${SEED_DOCKER_MAX_CONCURRENT_UPLOADS}     SEED_REGISTRY_PUSH_TIMEOUT_SECONDS=${SEED_REGISTRY_PUSH_TIMEOUT_SECONDS}     SEED_IMAGE_DISTRIBUTION_MODE=${SEED_IMAGE_DISTRIBUTION_MODE}     bash -lc '
    set -euo pipefail
    cd "${REMOTE_WORK_DIR}"
    tar -xzf compiled.tar.gz
    ./build_images.sh
  '" > "${ARTIFACT_DIR}/remote_build.log" 2>&1; then
    tail_log_on_failure "${ARTIFACT_DIR}/remote_build.log" 80
    if grep -Eiq 'i/o timeout|Client\.Timeout|TLS handshake timeout|context deadline exceeded' "${ARTIFACT_DIR}/remote_build.log"; then
      fail_with_reason "registry_timeout" "${ARTIFACT_DIR}/remote_build.log"         "scripts/validate_k3s_real_topology_multinode.sh build" "tail -n 200 ${ARTIFACT_DIR}/remote_build.log"
    fi
    fail_with_reason "build_failed" "${ARTIFACT_DIR}/remote_build.log"       "scripts/validate_k3s_real_topology_multinode.sh build" "tail -n 200 ${ARTIFACT_DIR}/remote_build.log"
  fi

  if [ "${SEED_IMAGE_DISTRIBUTION_MODE}" = "preload" ]; then
    if ! preload_images_to_cluster; then
      if ! run_registry_fallback_after_preload_failure; then
        fail_with_reason "${FAILURE_REASON:-image_preload_failed}" "${ARTIFACT_DIR}/preload_worker2.log" \
          "scripts/validate_k3s_real_topology_multinode.sh build" "tail -n 100 ${ARTIFACT_DIR}/preload_worker2.log"
      fi
    fi
  else
    write_image_refs_artifact
  fi

  stage_duration="$(( $(date +%s) - stage_start ))"
  BUILD_DURATION_SECONDS="${stage_duration}"
  write_stage_timing "build_duration_seconds" "${stage_duration}"
  write_diagnostics "${CURRENT_STAGE}" "PASS" "${ARTIFACT_DIR}/remote_build.log"     "scripts/validate_k3s_real_topology_multinode.sh deploy" "scripts/validate_k3s_real_topology_multinode.sh start-bird"
}

run_phased_startup() {
  CURRENT_STAGE="phase_start"
  local rc=0 stage_start stage_duration
  stage_start="$(date +%s)"
  python3 "${SEED_PHASE_START_DRIVER}" "${SEED_NAMESPACE}" "${ARTIFACT_DIR}" || rc=$?
  case "${rc}" in
    0)
      stage_duration="$(( $(date +%s) - stage_start ))"
      PHASE_START_DURATION_SECONDS="${stage_duration}"
      write_stage_timing "phase_start_duration_seconds" "${stage_duration}"
      write_diagnostics "${CURRENT_STAGE}" "PASS" "${ARTIFACT_DIR}/phased_startup_summary.json"         "scripts/validate_k3s_real_topology_multinode.sh verify" "kubectl -n ${SEED_NAMESPACE} get pods -o wide"
      return 0
      ;;
    10)
      fail_with_reason "bird_not_started" "${ARTIFACT_DIR}/phased_startup_summary.json"         "scripts/validate_k3s_real_topology_multinode.sh phase-start" "cat ${ARTIFACT_DIR}/bird_before_phase.txt"
      ;;
    20)
      fail_with_reason "ibgp_phase_failed" "${ARTIFACT_DIR}/phased_startup_summary.json"         "scripts/validate_k3s_real_topology_multinode.sh phase-start" "cat ${ARTIFACT_DIR}/bird_after_phase.txt"
      ;;
    30)
      fail_with_reason "ebgp_phase_failed" "${ARTIFACT_DIR}/phased_startup_summary.json"         "scripts/validate_k3s_real_topology_multinode.sh phase-start" "cat ${ARTIFACT_DIR}/bird_after_phase.txt"
      ;;
    41)
      fail_with_reason "kernel_switch_failed" "${ARTIFACT_DIR}/bird_kernel_summary.json"         "scripts/validate_k3s_real_topology_multinode.sh phase-start" "cat ${ARTIFACT_DIR}/bird_kernel.log"
      ;;
    *)
      fail_with_reason "phase_start_failed" "${ARTIFACT_DIR}/phased_startup.log"         "scripts/validate_k3s_real_topology_multinode.sh phase-start" "cat ${ARTIFACT_DIR}/phased_startup.log"
      ;;
  esac
}

run_start_bird() {
  CURRENT_STAGE="start_bird"
  LAST_COMMAND="python3 ${SCRIPT_DIR}/seed_k8s_start_bird0130.py ${SEED_NAMESPACE} ${ARTIFACT_DIR}"
  local rc=0 stage_start stage_duration
  stage_start="$(date +%s)"
  python3 "${SCRIPT_DIR}/seed_k8s_start_bird0130.py" "${SEED_NAMESPACE}" "${ARTIFACT_DIR}" || rc=$?
  case "${rc}" in
    0)
      stage_duration="$(( $(date +%s) - stage_start ))"
      write_stage_timing "start_bird_duration_seconds" "${stage_duration}"
      write_diagnostics "${CURRENT_STAGE}" "PASS" "${ARTIFACT_DIR}/start_bird_summary.json"         "scripts/validate_k3s_real_topology_multinode.sh start-kernel" "kubectl -n ${SEED_NAMESPACE} get pods -o wide"
      return 0
      ;;
    *)
      fail_with_reason "start_bird_failed" "${ARTIFACT_DIR}/start_bird_summary.json"         "scripts/validate_k3s_real_topology_multinode.sh start-bird" "cat ${ARTIFACT_DIR}/start_bird.log"
      ;;
  esac
}

run_start_kernel() {
  CURRENT_STAGE="start_kernel"
  LAST_COMMAND="python3 ${SCRIPT_DIR}/seed_k8s_start_bird_kernel.py ${SEED_NAMESPACE} ${ARTIFACT_DIR}"
  local rc=0 stage_start stage_duration
  stage_start="$(date +%s)"
  python3 "${SCRIPT_DIR}/seed_k8s_start_bird_kernel.py" "${SEED_NAMESPACE}" "${ARTIFACT_DIR}" || rc=$?
  case "${rc}" in
    0)
      stage_duration="$(( $(date +%s) - stage_start ))"
      write_stage_timing "start_kernel_duration_seconds" "${stage_duration}"
      write_diagnostics "${CURRENT_STAGE}" "PASS" "${ARTIFACT_DIR}/start_kernel_summary.json"         "scripts/validate_k3s_real_topology_multinode.sh verify" "kubectl -n ${SEED_NAMESPACE} get pods -o wide"
      return 0
      ;;
    *)
      fail_with_reason "start_kernel_failed" "${ARTIFACT_DIR}/start_kernel_summary.json"         "scripts/validate_k3s_real_topology_multinode.sh start-kernel" "cat ${ARTIFACT_DIR}/start_kernel.log"
      ;;
  esac
}

force_finalize_namespace() {
  local namespace="$1"
  python3 - "${namespace}" <<'PY'
import json
import subprocess
import sys

namespace = sys.argv[1]
result = subprocess.run(
    ["kubectl", "get", "namespace", namespace, "-o", "json"],
    text=True,
    capture_output=True,
)
if result.returncode != 0:
    raise SystemExit(0)

payload = json.loads(result.stdout)
payload.setdefault("spec", {})["finalizers"] = []
finalize = subprocess.run(
    ["kubectl", "replace", "--raw", f"/api/v1/namespaces/{namespace}/finalize", "-f", "-"],
    input=json.dumps(payload),
    text=True,
)
raise SystemExit(finalize.returncode)
PY
}

aggressive_namespace_cleanup() {
  local namespace="$1"

  if ! kubectl get namespace "${namespace}" >/dev/null 2>&1; then
    return 0
  fi

  kubectl -n "${namespace}" delete deployment --all --wait=false >/dev/null 2>&1 || true
  kubectl -n "${namespace}" delete network-attachment-definitions.k8s.cni.cncf.io --all --wait=false >/dev/null 2>&1 || true
  kubectl -n "${namespace}" delete pod --all --force --grace-period=0 >/dev/null 2>&1 || true
  kubectl delete namespace "${namespace}" --wait=false >/dev/null 2>&1 || true
}

ensure_clean_namespace() {
  local namespace="$1"
  aggressive_namespace_cleanup "${namespace}"

  if ! kubectl get namespace "${namespace}" >/dev/null 2>&1; then
    return 0
  fi

  if ! kubectl wait --for=delete namespace/"${namespace}" --timeout=90s >/dev/null 2>&1; then
    log "Namespace ${namespace} is still terminating; retrying aggressive cleanup and forcing finalization."
    aggressive_namespace_cleanup "${namespace}"
    force_finalize_namespace "${namespace}" >/dev/null 2>&1 || true
    kubectl wait --for=delete namespace/"${namespace}" --timeout=90s >/dev/null 2>&1 || true
  fi

  if kubectl get namespace "${namespace}" >/dev/null 2>&1; then
    kubectl get namespace "${namespace}" -o yaml > "${ARTIFACT_DIR}/namespace_delete_blocked.yaml" 2>/dev/null || true
    kubectl -n "${namespace}" get deploy -o wide > "${ARTIFACT_DIR}/namespace_delete_blocked_deployments.txt" 2>/dev/null || true
    kubectl -n "${namespace}" get pods -o wide > "${ARTIFACT_DIR}/namespace_delete_blocked_pods.txt" 2>/dev/null || true
    kubectl -n "${namespace}" get network-attachment-definitions.k8s.cni.cncf.io > "${ARTIFACT_DIR}/namespace_delete_blocked_network_attachments.txt" 2>/dev/null || true
    fail_with_reason "namespace_delete_blocked" "${ARTIFACT_DIR}/namespace_delete_blocked.yaml" \
      "kubectl delete namespace ${namespace} --wait=false" \
      "kubectl get namespace ${namespace} -o yaml"
  fi
}

run_deploy() {
  CURRENT_STAGE="deploy"
  log "Deploy: apply k8s.yaml to namespace ${SEED_NAMESPACE} (bird stays stopped)"

  local stage_start stage_duration
  stage_start="$(date +%s)"

  if [ "${CLEAN_NAMESPACE}" = "true" ]; then
    ensure_clean_namespace "${SEED_NAMESPACE}"
  fi

  kubectl create namespace "${SEED_NAMESPACE}" --dry-run=client -o yaml | kubectl apply -f - >/dev/null
  if ! kubectl -n "${SEED_NAMESPACE}" apply -f "${COMPILE_DIR}/k8s.yaml" > "${ARTIFACT_DIR}/apply.log" 2>&1; then
    tail_log_on_failure "${ARTIFACT_DIR}/apply.log" 80
    fail_with_reason "deploy_wait_timeout_or_failure" "${ARTIFACT_DIR}/apply.log" \
      "scripts/validate_k3s_real_topology_multinode.sh deploy" "kubectl -n ${SEED_NAMESPACE} get pods -o wide"
  fi

  local namespace_phase
  namespace_phase="$(kubectl get namespace "${SEED_NAMESPACE}" -o jsonpath='{.status.phase}' 2>/dev/null || true)"
  if [ "${namespace_phase}" != "Active" ]; then
    kubectl get namespace "${SEED_NAMESPACE}" -o yaml > "${ARTIFACT_DIR}/namespace_not_active.yaml" 2>/dev/null || true
    fail_with_reason "namespace_delete_blocked" "${ARTIFACT_DIR}/namespace_not_active.yaml" \
      "kubectl delete namespace ${SEED_NAMESPACE} --wait=false" \
      "kubectl get namespace ${SEED_NAMESPACE} -o yaml"
  fi

  if ! kubectl -n "${SEED_NAMESPACE}" wait --for=condition=Available --timeout="${DEPLOY_WAIT_TIMEOUT}" deployment --all > "${ARTIFACT_DIR}/wait.log" 2>&1; then
    tail_log_on_failure "${ARTIFACT_DIR}/wait.log" 80
    kubectl -n "${SEED_NAMESPACE}" get pods -o wide > "${ARTIFACT_DIR}/pods_wide.txt" 2>/dev/null || true
    kubectl -n "${SEED_NAMESPACE}" get deploy -o wide > "${ARTIFACT_DIR}/deployments_wide.txt" 2>/dev/null || true
    kubectl -n "${SEED_NAMESPACE}" get events --sort-by=.lastTimestamp > "${ARTIFACT_DIR}/events.txt" 2>/dev/null || true
    fail_with_reason "deploy_wait_timeout_or_failure" "${ARTIFACT_DIR}/wait.log"       "scripts/validate_k3s_real_topology_multinode.sh deploy" "kubectl -n ${SEED_NAMESPACE} get pods -o wide"
  fi

  kubectl -n "${SEED_NAMESPACE}" get pods -o wide > "${ARTIFACT_DIR}/pods_wide.txt"
  kubectl -n "${SEED_NAMESPACE}" get deploy -o wide > "${ARTIFACT_DIR}/deployments_wide.txt"
  stage_duration="$(( $(date +%s) - stage_start ))"
  UP_DURATION_SECONDS="${stage_duration}"
  write_stage_timing "up_duration_seconds" "${stage_duration}"
  write_diagnostics "${CURRENT_STAGE}" "PASS" "${ARTIFACT_DIR}/deployments_wide.txt"     "scripts/validate_k3s_real_topology_multinode.sh start-bird" "kubectl -n ${SEED_NAMESPACE} get pods -o wide"
}

list_router_pods() {
  python3 - "${SEED_NAMESPACE}" <<'PY'
import json
import subprocess
import sys

ns = sys.argv[1]
out = subprocess.check_output(["kubectl", "-n", ns, "get", "pods", "-o", "json"], text=True)
data = json.loads(out)
router_pods = []
for item in data.get("items", []):
    labels = item.get("metadata", {}).get("labels", {}) or {}
    name = str(labels.get("seedemu.io/name", ""))
    if name.startswith("r"):
        router_pods.append(item["metadata"]["name"])
for pod in sorted(router_pods):
    print(pod)
raise SystemExit(0 if router_pods else 1)
PY
}

run_materialize_validation_contract() {
  if ! python3 "${SCRIPT_DIR}/seed_k8s_validation_contract.py" materialize \
    "${SEED_NAMESPACE}" "${ARTIFACT_DIR}" "${SEED_EXPERIMENT_PROFILE}" \
    --kubectl-timeout "${SEED_KUBECTL_EXEC_TIMEOUT_SECONDS}" >/dev/null 2>&1; then
    FAILURE_REASON="artifact_materialization_failed"
    return 1
  fi
  return 0
}

run_verify_connectivity() {
  if ! run_materialize_validation_contract; then
    return 1
  fi
  CONNECTIVITY_PASSED="$(python3 - <<PY
import json
from pathlib import Path
data = json.loads(Path("${ARTIFACT_DIR}/connectivity_summary.json").read_text(encoding="utf-8"))
print("true" if data.get("passed", False) else "false")
PY
)"
  if [ "${CONNECTIVITY_PASSED}" != "true" ]; then
    FAILURE_REASON="connectivity_check_failed"
    return 1
  fi
  return 0
}

run_verify_recovery() {
  if ! python3 "${SCRIPT_DIR}/seed_k8s_failure_injection.py" \
    "${SEED_NAMESPACE}" "${ARTIFACT_DIR}" \
    --timeout-seconds 600 \
    --kubectl-exec-timeout "${SEED_KUBECTL_EXEC_TIMEOUT_SECONDS}" >/dev/null 2>&1; then
    FAILURE_REASON="recovery_check_failed"
    return 1
  fi
  RECOVERY_PASSED="$(python3 - <<PY
import json
from pathlib import Path
data = json.loads(Path("${ARTIFACT_DIR}/failure_injection_summary.json").read_text(encoding="utf-8"))
print("true" if data.get("status") == "pass" else "false")
PY
)"
  if [ "${RECOVERY_PASSED}" != "true" ]; then
    FAILURE_REASON="recovery_check_failed"
    return 1
  fi
  if ! python3 "${SCRIPT_DIR}/seed_k8s_validation_contract.py" assert \
    "${ARTIFACT_DIR}" \
    --profile-file "${REPO_ROOT}/configs/seed_k8s_profiles.yaml" \
    --profile-id "${SEED_EXPERIMENT_PROFILE}" >/dev/null 2>&1; then
    FAILURE_REASON="artifact_contract_failed"
    return 1
  fi
  return 0
}

run_verify() {
  CURRENT_STAGE="verify"
  local stage_start_ts stage_duration
  stage_start_ts="$(date +%s)"
  log "Verify: expected count + by-AS hard placement + full-namespace BGP health"

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
    fail_with_reason "placement_check_failed" "${ARTIFACT_DIR}/counts.json"       "scripts/validate_k3s_real_topology_multinode.sh verify" "cat ${ARTIFACT_DIR}/counts.json"
  fi

  local placement_reason=""
  if ! placement_reason="$(python3 "${SCRIPT_DIR}/seed_k8s_verify_by_as_placement.py"       "${SEED_NAMESPACE}" "${ARTIFACT_DIR}" "${SEED_PLACEMENT_MODE}" "${SEED_MIN_NODES_USED}"       "${ARTIFACT_DIR}/placement_expected.json" 2>/dev/null)"; then
    fail_with_reason "${placement_reason:-placement_check_failed}" "${ARTIFACT_DIR}/placement_check.json"       "scripts/validate_k3s_real_topology_multinode.sh verify" "cat ${ARTIFACT_DIR}/placement_by_as.tsv"
  fi

  NODES_USED="$(python3 - <<PY2
import json
from pathlib import Path
x = json.loads(Path("${ARTIFACT_DIR}/placement_check.json").read_text(encoding="utf-8"))
print(int(x.get("nodes_used_count", 0)))
PY2
)"
  PLACEMENT_PASSED="true"

  local bgp_reason="" deadline now
  deadline="$(( $(date +%s) + BGP_WAIT_TIMEOUT_SECONDS ))"
  while true; do
    if bgp_reason="$(python3 "${SCRIPT_DIR}/seed_k8s_bgp_health.py" \
        "${SEED_NAMESPACE}" "${ARTIFACT_DIR}" \
        --parallelism "${BGP_HEALTH_PARALLELISM}" \
        --kubectl-timeout "${SEED_KUBECTL_EXEC_TIMEOUT_SECONDS}" 2>/dev/null)"; then
      break
    fi
    now="$(date +%s)"
    if [ "${now}" -ge "${deadline}" ]; then
      fail_with_reason "${bgp_reason:-bgp_not_established}" "${ARTIFACT_DIR}/bgp_health_summary.json"         "scripts/validate_k3s_real_topology_multinode.sh verify" "cat ${ARTIFACT_DIR}/bgp_health_failures.txt"
    fi
    sleep 5
  done
  BGP_PASSED="true"
  run_verify_connectivity || return 1
  run_verify_recovery || return 1
  OVERALL_PASSED="true"
  stage_duration="$(( $(date +%s) - stage_start_ts ))"
  write_stage_timing "validation_duration_seconds" "${stage_duration}"

  write_diagnostics "${CURRENT_STAGE}" "PASS" "${ARTIFACT_DIR}/failure_injection_summary.json"     "scripts/validate_k3s_real_topology_multinode.sh verify" "kubectl -n ${SEED_NAMESPACE} get pods -o wide"
}

run_clean() {
  CURRENT_STAGE="clean"
  log "Clean: namespace ${SEED_NAMESPACE}"
  ensure_kubeconfig
  kubectl delete namespace "${SEED_NAMESPACE}" --ignore-not-found >/dev/null 2>&1 || true
  write_diagnostics "${CURRENT_STAGE}" "PASS" "${ARTIFACT_DIR}/summary.json" \
    "scripts/validate_k3s_real_topology_multinode.sh all" "scripts/seed_k8s_profile_runner.sh ${SEED_EXPERIMENT_PROFILE} all"
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
      run_phased_startup
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
    phase-start)
      run_preflight
      run_phased_startup
      write_summary "PASS" "$(( $(date +%s) - START_TS ))"
      ;;
    start-bird)
      run_preflight
      run_start_bird
      write_summary "PASS" "$(( $(date +%s) - START_TS ))"
      ;;
    start-kernel)
      run_preflight
      run_start_kernel
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
