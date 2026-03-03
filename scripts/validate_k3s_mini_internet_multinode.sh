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

SEED_K3S_MASTER_NAME="${SEED_K3S_MASTER_NAME:-seed-k3s-master}"
SEED_K3S_WORKER1_NAME="${SEED_K3S_WORKER1_NAME:-seed-k3s-worker1}"
SEED_K3S_WORKER2_NAME="${SEED_K3S_WORKER2_NAME:-seed-k3s-worker2}"

SEED_NAMESPACE="${SEED_NAMESPACE:-seedemu-k3s-mini-mn}"
SEED_REGISTRY_HOST="${SEED_REGISTRY_HOST:-${SEED_K3S_MASTER_IP}}"
SEED_REGISTRY_PORT="${SEED_REGISTRY_PORT:-5000}"
SEED_REGISTRY="${SEED_REGISTRY:-${SEED_REGISTRY_HOST}:${SEED_REGISTRY_PORT}}"
if [ "${SEED_REGISTRY}" = "localhost:5001" ] || [ "${SEED_REGISTRY}" = "localhost:5000" ]; then
  # scripts/env_seedemu.sh defaults to localhost registry for kind; override to K3s master registry.
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
SEED_PLACEMENT_MODE="${SEED_PLACEMENT_MODE:-auto}"
SEED_SCHEDULING_STRATEGY="${SEED_SCHEDULING_STRATEGY:-}"
SEED_MIN_NODES_USED="${SEED_MIN_NODES_USED:-2}"
SEED_REQUIRE_ALL_NODES="${SEED_REQUIRE_ALL_NODES:-false}"
SEED_HOSTS_PER_AS="${SEED_HOSTS_PER_AS:-2}"
CONNECTIVITY_RETRY="${CONNECTIVITY_RETRY:-24}"
CONNECTIVITY_RETRY_INTERVAL_SECONDS="${CONNECTIVITY_RETRY_INTERVAL_SECONDS:-5}"
BGP_WAIT_TIMEOUT_SECONDS="${BGP_WAIT_TIMEOUT_SECONDS:-300}"
DEPLOY_WAIT_TIMEOUT="${DEPLOY_WAIT_TIMEOUT:-1800s}"
CLEAN_NAMESPACE="${SEED_CLEAN_NAMESPACE:-true}"
SEED_AUTO_CNI_FALLBACK="${SEED_AUTO_CNI_FALLBACK:-false}"
SEED_EXPERIMENT_PROFILE="${SEED_EXPERIMENT_PROFILE:-mini_internet}"
SEED_AGENT_PROACTIVE_MODE="${SEED_AGENT_PROACTIVE_MODE:-guided}"
SEED_FAILURE_ACTION_MAP="${SEED_FAILURE_ACTION_MAP:-${REPO_ROOT}/configs/seed_failure_action_map.yaml}"

RUN_ID="${SEED_RUN_ID:-$(date +%Y%m%d_%H%M%S)}"
DEFAULT_ARTIFACT_DIR="${REPO_ROOT}/output/multinode_mini_validation/${RUN_ID}"
SEED_ARTIFACT_DIR="${SEED_ARTIFACT_DIR:-${DEFAULT_ARTIFACT_DIR}}"
SEED_OUTPUT_DIR="${SEED_OUTPUT_DIR:-${SEED_ARTIFACT_DIR}/compiled}"

KUBECONFIG_PATH="${REPO_ROOT}/output/kubeconfigs/${SEED_K3S_CLUSTER_NAME}.yaml"
EXAMPLE_DIR="${REPO_ROOT}/examples/kubernetes"
COMPILE_DIR="${SEED_OUTPUT_DIR}"
ARTIFACT_DIR="${SEED_ARTIFACT_DIR}"
REMOTE_WORK_BASE="/tmp/seedemu-mini-multinode"
REMOTE_WORK_DIR="${REMOTE_WORK_BASE}-${RUN_ID}"
STAGE_TIMELINE_PATH="${ARTIFACT_DIR}/stage_timeline.json"
DIAGNOSTICS_PATH="${ARTIFACT_DIR}/diagnostics.json"
NEXT_ACTIONS_PATH="${ARTIFACT_DIR}/next_actions.json"

PRECHECK_REPAIRED="false"
FALLBACK_USED="none"
FAILURE_REASON=""
STRICT3_PASSED="false"
PLACEMENT_PASSED="false"
BGP_PASSED="false"
CONNECTIVITY_PASSED="false"
RECOVERY_PASSED="false"
NODES_USED="0"
START_TS="$(date +%s)"
CURRENT_STAGE="init"
LAST_COMMAND=""
LAST_FAILURE_CODE=""

MASTER_NODE_NAME=""
WORKER1_NODE_NAME=""
WORKER2_NODE_NAME=""
EFFECTIVE_CNI_IFACE=""
SEED_NODE_LABELS_JSON_EFFECTIVE=""

SSH_OPTS=(
  -o StrictHostKeyChecking=no
  -o UserKnownHostsFile=/dev/null
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
Usage: scripts/validate_k3s_mini_internet_multinode.sh [all|preflight|compile|build|deploy|verify|clean]

Actions:
  all       Run full pipeline: preflight -> compile -> build -> deploy -> verify
  preflight Run health checks and auto-repair once if needed
  compile   Compile mini-internet into Kubernetes manifests
  build     Build and push images on K3s master
  deploy    Apply manifests and wait until all deployments are Available
  verify    Verify placement gate + BGP + connectivity + self-healing
  clean     Delete namespace resources used by this workflow
USAGE
}

require_cmd() {
  if ! command -v "$1" >/dev/null 2>&1; then
    echo "Missing required command: $1" >&2
    exit 1
  fi
}

normalize_placement_mode() {
  case "${SEED_PLACEMENT_MODE}" in
    auto|strict3)
      ;;
    *)
      log "Unknown SEED_PLACEMENT_MODE='${SEED_PLACEMENT_MODE}', falling back to 'auto'"
      SEED_PLACEMENT_MODE="auto"
      ;;
  esac
}

resolve_scheduling_defaults() {
  normalize_placement_mode

  if [ -z "${SEED_SCHEDULING_STRATEGY}" ]; then
    if [ "${SEED_PLACEMENT_MODE}" = "strict3" ]; then
      SEED_SCHEDULING_STRATEGY="custom"
    else
      SEED_SCHEDULING_STRATEGY="auto"
    fi
  fi
}

ensure_dirs() {
  mkdir -p "${ARTIFACT_DIR}"
  mkdir -p "$(dirname "${COMPILE_DIR}")"
}

record_stage_event() {
  local stage="$1"
  local status="$2"
  local command="$3"
  local artifact="$4"
  local failure_reason="${5:-}"

  STAGE_EVENT_STAGE="${stage}" \
  STAGE_EVENT_STATUS="${status}" \
  STAGE_EVENT_COMMAND="${command}" \
  STAGE_EVENT_ARTIFACT="${artifact}" \
  STAGE_EVENT_FAILURE_REASON="${failure_reason}" \
  STAGE_TIMELINE_PATH="${STAGE_TIMELINE_PATH}" \
  python3 - <<'PY'
import json
import os
from datetime import datetime, timezone
from pathlib import Path

path = Path(os.environ["STAGE_TIMELINE_PATH"])
if path.exists():
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        data = []
else:
    data = []

if not isinstance(data, list):
    data = []

data.append(
    {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "stage": os.environ.get("STAGE_EVENT_STAGE", ""),
        "status": os.environ.get("STAGE_EVENT_STATUS", ""),
        "command": os.environ.get("STAGE_EVENT_COMMAND", ""),
        "artifact": os.environ.get("STAGE_EVENT_ARTIFACT", ""),
        "failure_reason": os.environ.get("STAGE_EVENT_FAILURE_REASON", ""),
    }
)
path.write_text(json.dumps(data, indent=2), encoding="utf-8")
PY
}

resolve_failure_code() {
  local reason="$1"

  case "${reason}" in
    kubeconfig_not_found_after_fetch|kubeconfig_fetch_failed)
      echo "KCFG_MISSING"
      return
      ;;
    ssh_key_not_found)
      echo "SSH_KEY_INVALID"
      return
      ;;
    compile_missing_k8s_yaml|compile_missing_build_script)
      echo "COMPILE_FAILED"
      return
      ;;
    build_failed)
      echo "BUILD_FAILED"
      return
      ;;
    deploy_wait_timeout_or_failure|deploy_failed|deploy_failed_after_cni_fallback)
      echo "DEPLOY_TIMEOUT"
      return
      ;;
    strict3_placement_failed|placement_check_failed)
      echo "PLACEMENT_FAILED"
      return
      ;;
    bgp_not_established)
      echo "BGP_NOT_ESTABLISHED"
      return
      ;;
    connectivity_check_failed)
      echo "CONNECTIVITY_FAILED"
      return
      ;;
    recovery_check_failed)
      echo "RECOVERY_FAILED"
      return
      ;;
  esac

  if [ -f "${ARTIFACT_DIR}/preflight.json" ]; then
    local preflight_code
    preflight_code="$(
      python3 - <<PY
import json
from pathlib import Path

p = Path(${ARTIFACT_DIR@Q}) / "preflight.json"
try:
    data = json.loads(p.read_text(encoding="utf-8"))
except Exception:
    print("")
    raise SystemExit(0)

if not data.get("kubeconfig_ok", True):
    print("KCFG_MISSING")
elif not data.get("k3s_nodes_ready", True):
    print("NODE_NOT_READY")
elif not data.get("multus_ready", True):
    print("MULTUS_NOT_READY")
elif (not data.get("registry_container_running", True)) or (not data.get("registry_reachable_from_workers", True)):
    print("REGISTRY_UNREACHABLE")
else:
    print("")
PY
    )"
    if [ -n "${preflight_code}" ]; then
      echo "${preflight_code}"
      return
    fi
  fi

  if [ "${CURRENT_STAGE}" = "preflight" ]; then
    echo "NODE_NOT_READY"
  else
    echo "DEPLOY_TIMEOUT"
  fi
}

write_diagnostics_and_next_actions() {
  local stage="$1"
  local status="$2"
  local failure_reason="${3:-}"
  local failure_code="$4"

  python3 - <<PY
import json
from pathlib import Path
import glob

try:
    import yaml  # type: ignore
except Exception:
    yaml = None

artifact_dir = Path(${ARTIFACT_DIR@Q}).resolve()
diag_path = Path(${DIAGNOSTICS_PATH@Q})
next_path = Path(${NEXT_ACTIONS_PATH@Q})
map_path = Path(${SEED_FAILURE_ACTION_MAP@Q})

failure_code = ${failure_code@Q}
stage = ${stage@Q}
status = ${status@Q}
failure_reason = ${failure_reason@Q}

failure_actions = {}
if map_path.exists() and yaml is not None:
    try:
        loaded = yaml.safe_load(map_path.read_text(encoding="utf-8")) or {}
        failure_actions = loaded.get("failure_actions", {}) if isinstance(loaded, dict) else {}
    except Exception:
        failure_actions = {}

entry = failure_actions.get(failure_code, {})

default_success_next = {
    "preflight": "scripts/validate_k3s_mini_internet_multinode.sh compile",
    "compile": "scripts/validate_k3s_mini_internet_multinode.sh build",
    "build": "scripts/validate_k3s_mini_internet_multinode.sh deploy",
    "deploy": "scripts/validate_k3s_mini_internet_multinode.sh verify",
    "verify": "scripts/inspect_k3s_mini_internet.sh ${SEED_NAMESPACE}",
    "clean": "scripts/validate_k3s_mini_internet_multinode.sh preflight",
    "all": "scripts/seedlab_report_from_artifacts.sh ${SEED_ARTIFACT_DIR}",
}

first_pattern = str(entry.get("first_evidence_pattern", "summary.json"))
matches = sorted(glob.glob(str(artifact_dir / first_pattern)))
if matches:
    first_evidence = matches[0]
else:
    candidate = artifact_dir / first_pattern
    first_evidence = str(candidate if candidate.exists() else artifact_dir / "summary.json")

if status == "PASS":
    minimal_retry = default_success_next.get(stage, "scripts/seedlab_report_from_artifacts.sh")
    fallback = minimal_retry
    operator_hint = "Stage passed; continue with suggested next stage"
    safe_auto_retry = True
    requires_confirmation = False
else:
    minimal_retry = str(entry.get("minimal_retry_command", "scripts/validate_k3s_mini_internet_multinode.sh verify"))
    fallback = str(entry.get("fallback_command", minimal_retry))
    operator_hint = str(entry.get("operator_hint", "Inspect artifact files and retry from failed stage"))
    safe_auto_retry = bool(entry.get("safe_auto_retry", False))
    requires_confirmation = bool(entry.get("requires_confirmation", False))

diagnostics = {
    "stage": stage,
    "status": status,
    "failure_reason": failure_reason,
    "failure_code": failure_code,
    "first_evidence_file": first_evidence,
    "minimal_retry_command": minimal_retry,
    "fallback_command": fallback,
    "operator_hint": operator_hint,
    "safe_auto_retry": safe_auto_retry,
    "requires_confirmation": requires_confirmation,
    "action_map_file": str(map_path),
}

next_actions = {
    "stage": stage,
    "status": status,
    "failure_code": failure_code,
    "first_evidence_file": first_evidence,
    "minimal_retry_command": minimal_retry,
    "fallback_command": fallback,
    "safe_auto_retry": safe_auto_retry,
    "requires_confirmation": requires_confirmation,
}

diag_path.write_text(json.dumps(diagnostics, indent=2), encoding="utf-8")
next_path.write_text(json.dumps(next_actions, indent=2), encoding="utf-8")
PY
}

write_summary() {
  local end_ts duration
  end_ts="$(date +%s)"
  duration="$((end_ts - START_TS))"

  python3 - <<PY
import json
from pathlib import Path

summary = {
    "cluster": "${SEED_K3S_CLUSTER_NAME}",
    "namespace": "${SEED_NAMESPACE}",
    "profile": "${SEED_EXPERIMENT_PROFILE}",
    "proactive_mode": "${SEED_AGENT_PROACTIVE_MODE}",
    "placement_mode": "${SEED_PLACEMENT_MODE}",
    "cni_type": "${SEED_CNI_TYPE}",
    "cni_master_interface": "${EFFECTIVE_CNI_IFACE}",
    "nodes_used": int("${NODES_USED}"),
    "placement_passed": "${PLACEMENT_PASSED}" == "true",
    "strict3_passed": "${STRICT3_PASSED}" == "true",
    "bgp_passed": "${BGP_PASSED}" == "true",
    "connectivity_passed": "${CONNECTIVITY_PASSED}" == "true",
    "recovery_passed": "${RECOVERY_PASSED}" == "true",
    "duration_seconds": int("${duration}"),
    "fallback_used": "${FALLBACK_USED}",
    "failure_reason": "${FAILURE_REASON}",
    "failure_code": "${LAST_FAILURE_CODE}",
}

Path("${ARTIFACT_DIR}").mkdir(parents=True, exist_ok=True)
Path("${ARTIFACT_DIR}/summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
PY
}

fail_with_reason() {
  FAILURE_REASON="$1"
  LAST_FAILURE_CODE="$(resolve_failure_code "${FAILURE_REASON}")"
  record_stage_event "${CURRENT_STAGE}" "FAIL" "${LAST_COMMAND}" "${ARTIFACT_DIR}" "${FAILURE_REASON}"
  write_summary
  write_diagnostics_and_next_actions "${CURRENT_STAGE}" "FAIL" "${FAILURE_REASON}" "${LAST_FAILURE_CODE}"
  echo "ERROR: ${FAILURE_REASON}" >&2
  exit 1
}

ensure_kubeconfig() {
  LAST_COMMAND="${SCRIPT_DIR}/k3s_fetch_kubeconfig.sh"
  if ! "${SCRIPT_DIR}/k3s_fetch_kubeconfig.sh" > "${ARTIFACT_DIR}/kubeconfig_fetch.log" 2>&1; then
    fail_with_reason "kubeconfig_fetch_failed"
  fi
  if [ ! -f "${KUBECONFIG_PATH}" ]; then
    fail_with_reason "kubeconfig_not_found_after_fetch"
  fi
  export KUBECONFIG="${KUBECONFIG_PATH}"
}

get_node_name_by_ip() {
  local ip="$1"
  kubectl get nodes -o wide --no-headers | awk -v ip="${ip}" '$6==ip {print $1; exit}'
}

detect_cluster_nodes() {
  MASTER_NODE_NAME="$(kubectl get nodes -l node-role.kubernetes.io/control-plane -o jsonpath='{.items[0].metadata.name}' 2>/dev/null || true)"
  if [ -z "${MASTER_NODE_NAME}" ]; then
    MASTER_NODE_NAME="$(kubectl get nodes -l node-role.kubernetes.io/master -o jsonpath='{.items[0].metadata.name}' 2>/dev/null || true)"
  fi

  WORKER1_NODE_NAME="$(get_node_name_by_ip "${SEED_K3S_WORKER1_IP}")"
  WORKER2_NODE_NAME="$(get_node_name_by_ip "${SEED_K3S_WORKER2_IP}")"

  if [ -z "${MASTER_NODE_NAME}" ]; then
    MASTER_NODE_NAME="$(get_node_name_by_ip "${SEED_K3S_MASTER_IP}")"
  fi

  if [ -z "${MASTER_NODE_NAME}" ] || [ -z "${WORKER1_NODE_NAME}" ] || [ -z "${WORKER2_NODE_NAME}" ]; then
    fail_with_reason "unable_to_detect_k3s_node_names"
  fi
}

resolve_cni_master_interface() {
  local master_iface worker1_iface worker2_iface

  master_iface="$(ssh "${SSH_OPTS[@]}" "${SEED_K3S_USER}@${SEED_K3S_MASTER_IP}" "ip -o -4 route show to default | sed -n '1{s/.* dev \\([^ ]*\\).*/\\1/p}'")"
  worker1_iface="$(ssh "${SSH_OPTS[@]}" "${SEED_K3S_USER}@${SEED_K3S_WORKER1_IP}" "ip -o -4 route show to default | sed -n '1{s/.* dev \\([^ ]*\\).*/\\1/p}'")"
  worker2_iface="$(ssh "${SSH_OPTS[@]}" "${SEED_K3S_USER}@${SEED_K3S_WORKER2_IP}" "ip -o -4 route show to default | sed -n '1{s/.* dev \\([^ ]*\\).*/\\1/p}'")"

  if [ -z "${master_iface}" ] || [ -z "${worker1_iface}" ] || [ -z "${worker2_iface}" ]; then
    fail_with_reason "failed_to_detect_default_route_interface"
  fi

  if [ "${master_iface}" != "${worker1_iface}" ] || [ "${master_iface}" != "${worker2_iface}" ]; then
    fail_with_reason "cni_master_interface_mismatch_across_nodes"
  fi

  if [ -n "${SEED_CNI_MASTER_INTERFACE}" ] && [ "${SEED_CNI_MASTER_INTERFACE}" != "${master_iface}" ]; then
    log "SEED_CNI_MASTER_INTERFACE=${SEED_CNI_MASTER_INTERFACE} overrides detected ${master_iface}"
    EFFECTIVE_CNI_IFACE="${SEED_CNI_MASTER_INTERFACE}"
  else
    EFFECTIVE_CNI_IFACE="${master_iface}"
  fi
}

set_effective_node_labels_json() {
  if [ -n "${SEED_NODE_LABELS_JSON:-}" ]; then
    SEED_NODE_LABELS_JSON_EFFECTIVE="${SEED_NODE_LABELS_JSON}"
    return
  fi

  if [ "${SEED_PLACEMENT_MODE}" != "strict3" ]; then
    SEED_NODE_LABELS_JSON_EFFECTIVE="{}"
    return
  fi

  SEED_NODE_LABELS_JSON_EFFECTIVE="$(cat <<JSON
{
  "2": {"kubernetes.io/hostname": "${MASTER_NODE_NAME}"},
  "3": {"kubernetes.io/hostname": "${MASTER_NODE_NAME}"},
  "4": {"kubernetes.io/hostname": "${MASTER_NODE_NAME}"},
  "11": {"kubernetes.io/hostname": "${MASTER_NODE_NAME}"},
  "12": {"kubernetes.io/hostname": "${MASTER_NODE_NAME}"},
  "100": {"kubernetes.io/hostname": "${MASTER_NODE_NAME}"},
  "101": {"kubernetes.io/hostname": "${MASTER_NODE_NAME}"},
  "102": {"kubernetes.io/hostname": "${MASTER_NODE_NAME}"},
  "103": {"kubernetes.io/hostname": "${MASTER_NODE_NAME}"},
  "104": {"kubernetes.io/hostname": "${MASTER_NODE_NAME}"},
  "105": {"kubernetes.io/hostname": "${MASTER_NODE_NAME}"},
  "150": {"kubernetes.io/hostname": "${WORKER1_NODE_NAME}"},
  "152": {"kubernetes.io/hostname": "${WORKER1_NODE_NAME}"},
  "154": {"kubernetes.io/hostname": "${WORKER1_NODE_NAME}"},
  "160": {"kubernetes.io/hostname": "${WORKER1_NODE_NAME}"},
  "162": {"kubernetes.io/hostname": "${WORKER1_NODE_NAME}"},
  "164": {"kubernetes.io/hostname": "${WORKER1_NODE_NAME}"},
  "170": {"kubernetes.io/hostname": "${WORKER1_NODE_NAME}"},
  "151": {"kubernetes.io/hostname": "${WORKER2_NODE_NAME}"},
  "153": {"kubernetes.io/hostname": "${WORKER2_NODE_NAME}"},
  "161": {"kubernetes.io/hostname": "${WORKER2_NODE_NAME}"},
  "163": {"kubernetes.io/hostname": "${WORKER2_NODE_NAME}"},
  "171": {"kubernetes.io/hostname": "${WORKER2_NODE_NAME}"}
}
JSON
)"
}

run_preflight_check_once() {
  local virsh_ok ssh_ok sudo_ok nodes_ok multus_ok registry_ok registry_reachable_ok kubeconfig_ok
  virsh_ok="false"
  ssh_ok="false"
  sudo_ok="false"
  nodes_ok="false"
  multus_ok="false"
  registry_ok="false"
  registry_reachable_ok="false"
  kubeconfig_ok="false"

  # 1) virsh state
  if command -v virsh >/dev/null 2>&1; then
    if virsh domstate "${SEED_K3S_MASTER_NAME}" 2>/dev/null | grep -qi running \
      && virsh domstate "${SEED_K3S_WORKER1_NAME}" 2>/dev/null | grep -qi running \
      && virsh domstate "${SEED_K3S_WORKER2_NAME}" 2>/dev/null | grep -qi running; then
      virsh_ok="true"
    fi
  fi

  # 2) ssh + sudo
  if ssh "${SSH_OPTS[@]}" "${SEED_K3S_USER}@${SEED_K3S_MASTER_IP}" "echo ok" >/dev/null 2>&1 \
    && ssh "${SSH_OPTS[@]}" "${SEED_K3S_USER}@${SEED_K3S_WORKER1_IP}" "echo ok" >/dev/null 2>&1 \
    && ssh "${SSH_OPTS[@]}" "${SEED_K3S_USER}@${SEED_K3S_WORKER2_IP}" "echo ok" >/dev/null 2>&1; then
    ssh_ok="true"
  fi

  if ssh "${SSH_OPTS[@]}" "${SEED_K3S_USER}@${SEED_K3S_MASTER_IP}" "sudo -n true" >/dev/null 2>&1 \
    && ssh "${SSH_OPTS[@]}" "${SEED_K3S_USER}@${SEED_K3S_WORKER1_IP}" "sudo -n true" >/dev/null 2>&1 \
    && ssh "${SSH_OPTS[@]}" "${SEED_K3S_USER}@${SEED_K3S_WORKER2_IP}" "sudo -n true" >/dev/null 2>&1; then
    sudo_ok="true"
  fi

  # 3) kubeconfig
  if [ -f "${KUBECONFIG_PATH}" ] && kubectl --kubeconfig "${KUBECONFIG_PATH}" get nodes >/dev/null 2>&1; then
    kubeconfig_ok="true"
  fi

  # 4) k3s readiness
  if kubectl --kubeconfig "${KUBECONFIG_PATH}" wait --for=condition=Ready node --all --timeout=120s >/dev/null 2>&1; then
    nodes_ok="true"
  fi

  # 5) multus
  local desired ready
  desired="$(kubectl --kubeconfig "${KUBECONFIG_PATH}" -n kube-system get ds kube-multus-ds -o jsonpath='{.status.desiredNumberScheduled}' 2>/dev/null || echo 0)"
  ready="$(kubectl --kubeconfig "${KUBECONFIG_PATH}" -n kube-system get ds kube-multus-ds -o jsonpath='{.status.numberReady}' 2>/dev/null || echo -1)"
  if [ "${desired}" != "0" ] && [ "${desired}" = "${ready}" ]; then
    multus_ok="true"
  fi

  # 6) registry
  if ssh "${SSH_OPTS[@]}" "${SEED_K3S_USER}@${SEED_K3S_MASTER_IP}" "sudo docker ps --format '{{.Names}}' 2>/dev/null | grep -x registry" >/dev/null 2>&1; then
    registry_ok="true"
  fi

  if ssh "${SSH_OPTS[@]}" "${SEED_K3S_USER}@${SEED_K3S_WORKER1_IP}" "curl -m 5 -fsS http://${SEED_REGISTRY_HOST}:${SEED_REGISTRY_PORT}/v2/ >/dev/null" >/dev/null 2>&1 \
    && ssh "${SSH_OPTS[@]}" "${SEED_K3S_USER}@${SEED_K3S_WORKER2_IP}" "curl -m 5 -fsS http://${SEED_REGISTRY_HOST}:${SEED_REGISTRY_PORT}/v2/ >/dev/null" >/dev/null 2>&1; then
    registry_reachable_ok="true"
  fi

  # artifacts
  kubectl --kubeconfig "${KUBECONFIG_PATH}" get nodes -o wide > "${ARTIFACT_DIR}/kube_nodes.txt" 2>/dev/null || true
  kubectl --kubeconfig "${KUBECONFIG_PATH}" -n kube-system get ds kube-multus-ds -o wide > "${ARTIFACT_DIR}/multus_status.txt" 2>/dev/null || true

  python3 - <<PY
import json
from pathlib import Path

preflight = {
    "virsh_running": ${virsh_ok@Q} == "true",
    "ssh_ok": ${ssh_ok@Q} == "true",
    "sudo_nopasswd_ok": ${sudo_ok@Q} == "true",
    "kubeconfig_ok": ${kubeconfig_ok@Q} == "true",
    "k3s_nodes_ready": ${nodes_ok@Q} == "true",
    "multus_ready": ${multus_ok@Q} == "true",
    "registry_container_running": ${registry_ok@Q} == "true",
    "registry_reachable_from_workers": ${registry_reachable_ok@Q} == "true",
    "master_ip": ${SEED_K3S_MASTER_IP@Q},
    "worker1_ip": ${SEED_K3S_WORKER1_IP@Q},
    "worker2_ip": ${SEED_K3S_WORKER2_IP@Q},
    "repaired": ${PRECHECK_REPAIRED@Q} == "true"
}
Path(${ARTIFACT_DIR@Q}).mkdir(parents=True, exist_ok=True)
Path(${ARTIFACT_DIR@Q} + "/preflight.json").write_text(json.dumps(preflight, indent=2), encoding="utf-8")
PY

  if [ "${virsh_ok}" = "true" ] \
    && [ "${ssh_ok}" = "true" ] \
    && [ "${sudo_ok}" = "true" ] \
    && [ "${kubeconfig_ok}" = "true" ] \
    && [ "${nodes_ok}" = "true" ] \
    && [ "${multus_ok}" = "true" ] \
    && [ "${registry_ok}" = "true" ] \
    && [ "${registry_reachable_ok}" = "true" ]; then
    return 0
  fi

  return 1
}

repair_registry_connectivity() {
  log "Attempting quick registry remediation on master"
  ssh "${SSH_OPTS[@]}" "${SEED_K3S_USER}@${SEED_K3S_MASTER_IP}" \
    "sudo -n docker rm -f registry >/dev/null 2>&1 || true; sudo -n docker run -d --network host --restart=always --name registry registry:2 >/dev/null"

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

run_preflight() {
  CURRENT_STAGE="preflight"
  LAST_COMMAND="scripts/validate_k3s_mini_internet_multinode.sh preflight"
  ensure_kubeconfig

  if run_preflight_check_once; then
    log "Preflight passed"
    detect_cluster_nodes
    resolve_cni_master_interface
    resolve_scheduling_defaults
    set_effective_node_labels_json
    log "Placement mode=${SEED_PLACEMENT_MODE}, scheduling=${SEED_SCHEDULING_STRATEGY}"
    LAST_FAILURE_CODE=""
    record_stage_event "${CURRENT_STAGE}" "PASS" "${LAST_COMMAND}" "${ARTIFACT_DIR}/preflight.json" ""
    write_diagnostics_and_next_actions "${CURRENT_STAGE}" "PASS" "" "${LAST_FAILURE_CODE}"
    return
  fi

  log "Preflight failed; attempting quick registry remediation"
  PRECHECK_REPAIRED="true"
  FALLBACK_USED="registry_host_network_repair"

  if repair_registry_connectivity; then
    if run_preflight_check_once; then
      detect_cluster_nodes
      resolve_cni_master_interface
      resolve_scheduling_defaults
      set_effective_node_labels_json
      log "Placement mode=${SEED_PLACEMENT_MODE}, scheduling=${SEED_SCHEDULING_STRATEGY}"
      LAST_FAILURE_CODE=""
      record_stage_event "${CURRENT_STAGE}" "PASS" "${LAST_COMMAND}" "${ARTIFACT_DIR}/preflight.json" ""
      write_diagnostics_and_next_actions "${CURRENT_STAGE}" "PASS" "" "${LAST_FAILURE_CODE}"
      return
    fi
  fi

  log "Quick remediation did not recover preflight; running setup_k3s_cluster.sh"
  FALLBACK_USED="k3s_cluster_repair"

  (
    cd "${REPO_ROOT}"
    set -a
    source "${REPO_ROOT}/output/kvm_lab/k3s_vm_env.sh"
    set +a
    export SEED_ANSIBLE_TIMEOUT="${SEED_ANSIBLE_TIMEOUT:-600s}"
    ./scripts/setup_k3s_cluster.sh
  ) > "${ARTIFACT_DIR}/preflight_repair.log" 2>&1 || fail_with_reason "preflight_repair_failed"

  ensure_kubeconfig

  if ! run_preflight_check_once; then
    fail_with_reason "preflight_failed_after_repair"
  fi

  detect_cluster_nodes
  resolve_cni_master_interface
  resolve_scheduling_defaults
  set_effective_node_labels_json
  log "Placement mode=${SEED_PLACEMENT_MODE}, scheduling=${SEED_SCHEDULING_STRATEGY}"
  LAST_FAILURE_CODE=""
  record_stage_event "${CURRENT_STAGE}" "PASS" "${LAST_COMMAND}" "${ARTIFACT_DIR}/preflight.json" ""
  write_diagnostics_and_next_actions "${CURRENT_STAGE}" "PASS" "" "${LAST_FAILURE_CODE}"
}

run_compile() {
  CURRENT_STAGE="compile"
  LAST_COMMAND="python3 ${EXAMPLE_DIR}/k8s_mini_internet.py"
  log "Compiling mini-internet"
  rm -rf "${COMPILE_DIR}"
  mkdir -p "${COMPILE_DIR}"

  (
    cd "${EXAMPLE_DIR}"
    PYTHONPATH="${REPO_ROOT}" \
    SEED_NAMESPACE="${SEED_NAMESPACE}" \
    SEED_REGISTRY="${SEED_REGISTRY}" \
    SEED_CNI_TYPE="${SEED_CNI_TYPE}" \
    SEED_CNI_MASTER_INTERFACE="${EFFECTIVE_CNI_IFACE}" \
    SEED_SCHEDULING_STRATEGY="${SEED_SCHEDULING_STRATEGY}" \
    SEED_NODE_LABELS_JSON="${SEED_NODE_LABELS_JSON_EFFECTIVE}" \
    SEED_HOSTS_PER_AS="${SEED_HOSTS_PER_AS}" \
    SEED_OUTPUT_DIR="${COMPILE_DIR}" \
    python3 k8s_mini_internet.py
  ) 2>&1 | tee "${ARTIFACT_DIR}/compile.log"

  test -f "${COMPILE_DIR}/k8s.yaml" || fail_with_reason "compile_missing_k8s_yaml"
  test -x "${COMPILE_DIR}/build_images.sh" || fail_with_reason "compile_missing_build_script"

  cat > "${ARTIFACT_DIR}/placement_expected.json" <<JSON
${SEED_NODE_LABELS_JSON_EFFECTIVE}
JSON

  LAST_FAILURE_CODE=""
  record_stage_event "${CURRENT_STAGE}" "PASS" "${LAST_COMMAND}" "${ARTIFACT_DIR}/compile.log" ""
  write_diagnostics_and_next_actions "${CURRENT_STAGE}" "PASS" "" "${LAST_FAILURE_CODE}"
}

run_remote_build() {
  CURRENT_STAGE="build"
  LAST_COMMAND="scripts/validate_k3s_mini_internet_multinode.sh build"
  log "Building and pushing images on master (${SEED_K3S_MASTER_IP})"
  local tarball="${ARTIFACT_DIR}/compiled.tar.gz"

  if ! tar -C "${COMPILE_DIR}" -czf "${tarball}" .; then
    FAILURE_REASON="build_failed"
    return 1
  fi

  if ! ssh "${SSH_OPTS[@]}" "${SEED_K3S_USER}@${SEED_K3S_MASTER_IP}" \
    "rm -rf '${REMOTE_WORK_DIR}' && mkdir -p '${REMOTE_WORK_DIR}'"; then
    FAILURE_REASON="build_failed"
    return 1
  fi

  if ! scp -q "${SSH_OPTS[@]}" "${tarball}" "${SEED_K3S_USER}@${SEED_K3S_MASTER_IP}:${REMOTE_WORK_DIR}/compiled.tar.gz"; then
    FAILURE_REASON="build_failed"
    return 1
  fi

  if ! ssh "${SSH_OPTS[@]}" "${SEED_K3S_USER}@${SEED_K3S_MASTER_IP}" "sudo -n bash -lc '
    set -euo pipefail
    cd "${REMOTE_WORK_DIR}"
    tar -xzf compiled.tar.gz
    ./build_images.sh
  '" 2>&1 | tee "${ARTIFACT_DIR}/remote_build.log"; then
    FAILURE_REASON="build_failed"
    return 1
  fi

  LAST_FAILURE_CODE=""
  record_stage_event "${CURRENT_STAGE}" "PASS" "${LAST_COMMAND}" "${ARTIFACT_DIR}/remote_build.log" ""
  write_diagnostics_and_next_actions "${CURRENT_STAGE}" "PASS" "" "${LAST_FAILURE_CODE}"
}

run_deploy() {
  CURRENT_STAGE="deploy"
  LAST_COMMAND="kubectl -n ${SEED_NAMESPACE} apply -f ${COMPILE_DIR}/k8s.yaml"
  log "Deploying to namespace ${SEED_NAMESPACE}"

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
    kubectl -n "${SEED_NAMESPACE}" get deployment -o wide > "${ARTIFACT_DIR}/deployments_wide.txt" 2>/dev/null || true
    kubectl -n "${SEED_NAMESPACE}" get events --sort-by=.lastTimestamp > "${ARTIFACT_DIR}/events_tail.txt" 2>/dev/null || true
    FAILURE_REASON="deploy_wait_timeout_or_failure"
    record_stage_event "${CURRENT_STAGE}" "FAIL" "${LAST_COMMAND}" "${ARTIFACT_DIR}/wait.log" "${FAILURE_REASON}"
    return 1
  fi

  kubectl -n "${SEED_NAMESPACE}" get pods -o wide > "${ARTIFACT_DIR}/pods_wide.txt"
  kubectl -n "${SEED_NAMESPACE}" get deployment -o wide > "${ARTIFACT_DIR}/deployments_wide.txt"
  LAST_FAILURE_CODE=""
  record_stage_event "${CURRENT_STAGE}" "PASS" "${LAST_COMMAND}" "${ARTIFACT_DIR}/deployments_wide.txt" ""
  write_diagnostics_and_next_actions "${CURRENT_STAGE}" "PASS" "" "${LAST_FAILURE_CODE}"
}

run_verify_placement() {
  LAST_COMMAND="kubectl -n ${SEED_NAMESPACE} get pods -o jsonpath='{...placement...}'"
  log "Verifying placement mode=${SEED_PLACEMENT_MODE}"

  # `verify` can be called directly without `compile`.
  # Strict mode requires an explicit ASN->node expectation.
  if [ "${SEED_PLACEMENT_MODE}" = "strict3" ] && [ ! -f "${ARTIFACT_DIR}/placement_expected.json" ]; then
    cat > "${ARTIFACT_DIR}/placement_expected.json" <<JSON
${SEED_NODE_LABELS_JSON_EFFECTIVE}
JSON
  fi

  kubectl -n "${SEED_NAMESPACE}" get pods -o jsonpath='{range .items[*]}{.metadata.name}{"\t"}{.metadata.labels.seedemu\.io/asn}{"\t"}{.spec.nodeName}{"\n"}{end}' \
    > "${ARTIFACT_DIR}/placement_raw.tsv"

  if ! python3 - <<PY
import json
from pathlib import Path

mode = "${SEED_PLACEMENT_MODE}"
min_nodes = int("${SEED_MIN_NODES_USED}")
require_all_nodes = "${SEED_REQUIRE_ALL_NODES}".lower() == "true"
expected_path = Path("${ARTIFACT_DIR}/placement_expected.json")
expected = {}
if mode == "strict3":
    expected = json.loads(expected_path.read_text(encoding="utf-8")) if expected_path.exists() else {}

rows = []
by_asn = {}
unique_nodes = set()
errors = []

for line in Path("${ARTIFACT_DIR}/placement_raw.tsv").read_text(encoding="utf-8").splitlines():
    if not line.strip():
        continue
    pod, asn, node = line.split("\t")
    asn = str(asn)
    rows.append({"pod": pod, "asn": asn, "node": node})
    by_asn.setdefault(asn, set()).add(node)
    if node:
        unique_nodes.add(node)

if mode == "strict3":
    for asn, selector in expected.items():
        expected_node = selector.get("kubernetes.io/hostname", "")
        actual_nodes = sorted(by_asn.get(str(asn), set()))
        if not actual_nodes:
            errors.append(f"asn {asn} has no scheduled pod")
            continue
        if any(node != expected_node for node in actual_nodes):
            errors.append(f"asn {asn} expected {expected_node}, got {actual_nodes}")

ready_nodes = 0
kube_nodes = Path("${ARTIFACT_DIR}/kube_nodes.txt")
if kube_nodes.exists():
    for idx, line in enumerate(kube_nodes.read_text(encoding="utf-8").splitlines()):
        if idx == 0 and "STATUS" in line:
            continue
        cols = line.split()
        if len(cols) >= 2 and cols[1].startswith("Ready"):
            ready_nodes += 1

required_nodes = min_nodes
if require_all_nodes and ready_nodes > 0:
    required_nodes = ready_nodes

if mode == "strict3":
    placement_passed = (len(unique_nodes) == 3) and (len(errors) == 0)
    strict3_passed = placement_passed
else:
    if len(unique_nodes) < required_nodes:
        errors.append(
            f"auto placement needs >= {required_nodes} nodes, got {len(unique_nodes)}"
        )
    placement_passed = len(errors) == 0
    strict3_passed = len(unique_nodes) == 3

actual = {
    "pods": rows,
    "by_asn": {asn: sorted(nodes) for asn, nodes in sorted(by_asn.items())},
    "nodes_used": sorted(unique_nodes),
}
Path("${ARTIFACT_DIR}/placement_actual.json").write_text(json.dumps(actual, indent=2), encoding="utf-8")

check = {
    "placement_mode": mode,
    "placement_passed": placement_passed,
    "strict3_passed": strict3_passed,
    "required_nodes": required_nodes,
    "cluster_ready_nodes": ready_nodes,
    "nodes_used_count": len(unique_nodes),
    "nodes_used": sorted(unique_nodes),
    "errors": errors,
}
Path("${ARTIFACT_DIR}/placement_check.json").write_text(json.dumps(check, indent=2), encoding="utf-8")

if not placement_passed:
    raise SystemExit(1)
PY
  then
    FAILURE_REASON="placement_check_failed"
    return 1
  fi

  NODES_USED="$(python3 - <<PY
import json
from pathlib import Path
x = json.loads(Path("${ARTIFACT_DIR}/placement_check.json").read_text(encoding="utf-8"))
print(int(x.get("nodes_used_count", 0)))
PY
)"

  PLACEMENT_PASSED="$(python3 - <<PY
import json
from pathlib import Path
x = json.loads(Path("${ARTIFACT_DIR}/placement_check.json").read_text(encoding="utf-8"))
print("true" if x.get("placement_passed", False) else "false")
PY
)"

  STRICT3_PASSED="$(python3 - <<PY
import json
from pathlib import Path
x = json.loads(Path("${ARTIFACT_DIR}/placement_check.json").read_text(encoding="utf-8"))
print("true" if x.get("strict3_passed", False) else "false")
PY
)"
  return 0
}

run_verify_bgp() {
  LAST_COMMAND="kubectl -n ${SEED_NAMESPACE} exec <router151> -- birdc s p"
  log "Verifying BGP status"

  local router151 rs100
  router151="$(kubectl -n "${SEED_NAMESPACE}" get pods -l seedemu.io/name=router0,seedemu.io/asn=151 -o jsonpath='{.items[0].metadata.name}')"
  rs100="$(kubectl -n "${SEED_NAMESPACE}" get pods -l seedemu.io/name=ix100,seedemu.io/asn=100 -o jsonpath='{.items[0].metadata.name}')"

  local deadline now
  deadline="$(( $(date +%s) + BGP_WAIT_TIMEOUT_SECONDS ))"

  while true; do
    kubectl -n "${SEED_NAMESPACE}" exec "${router151}" -- birdc s p 2>/dev/null > "${ARTIFACT_DIR}/bird_router151.txt" || true
    kubectl -n "${SEED_NAMESPACE}" exec "${rs100}" -- birdc s p 2>/dev/null > "${ARTIFACT_DIR}/bird_ix100.txt" || true

    if grep -q 'Established' "${ARTIFACT_DIR}/bird_router151.txt" \
      && grep -Eq 'p_as2[[:space:]]+BGP.*Established' "${ARTIFACT_DIR}/bird_ix100.txt" \
      && grep -Eq 'p_as3[[:space:]]+BGP.*Established' "${ARTIFACT_DIR}/bird_ix100.txt" \
      && grep -Eq 'p_as4[[:space:]]+BGP.*Established' "${ARTIFACT_DIR}/bird_ix100.txt"; then
      BGP_PASSED="true"
      return 0
    fi

    now="$(date +%s)"
    if [ "${now}" -ge "${deadline}" ]; then
      FAILURE_REASON="bgp_not_established"
      return 1
    fi

    sleep 5
  done
}

run_verify_connectivity() {
  LAST_COMMAND="kubectl -n ${SEED_NAMESPACE} exec <host150> -- ping -c 3 -W 2 10.151.0.71"
  log "Verifying cross-AS connectivity"

  local host150 target_ip
  host150="$(kubectl -n "${SEED_NAMESPACE}" get pods -l seedemu.io/name=host_0,seedemu.io/asn=150 -o jsonpath='{.items[0].metadata.name}')"
  target_ip="10.151.0.71"

  : > "${ARTIFACT_DIR}/ping_150_to_151.txt"
  local attempt
  for ((attempt=1; attempt<=CONNECTIVITY_RETRY; attempt++)); do
    {
      echo "=== attempt ${attempt}/${CONNECTIVITY_RETRY} ==="
      kubectl -n "${SEED_NAMESPACE}" exec "${host150}" -- ping -c 3 -W 2 "${target_ip}"
    } >> "${ARTIFACT_DIR}/ping_150_to_151.txt" 2>&1 && {
      CONNECTIVITY_PASSED="true"
      return 0
    }
    sleep "${CONNECTIVITY_RETRY_INTERVAL_SECONDS}"
  done

  FAILURE_REASON="connectivity_check_failed"
  return 1
}

run_verify_recovery() {
  LAST_COMMAND="kubectl -n ${SEED_NAMESPACE} rollout status deployment/<host151-deployment> --timeout=600s"
  log "Verifying self-healing"

  local old_pod deployment new_pod start_ts end_ts recovery_seconds
  old_pod="$(kubectl -n "${SEED_NAMESPACE}" get pods -l seedemu.io/name=host_0,seedemu.io/asn=151 -o jsonpath='{.items[0].metadata.name}')"
  deployment="$(kubectl -n "${SEED_NAMESPACE}" get pod "${old_pod}" -o jsonpath='{.metadata.labels.app}')"

  start_ts="$(date +%s)"
  kubectl -n "${SEED_NAMESPACE}" delete pod "${old_pod}" >/dev/null
  if ! kubectl -n "${SEED_NAMESPACE}" rollout status deployment/"${deployment}" --timeout=600s >/dev/null; then
    FAILURE_REASON="recovery_check_failed"
    return 1
  fi
  end_ts="$(date +%s)"
  recovery_seconds="$((end_ts - start_ts))"

  new_pod="$(kubectl -n "${SEED_NAMESPACE}" get pods -l app="${deployment}" -o jsonpath='{.items[0].metadata.name}')"

  cat > "${ARTIFACT_DIR}/recovery_check.json" <<JSON
{
  "status": "recovered",
  "deployment": "${deployment}",
  "old_pod": "${old_pod}",
  "new_pod": "${new_pod}",
  "recovery_seconds": ${recovery_seconds}
}
JSON

  RECOVERY_PASSED="true"
  return 0
}

run_verify() {
  CURRENT_STAGE="verify"
  LAST_COMMAND="scripts/validate_k3s_mini_internet_multinode.sh verify"
  run_verify_placement || return 1
  run_verify_bgp || return 1
  run_verify_connectivity || return 1
  run_verify_recovery || return 1
  LAST_FAILURE_CODE=""
  record_stage_event "${CURRENT_STAGE}" "PASS" "${LAST_COMMAND}" "${ARTIFACT_DIR}/summary.json" ""
  write_diagnostics_and_next_actions "${CURRENT_STAGE}" "PASS" "" "${LAST_FAILURE_CODE}"
  return 0
}

run_clean() {
  CURRENT_STAGE="clean"
  LAST_COMMAND="kubectl delete namespace ${SEED_NAMESPACE} --ignore-not-found"
  log "Cleaning namespace ${SEED_NAMESPACE}"
  ensure_kubeconfig
  kubectl delete namespace "${SEED_NAMESPACE}" --ignore-not-found >/dev/null 2>&1 || true
  LAST_FAILURE_CODE=""
  record_stage_event "${CURRENT_STAGE}" "PASS" "${LAST_COMMAND}" "${ARTIFACT_DIR}/summary.json" ""
  write_diagnostics_and_next_actions "${CURRENT_STAGE}" "PASS" "" "${LAST_FAILURE_CODE}"
}

main_all() {
  CURRENT_STAGE="all"
  LAST_COMMAND="scripts/validate_k3s_mini_internet_multinode.sh all"
  run_preflight
  run_compile
  run_remote_build || fail_with_reason "${FAILURE_REASON:-build_failed}"
  run_deploy || fail_with_reason "${FAILURE_REASON:-deploy_failed}"
  if ! run_verify; then
    if [ "${SEED_CNI_TYPE}" = "macvlan" ] && [ "${SEED_AUTO_CNI_FALLBACK}" = "true" ]; then
      log "Verification failed with macvlan; retrying once with ipvlan fallback"
      FALLBACK_USED="cni_fallback_macvlan_to_ipvlan"
      SEED_CNI_TYPE="ipvlan"
      FAILURE_REASON=""
      PLACEMENT_PASSED="false"
      STRICT3_PASSED="false"
      BGP_PASSED="false"
      CONNECTIVITY_PASSED="false"
      RECOVERY_PASSED="false"
      NODES_USED="0"

      run_compile
      run_remote_build || fail_with_reason "${FAILURE_REASON:-build_failed_after_cni_fallback}"
      run_deploy || fail_with_reason "${FAILURE_REASON:-deploy_failed_after_cni_fallback}"
      if ! run_verify; then
        fail_with_reason "${FAILURE_REASON:-verification_failed_after_ipvlan_fallback}"
      fi
    else
      fail_with_reason "${FAILURE_REASON:-verification_failed}"
    fi
  fi
  LAST_FAILURE_CODE=""
  record_stage_event "${CURRENT_STAGE}" "PASS" "${LAST_COMMAND}" "${ARTIFACT_DIR}/summary.json" ""
  write_diagnostics_and_next_actions "${CURRENT_STAGE}" "PASS" "" "${LAST_FAILURE_CODE}"
  write_summary
  log "Validation succeeded. Artifacts: ${ARTIFACT_DIR}"
}

main() {
  ensure_dirs

  require_cmd python3
  require_cmd kubectl
  require_cmd ssh
  require_cmd scp
  require_cmd tar
  require_cmd awk

  CURRENT_STAGE="preflight"
  LAST_COMMAND="ssh -i ${SEED_K3S_SSH_KEY} ${SEED_K3S_USER}@${SEED_K3S_MASTER_IP}"
  if [ ! -f "${SEED_K3S_SSH_KEY}" ]; then
    fail_with_reason "ssh_key_not_found"
  fi

  case "${ACTION}" in
    all)
      main_all
      ;;
    preflight)
      run_preflight
      write_summary
      ;;
    compile)
      run_preflight
      run_compile
      write_summary
      ;;
    build)
      run_preflight
      run_remote_build || fail_with_reason "${FAILURE_REASON:-build_failed}"
      write_summary
      ;;
    deploy)
      run_preflight
      run_deploy || fail_with_reason "${FAILURE_REASON:-deploy_failed}"
      write_summary
      ;;
    verify)
      run_preflight
      run_verify || fail_with_reason "${FAILURE_REASON:-verify_failed}"
      write_summary
      ;;
    clean)
      run_clean
      write_summary
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
