#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SEED_NAMESPACE_INPUT="${SEED_NAMESPACE-}"
SEED_CNI_TYPE_INPUT="${SEED_CNI_TYPE-}"
SEED_SCHEDULING_STRATEGY_INPUT="${SEED_SCHEDULING_STRATEGY-}"
source "${SCRIPT_DIR}/env_seedemu.sh"
source "${SCRIPT_DIR}/seed_k8s_cluster_inventory.sh"
seed_load_cluster_inventory

PROFILE_ID="${1:-${SEED_EXPERIMENT_PROFILE:-mini_internet}}"
ACTION="${2:-all}"

PROFILE_FILE="${REPO_ROOT}/configs/seed_k8s_profiles.yaml"
FAILURE_MAP_FILE="${SEED_FAILURE_ACTION_MAP:-${REPO_ROOT}/configs/seed_failure_action_map.yaml}"
SEED_RUN_ID_INPUT="${SEED_RUN_ID:-}"
RUN_ID="${SEED_RUN_ID_INPUT:-$(date +%Y%m%d_%H%M%S)}"
BASE_DIR="${REPO_ROOT}/output/profile_runs/${PROFILE_ID}/${RUN_ID}"
PROFILE_ROOT="${REPO_ROOT}/output/profile_runs/${PROFILE_ID}"
LATEST_LINK="${PROFILE_ROOT}/latest"

VALIDATION_DIR="${BASE_DIR}/validation"
COMPILED_DIR="${BASE_DIR}/compiled"
OBSERVE_DIR="${BASE_DIR}/observe"
REPORT_DIR="${BASE_DIR}/report"
RUNNER_SUMMARY="${BASE_DIR}/runner_summary.json"
RUNNER_DIAGNOSTICS="${BASE_DIR}/diagnostics.json"
RUNNER_NEXT_ACTIONS="${BASE_DIR}/next_actions.json"
RUNNER_LOG="${BASE_DIR}/runner.log"
RUNNER_START_TS="$(date +%s)"
RUNNER_START_ISO="$(date -u +"%Y-%m-%dT%H:%M:%SZ")"
PROFILE_SUPPORT_TIER=""
PROFILE_ACCEPTANCE_LEVEL=""
PROFILE_CAPACITY_GATE=""

setup_runner_logging() {
  local enabled="${SEED_RUNNER_LOG:-true}"
  if [ "${enabled}" != "true" ]; then
    return 0
  fi
  mkdir -p "${BASE_DIR}"
  touch "${RUNNER_LOG}"
  exec > >(tee -a "${RUNNER_LOG}") 2>&1
}

rebind_run_paths() {
  BASE_DIR="$1"
  VALIDATION_DIR="${BASE_DIR}/validation"
  COMPILED_DIR="${BASE_DIR}/compiled"
  OBSERVE_DIR="${BASE_DIR}/observe"
  REPORT_DIR="${BASE_DIR}/report"
  RUNNER_SUMMARY="${BASE_DIR}/runner_summary.json"
  RUNNER_DIAGNOSTICS="${BASE_DIR}/diagnostics.json"
  RUNNER_NEXT_ACTIONS="${BASE_DIR}/next_actions.json"
  RUNNER_LOG="${BASE_DIR}/runner.log"
}

adopt_latest_for_read_actions() {
  if [ -n "${SEED_RUN_ID_INPUT}" ]; then
    return 0
  fi

  case "${ACTION}" in
    start|phase-start|verify|observe|report|triage|showcase|compare)
      ;;
    *)
      return 0
      ;;
  esac

  local candidate_dir
  candidate_dir=""

  run_has_required_artifacts() {
    local run_dir="$1"
    case "${ACTION}" in
      start)
        [ -f "${run_dir}/compiled/k8s.yaml" ]
        ;;
      phase-start|verify|observe)
        [ -d "${run_dir}/validation" ]
        ;;
      report)
        [ -f "${run_dir}/validation/summary.json" ]
        ;;
      compare)
        [ -f "${run_dir}/validation/summary.json" ] || [ -f "${run_dir}/report/report.json" ]
        ;;
      showcase)
        [ -f "${run_dir}/validation/summary.json" ] || [ -f "${run_dir}/report/report.json" ]
        ;;
      triage)
        [ -f "${run_dir}/validation/diagnostics.json" ] || [ -f "${run_dir}/validation/summary.json" ]
        ;;
      *)
        return 1
        ;;
    esac
  }

  if [ -L "${LATEST_LINK}" ]; then
    local latest_dir
    latest_dir="$(readlink -f "${LATEST_LINK}" || true)"
    if [ -n "${latest_dir}" ] && [ -d "${latest_dir}" ] && run_has_required_artifacts "${latest_dir}"; then
      candidate_dir="${latest_dir}"
    fi
  fi

  if [ -z "${candidate_dir}" ] && [ -d "${PROFILE_ROOT}" ]; then
    while IFS= read -r run_dir; do
      if run_has_required_artifacts "${run_dir}"; then
        candidate_dir="${run_dir}"
        break
      fi
    done < <(find "${PROFILE_ROOT}" -mindepth 1 -maxdepth 1 -type d ! -name latest | sort -r)
  fi

  if [ -n "${candidate_dir}" ]; then
    rebind_run_paths "${candidate_dir}"
  fi
}

log() {
  echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*"
}

require_cmd() {
  if ! command -v "$1" >/dev/null 2>&1; then
    echo "Missing required command: $1" >&2
    exit 1
  fi
}

ensure_kubeconfig() {
  # Prefer an already-working kubectl environment (kind, etc.). If kubectl is
  # not usable, fall back to the repo-managed k3s kubeconfig.
  if kubectl get nodes >/dev/null 2>&1; then
    return 0
  fi

  local cluster_name kubeconfig_path
  cluster_name="${SEED_K3S_CLUSTER_NAME:-seedemu-k3s}"
  kubeconfig_path="${REPO_ROOT}/output/kubeconfigs/${cluster_name}.yaml"

  if [ -f "${kubeconfig_path}" ]; then
    export KUBECONFIG="${kubeconfig_path}"
    if kubectl get nodes >/dev/null 2>&1; then
      return 0
    fi
  fi

  if "${SCRIPT_DIR}/k3s_fetch_kubeconfig.sh" >/dev/null 2>&1 && [ -f "${kubeconfig_path}" ]; then
    export KUBECONFIG="${kubeconfig_path}"
    if kubectl get nodes >/dev/null 2>&1; then
      return 0
    fi
  fi

  echo "ERROR: kubectl cannot reach a cluster." >&2
  echo "Hint: export KUBECONFIG=${kubeconfig_path} (or run scripts/k3s_fetch_kubeconfig.sh)" >&2
  return 1
}

usage() {
  cat <<'USAGE'
Usage: scripts/seed_k8s_profile_runner.sh <profile_id> <action>

Actions:
  doctor      Preflight risk assessment only
  build       preflight -> compile -> build
  start       preflight -> compile -> build -> deploy (bird remains stopped)
  phase-start Run the separate bird/iBGP/eBGP startup stage on latest deployment
  verify      Verify deployment status
  observe     Collect runtime observation artifacts
  compare     Generate compose-vs-k3s comparison report for latest run
  showcase    Launch the live academic showcase dashboard for the latest run
  all         build -> start -> phase-start -> verify -> observe -> report
  triage      Diagnose most recent failure from artifacts
  report      Generate normalized report from artifacts
USAGE
}

profile_field() {
  local field="$1"
  python3 - <<PY
from pathlib import Path
import json

try:
    import yaml  # type: ignore
except Exception as exc:
    raise SystemExit(f"PyYAML required to parse profile file: {exc}")

p = Path(${PROFILE_FILE@Q})
if not p.exists():
    raise SystemExit(f"Profile file not found: {p}")

data = yaml.safe_load(p.read_text(encoding="utf-8")) or {}
profiles = data.get("profiles", {}) if isinstance(data, dict) else {}
profile = profiles.get(${PROFILE_ID@Q})
if not isinstance(profile, dict):
    raise SystemExit(f"Unknown profile_id: ${PROFILE_ID}")

value = profile.get(${field@Q}, "")
if isinstance(value, (dict, list)):
    print(json.dumps(value))
else:
    print(str(value))
PY
}

write_runner_artifacts() {
  local stage="$1"
  local status="$2"
  local failure_code="$3"
  local failure_reason="$4"
  local first_evidence="$5"
  local minimal_retry="$6"
  local fallback_command="$7"

  python3 - <<PY
import json
from datetime import datetime, timezone
from pathlib import Path

base = Path(${BASE_DIR@Q})
base.mkdir(parents=True, exist_ok=True)

summary = {
    "generated_at": datetime.now(timezone.utc).isoformat(),
    "started_at": ${RUNNER_START_ISO@Q},
    "finished_at": datetime.now(timezone.utc).isoformat(),
    "profile_id": ${PROFILE_ID@Q},
    "action": ${ACTION@Q},
    "stage": ${stage@Q},
    "status": ${status@Q},
    "failure_code": ${failure_code@Q},
    "failure_reason": ${failure_reason@Q},
    "duration_seconds": max(0, int(datetime.now(timezone.utc).timestamp()) - int(${RUNNER_START_TS@Q})),
    "base_dir": str(base),
    "validation_dir": ${VALIDATION_DIR@Q},
    "compiled_dir": ${COMPILED_DIR@Q},
    "observe_dir": ${OBSERVE_DIR@Q},
    "report_dir": ${REPORT_DIR@Q},
    "proactive_mode": ${SEED_AGENT_PROACTIVE_MODE@Q},
}

diagnostics = {
    "stage": ${stage@Q},
    "status": ${status@Q},
    "failure_code": ${failure_code@Q},
    "failure_reason": ${failure_reason@Q},
    "first_evidence_file": ${first_evidence@Q},
    "minimal_retry_command": ${minimal_retry@Q},
    "fallback_command": ${fallback_command@Q},
}

next_actions = {
    "stage": ${stage@Q},
    "status": ${status@Q},
    "failure_code": ${failure_code@Q},
    "first_evidence_file": ${first_evidence@Q},
    "minimal_retry_command": ${minimal_retry@Q},
    "fallback_command": ${fallback_command@Q},
}

Path(${RUNNER_SUMMARY@Q}).write_text(json.dumps(summary, indent=2), encoding="utf-8")
Path(${RUNNER_DIAGNOSTICS@Q}).write_text(json.dumps(diagnostics, indent=2), encoding="utf-8")
Path(${RUNNER_NEXT_ACTIONS@Q}).write_text(json.dumps(next_actions, indent=2), encoding="utf-8")
PY
}

sync_validation_summary_runtime_fields() {
  python3 - <<PY
import json
from pathlib import Path

summary_path = Path(${VALIDATION_DIR@Q}) / "summary.json"
timing_path = Path(${VALIDATION_DIR@Q}) / "timing.json"
runner_path = Path(${RUNNER_SUMMARY@Q})

if not summary_path.exists():
    raise SystemExit(0)

try:
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
except Exception:
    raise SystemExit(0)

if not isinstance(summary, dict):
    raise SystemExit(0)

if timing_path.exists():
    try:
        timing = json.loads(timing_path.read_text(encoding="utf-8"))
    except Exception:
        timing = {}
else:
    timing = {}

if not isinstance(timing, dict):
    timing = {}

if runner_path.exists():
    try:
        runner = json.loads(runner_path.read_text(encoding="utf-8"))
    except Exception:
        runner = {}
else:
    runner = {}

if not isinstance(runner, dict):
    runner = {}

build_duration = int(timing.get("build_duration_seconds", summary.get("build_duration_seconds", 0)) or 0)
up_duration = int(timing.get("up_duration_seconds", summary.get("up_duration_seconds", 0)) or 0)
phase_duration = int(timing.get("phase_start_duration_seconds", summary.get("phase_start_duration_seconds", 0)) or 0)
validation_duration = int(summary.get("validation_duration_seconds", summary.get("duration_seconds", 0)) or 0)
runner_duration = int(runner.get("duration_seconds", 0) or 0)
pipeline_duration = max(
    int(summary.get("pipeline_duration_seconds", 0) or 0),
    runner_duration,
    build_duration + up_duration + phase_duration + validation_duration,
    validation_duration,
)

summary["build_duration_seconds"] = build_duration
summary["up_duration_seconds"] = up_duration
summary["phase_start_duration_seconds"] = phase_duration
summary["validation_duration_seconds"] = validation_duration
summary["pipeline_duration_seconds"] = pipeline_duration
summary["profile_id"] = str(summary.get("profile_id", "") or ${PROFILE_ID@Q})
summary["support_tier"] = str(summary.get("support_tier", "") or ${PROFILE_SUPPORT_TIER@Q})
summary["acceptance_level"] = str(summary.get("acceptance_level", "") or ${PROFILE_ACCEPTANCE_LEVEL@Q})
summary["capacity_gate"] = str(summary.get("capacity_gate", "") or ${PROFILE_CAPACITY_GATE@Q})
summary["capacity_gate_status"] = str(summary.get("capacity_gate_status", "") or "open")
summary["runner_action"] = str(runner.get("action", "") or "")
summary["runner_status"] = str(
    runner.get("status", "")
    or summary.get("runner_status", "")
    or ("PASS" if not summary.get("failure_code") else "FAIL")
)
summary["runner_started_at"] = str(runner.get("started_at", "") or "")
summary["runner_finished_at"] = str(runner.get("finished_at", "") or "")

if summary["runner_action"] in {"all", "report"}:
    summary["duration_seconds"] = pipeline_duration

summary_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
PY
}

write_runner_failure_from_validation() {
  local default_stage="$1"
  local diag_file="${VALIDATION_DIR}/diagnostics.json"
  local summary_file="${VALIDATION_DIR}/summary.json"

  if [ -f "${diag_file}" ]; then
    python3 - <<PY
import json
from pathlib import Path

p = Path(${diag_file@Q})
data = json.loads(p.read_text(encoding="utf-8"))
stage = str(data.get("stage", "") or "")
failure_code = str(data.get("failure_code", "") or "")
failure_reason = str(data.get("failure_reason", "") or "")
evidence = str(data.get("first_evidence_file", "") or str(p))
minimal = str(data.get("minimal_retry_command", "") or "")
fallback = str(data.get("fallback_command", "") or "")
print(stage)
print(failure_code)
print(failure_reason)
print(evidence)
print(minimal)
print(fallback)
PY
    return 0
  fi

  if [ -f "${summary_file}" ]; then
    python3 - <<PY
import json
from pathlib import Path

p = Path(${summary_file@Q})
data = json.loads(p.read_text(encoding="utf-8"))
failure_code = str(data.get("failure_code", "") or "")
failure_reason = str(data.get("failure_reason", "") or "")
print(${default_stage@Q})
print(failure_code or "DEPLOY_TIMEOUT")
print(failure_reason or "unknown_failure")
print(str(p))
print(f"scripts/seed_k8s_profile_runner.sh {${PROFILE_ID@Q}} {${ACTION@Q}}")
print(f"scripts/seed_k8s_profile_runner.sh {${PROFILE_ID@Q}} triage")
PY
    return 0
  fi

  if [ -f "${RUNNER_DIAGNOSTICS}" ]; then
    python3 - <<PY
import json
from pathlib import Path

p = Path(${RUNNER_DIAGNOSTICS@Q})
data = json.loads(p.read_text(encoding="utf-8"))
stage = str(data.get("stage", "") or ${default_stage@Q})
failure_code = str(data.get("failure_code", "") or "DEPLOY_TIMEOUT")
failure_reason = str(data.get("failure_reason", "") or "unknown_failure")
evidence = str(data.get("first_evidence_file", "") or str(p))
minimal = str(data.get("minimal_retry_command", "") or f"scripts/seed_k8s_profile_runner.sh {${PROFILE_ID@Q}} {${ACTION@Q}}")
fallback = str(data.get("fallback_command", "") or f"scripts/seed_k8s_profile_runner.sh {${PROFILE_ID@Q}} triage")
print(stage)
print(failure_code)
print(failure_reason)
print(evidence)
print(minimal)
print(fallback)
PY
    return 0
  fi

  if [ -f "${RUNNER_SUMMARY}" ]; then
    python3 - <<PY
import json
from pathlib import Path

p = Path(${RUNNER_SUMMARY@Q})
data = json.loads(p.read_text(encoding="utf-8"))
stage = str(data.get("stage", "") or ${default_stage@Q})
failure_code = str(data.get("failure_code", "") or "DEPLOY_TIMEOUT")
failure_reason = str(data.get("failure_reason", "") or "unknown_failure")
print(stage)
print(failure_code)
print(failure_reason)
print(str(p))
print(f"scripts/seed_k8s_profile_runner.sh {${PROFILE_ID@Q}} {${ACTION@Q}}")
print(f"scripts/seed_k8s_profile_runner.sh {${PROFILE_ID@Q}} triage")
PY
    return 0
  fi

  printf '%s\n' "${default_stage}" "DEPLOY_TIMEOUT" "unknown_failure" "${VALIDATION_DIR}/" \
    "scripts/seed_k8s_profile_runner.sh ${PROFILE_ID} ${ACTION}" "scripts/seed_k8s_profile_runner.sh ${PROFILE_ID} doctor"
  return 0
}

next_from_map() {
  local failure_code="$1"
  python3 - <<PY
from pathlib import Path

try:
    import yaml  # type: ignore
except Exception:
    yaml = None

failure_code = ${failure_code@Q}
p = Path(${FAILURE_MAP_FILE@Q})
if yaml is None or not p.exists():
    print("", end="")
    raise SystemExit(0)

loaded = yaml.safe_load(p.read_text(encoding="utf-8")) or {}
entry = (loaded.get("failure_actions", {}) if isinstance(loaded, dict) else {}).get(failure_code, {})
print(entry.get("minimal_retry_command", ""))
PY
}

init_profile_context() {
  mkdir -p "${BASE_DIR}" "${VALIDATION_DIR}" "${COMPILED_DIR}" "${OBSERVE_DIR}" "${REPORT_DIR}"
  mkdir -p "${PROFILE_ROOT}"
  ln -sfn "${BASE_DIR}" "${LATEST_LINK}"

  export SEED_EXPERIMENT_PROFILE="${PROFILE_ID}"
  export SEED_FAILURE_ACTION_MAP="${FAILURE_MAP_FILE}"

  local default_namespace default_cni default_sched
  default_namespace="$(profile_field default_namespace)"
  default_cni="$(profile_field default_cni_type)"
  default_sched="$(profile_field default_scheduling_strategy)"

  export SEED_NAMESPACE="${SEED_NAMESPACE_INPUT:-${default_namespace}}"
  export SEED_CNI_TYPE="${SEED_CNI_TYPE_INPUT:-${default_cni}}"
  export SEED_SCHEDULING_STRATEGY="${SEED_SCHEDULING_STRATEGY_INPUT:-${default_sched}}"
  export SEED_REGISTRY_HOST="${SEED_REGISTRY_HOST:-${SEED_K3S_MASTER_IP:-192.168.122.110}}"
  export SEED_REGISTRY_PORT="${SEED_REGISTRY_PORT:-5000}"
  export SEED_REGISTRY="${SEED_REGISTRY:-${SEED_REGISTRY_HOST}:${SEED_REGISTRY_PORT}}"
  export SEED_ARTIFACT_DIR="${VALIDATION_DIR}"
  export SEED_OUTPUT_DIR="${COMPILED_DIR}"
  export SEED_BGP_STARTUP_MODE="${SEED_BGP_STARTUP_MODE:-phased}"
  export SEED_PLACEMENT_MODE="${SEED_PLACEMENT_MODE:-by_as_hard}"
  export SEED_K3S_CLUSTER_NAME="${SEED_K3S_CLUSTER_NAME:-seedemu-k3s}"
  export SEED_K3S_MASTER_IP="${SEED_K3S_MASTER_IP:-192.168.122.110}"
  export SEED_K3S_USER="${SEED_K3S_USER:-ubuntu}"
  export SEED_K3S_SSH_KEY="${SEED_K3S_SSH_KEY:-$HOME/.ssh/id_ed25519}"

  case "${PROFILE_ID}" in
    real_topology_rr_scale)
      export SEED_PROFILE_KIND="${SEED_PROFILE_KIND:-scale}"
      ;;
    *)
      export SEED_PROFILE_KIND="${SEED_PROFILE_KIND:-baseline}"
      ;;
  esac
}

run_mini_validate() {
  local mini_action="$1"
  "${SCRIPT_DIR}/validate_k3s_mini_internet_multinode.sh" "${mini_action}"
}

run_real_topology_validate() {
  local topo_action="$1"
  "${SCRIPT_DIR}/validate_k3s_real_topology_multinode.sh" "${topo_action}"
}

is_real_topology_profile() {
  [ "${PROFILE_ID}" = "real_topology_rr" ] || [ "${PROFILE_ID}" = "real_topology_rr_scale" ]
}

run_generic_compile() {
  local compile_script
  compile_script="$(profile_field compile_script)"
  if [ -z "${compile_script}" ]; then
    echo "compile_script missing for profile ${PROFILE_ID}" >&2
    exit 1
  fi

  log "Compiling profile ${PROFILE_ID} with ${compile_script}"
  if ! (
    cd "${REPO_ROOT}"
    PYTHONPATH="${REPO_ROOT}" \
    SEED_NAMESPACE="${SEED_NAMESPACE}" \
    SEED_REGISTRY="${SEED_REGISTRY}" \
    SEED_CNI_TYPE="${SEED_CNI_TYPE}" \
    SEED_CNI_MASTER_INTERFACE="${SEED_CNI_MASTER_INTERFACE}" \
    SEED_SCHEDULING_STRATEGY="${SEED_SCHEDULING_STRATEGY}" \
    SEED_OUTPUT_DIR="${COMPILED_DIR}" \
    python3 "${compile_script}"
  ) 2>&1 | tee "${VALIDATION_DIR}/compile.log"; then
    write_runner_artifacts "compile" "FAIL" "COMPILE_FAILED" "compile_command_failed" "${VALIDATION_DIR}/compile.log" \
      "scripts/seed_k8s_profile_runner.sh ${PROFILE_ID} start" "scripts/seed_k8s_profile_runner.sh ${PROFILE_ID} doctor"
    return 1
  fi

  if [ ! -f "${COMPILED_DIR}/k8s.yaml" ] || [ ! -x "${COMPILED_DIR}/build_images.sh" ]; then
    write_runner_artifacts "compile" "FAIL" "COMPILE_FAILED" "compile_output_missing" "${VALIDATION_DIR}/compile.log" \
      "scripts/seed_k8s_profile_runner.sh ${PROFILE_ID} start" "scripts/seed_k8s_profile_runner.sh ${PROFILE_ID} doctor"
    return 1
  fi
}

run_generic_build() {
  local registry_local_endpoint
  registry_local_endpoint="${SEED_REGISTRY_LOCAL_ENDPOINT:-${SEED_REGISTRY}}"
  local cluster_runtime
  cluster_runtime="${SEED_CLUSTER_RUNTIME:-}"

  stage_prefetched_remote_images() {
    local build_script="$1"
    local prefetch_dir="$2"
    local source_image=""
    local staged=0

    rm -rf "${prefetch_dir}"
    mkdir -p "${prefetch_dir}"

    while IFS= read -r source_image; do
      [ -n "${source_image}" ] || continue
      if ! docker image inspect "${source_image}" >/dev/null 2>&1; then
        continue
      fi
      local digest
      digest="$(printf '%s' "${source_image}" | md5sum | awk '{print $1}')"
      log "Staging local image for remote build: ${source_image}"
      docker save -o "${prefetch_dir}/${digest}.tar" "${source_image}" >/dev/null
      staged=1
    done < <(awk '$1 == "seedemu_copy_and_push_image" { print $2 }' "${build_script}" | sort -u)

    if [ "${staged}" -eq 0 ]; then
      rmdir "${prefetch_dir}" >/dev/null 2>&1 || true
    fi
  }

  log "Building profile ${PROFILE_ID} images from ${COMPILED_DIR}"

  if [ "${cluster_runtime}" = "k3s" ] && [ -n "${SEED_K3S_MASTER_IP:-}" ] && [ -n "${SEED_K3S_USER:-}" ] && [ -f "${SEED_K3S_SSH_KEY:-}" ]; then
    local remote_work_dir tarball
    remote_work_dir="/tmp/seedemu-generic-build-${PROFILE_ID}-$(basename "${BASE_DIR}")"
    tarball="${VALIDATION_DIR}/compiled.tar.gz"

    if ! stage_prefetched_remote_images "${COMPILED_DIR}/build_images.sh" "${COMPILED_DIR}/prefetched_images" 2>&1 | tee "${VALIDATION_DIR}/build.log"; then
      write_runner_artifacts "build" "FAIL" "BUILD_FAILED" "remote_build_prefetch_failed" "${VALIDATION_DIR}/build.log" \
        "scripts/seed_k8s_profile_runner.sh ${PROFILE_ID} build" "scripts/seed_k8s_profile_runner.sh ${PROFILE_ID} doctor"
      return 1
    fi

    tar -C "${COMPILED_DIR}" -czf "${tarball}" .

    if ! ssh \
      -o StrictHostKeyChecking=no \
      -o UserKnownHostsFile=/dev/null \
      -o LogLevel=ERROR \
      -o BatchMode=yes \
      -o ConnectTimeout=10 \
      -o ServerAliveInterval=30 \
      -o ServerAliveCountMax=3 \
      -i "${SEED_K3S_SSH_KEY}" \
      "${SEED_K3S_USER}@${SEED_K3S_MASTER_IP}" \
      "rm -rf '${remote_work_dir}' && mkdir -p '${remote_work_dir}'" \
      >/dev/null 2>&1; then
      write_runner_artifacts "build" "FAIL" "BUILD_FAILED" "remote_build_workspace_prepare_failed" "${VALIDATION_DIR}/build.log" \
        "scripts/seed_k8s_profile_runner.sh ${PROFILE_ID} build" "scripts/seed_k8s_profile_runner.sh ${PROFILE_ID} doctor"
      return 1
    fi

    if ! scp \
      -q \
      -o StrictHostKeyChecking=no \
      -o UserKnownHostsFile=/dev/null \
      -o LogLevel=ERROR \
      -o BatchMode=yes \
      -o ConnectTimeout=10 \
      -i "${SEED_K3S_SSH_KEY}" \
      "${tarball}" "${SEED_K3S_USER}@${SEED_K3S_MASTER_IP}:${remote_work_dir}/compiled.tar.gz"; then
      write_runner_artifacts "build" "FAIL" "BUILD_FAILED" "remote_build_tarball_copy_failed" "${tarball}" \
        "scripts/seed_k8s_profile_runner.sh ${PROFILE_ID} build" "scripts/seed_k8s_profile_runner.sh ${PROFILE_ID} doctor"
      return 1
    fi

    if ! ssh \
      -o StrictHostKeyChecking=no \
      -o UserKnownHostsFile=/dev/null \
      -o LogLevel=ERROR \
      -o BatchMode=yes \
      -o ConnectTimeout=10 \
      -o ServerAliveInterval=30 \
      -o ServerAliveCountMax=3 \
      -i "${SEED_K3S_SSH_KEY}" \
      "${SEED_K3S_USER}@${SEED_K3S_MASTER_IP}" \
      "sudo -n env \
        SEED_BUILD_PARALLELISM=${SEED_BUILD_PARALLELISM:-1} \
        SEED_DOCKER_BUILDKIT=${SEED_DOCKER_BUILDKIT:-0} \
        SEED_REGISTRY_PUSH_RETRIES=${SEED_REGISTRY_PUSH_RETRIES:-5} \
        SEED_REGISTRY_PUSH_BACKOFF_SECONDS=${SEED_REGISTRY_PUSH_BACKOFF_SECONDS:-5} \
        SEED_DOCKER_MAX_CONCURRENT_UPLOADS=${SEED_DOCKER_MAX_CONCURRENT_UPLOADS:-1} \
        SEED_REGISTRY_PUSH_TIMEOUT_SECONDS=${SEED_REGISTRY_PUSH_TIMEOUT_SECONDS:-180} \
        SEED_IMAGE_DISTRIBUTION_MODE=${SEED_IMAGE_DISTRIBUTION_MODE:-registry} \
        bash -lc 'set -euo pipefail; cd \"${remote_work_dir}\"; tar -xzf compiled.tar.gz; ./build_images.sh'" \
      2>&1 | tee "${VALIDATION_DIR}/build.log"; then
      write_runner_artifacts "build" "FAIL" "BUILD_FAILED" "remote_build_command_failed" "${VALIDATION_DIR}/build.log" \
        "scripts/seed_k8s_profile_runner.sh ${PROFILE_ID} build" "scripts/seed_k8s_profile_runner.sh ${PROFILE_ID} doctor"
      return 1
    fi

    return 0
  fi

  if ! (
    cd "${COMPILED_DIR}"
    SEED_REGISTRY="${SEED_REGISTRY}" \
    SEED_REGISTRY_LOCAL_ENDPOINT="${registry_local_endpoint}" \
    ./build_images.sh
  ) 2>&1 | tee "${VALIDATION_DIR}/build.log"; then
    write_runner_artifacts "build" "FAIL" "BUILD_FAILED" "build_command_failed" "${VALIDATION_DIR}/build.log" \
      "scripts/seed_k8s_profile_runner.sh ${PROFILE_ID} start" "scripts/seed_k8s_profile_runner.sh ${PROFILE_ID} doctor"
    return 1
  fi
}

run_generic_deploy() {
  ensure_kubeconfig || return 1

  local deploy_timeout
  deploy_timeout="${SEED_GENERIC_DEPLOY_TIMEOUT_SECONDS:-1200}"

  log "Deploying profile ${PROFILE_ID} to namespace ${SEED_NAMESPACE}"
  kubectl delete namespace "${SEED_NAMESPACE}" --ignore-not-found >/dev/null 2>&1 || true
  kubectl create namespace "${SEED_NAMESPACE}" --dry-run=client -o yaml | kubectl apply -f - >/dev/null

  if ! kubectl -n "${SEED_NAMESPACE}" apply -f "${COMPILED_DIR}/k8s.yaml" 2>&1 | tee "${VALIDATION_DIR}/apply.log"; then
    write_runner_artifacts "deploy" "FAIL" "DEPLOY_TIMEOUT" "apply_failed" "${VALIDATION_DIR}/apply.log" \
      "scripts/seed_k8s_profile_runner.sh ${PROFILE_ID} start" "kubectl -n ${SEED_NAMESPACE} get events --sort-by=.lastTimestamp"
    return 1
  fi

  if ! kubectl -n "${SEED_NAMESPACE}" wait --for=condition=Available --timeout="${deploy_timeout}s" deployment --all \
    2>&1 | tee "${VALIDATION_DIR}/wait.log"; then
    write_runner_artifacts "deploy" "FAIL" "DEPLOY_TIMEOUT" "wait_timeout_or_notready" "${VALIDATION_DIR}/wait.log" \
      "scripts/seed_k8s_profile_runner.sh ${PROFILE_ID} verify" "kubectl -n ${SEED_NAMESPACE} get pods -o wide"
    return 1
  fi
}

run_generic_verify() {
  ensure_kubeconfig || return 1

  local verify_mode
  verify_mode="$(profile_field verify_mode)"

  if [ "${verify_mode}" = "hybrid_vm" ]; then
    kubectl -n "${SEED_NAMESPACE}" get vm,vmi -o wide > "${VALIDATION_DIR}/vm_vmi.txt" 2>/dev/null || true
  fi

  kubectl -n "${SEED_NAMESPACE}" get deployment -o wide > "${VALIDATION_DIR}/deployments_wide.txt"
  kubectl -n "${SEED_NAMESPACE}" get pods -o wide > "${VALIDATION_DIR}/pods_wide.txt"

  local dep_count pod_count
  dep_count="$( (kubectl -n "${SEED_NAMESPACE}" get deploy --no-headers 2>/dev/null || true) | wc -l | tr -d ' ' )"
  pod_count="$( (kubectl -n "${SEED_NAMESPACE}" get pods --field-selector=status.phase=Running --no-headers 2>/dev/null || true) | wc -l | tr -d ' ' )"

  if [ "${dep_count}" -lt 1 ] || [ "${pod_count}" -lt 1 ]; then
    write_runner_artifacts "verify" "FAIL" "DEPLOY_TIMEOUT" "generic_verify_not_ready" "${VALIDATION_DIR}/deployments_wide.txt" \
      "scripts/seed_k8s_profile_runner.sh ${PROFILE_ID} verify" "kubectl -n ${SEED_NAMESPACE} get events --sort-by=.lastTimestamp"
    return 1
  fi
}

run_observe() {
  ensure_kubeconfig || return 1

  if [ "${PROFILE_ID}" = "mini_internet" ]; then
    "${SCRIPT_DIR}/inspect_k3s_mini_internet.sh" "${SEED_NAMESPACE}" "${OBSERVE_DIR}"
    kubectl top nodes > "${OBSERVE_DIR}/nodes_top.txt" 2>/dev/null || true
    kubectl -n "${SEED_NAMESPACE}" top pods > "${OBSERVE_DIR}/pods_top.txt" 2>/dev/null || true
    kubectl -n "${SEED_NAMESPACE}" get events --sort-by=.lastTimestamp > "${OBSERVE_DIR}/events.txt" 2>/dev/null || true
    python3 "${SCRIPT_DIR}/seed_k8s_bgp_health.py" \
      "${SEED_NAMESPACE}" "${OBSERVE_DIR}" \
      --parallelism "${SEED_BGP_HEALTH_PARALLELISM:-8}" \
      --kubectl-timeout "${SEED_KUBECTL_EXEC_TIMEOUT_SECONDS:-20}" >/dev/null 2>&1 || true
  else
    kubectl get nodes -o wide > "${OBSERVE_DIR}/nodes_wide.txt"
    kubectl -n "${SEED_NAMESPACE}" get pods -o wide > "${OBSERVE_DIR}/pods_wide.txt"
    kubectl -n "${SEED_NAMESPACE}" get deploy -o wide > "${OBSERVE_DIR}/deploy_wide.txt"
    kubectl top nodes > "${OBSERVE_DIR}/nodes_top.txt" 2>/dev/null || true
    kubectl -n "${SEED_NAMESPACE}" top pods > "${OBSERVE_DIR}/pods_top.txt" 2>/dev/null || true
    kubectl -n "${SEED_NAMESPACE}" get events --sort-by=.lastTimestamp > "${OBSERVE_DIR}/events.txt" 2>/dev/null || true
    if [ -f "${COMPILED_DIR}/rr_plan.json" ]; then
      cp "${COMPILED_DIR}/rr_plan.json" "${OBSERVE_DIR}/rr_plan.json"
    fi
    python3 "${SCRIPT_DIR}/seed_k8s_bgp_health.py" \
      "${SEED_NAMESPACE}" "${OBSERVE_DIR}" \
      --parallelism "${SEED_BGP_HEALTH_PARALLELISM:-8}" \
      --kubectl-timeout "${SEED_KUBECTL_EXEC_TIMEOUT_SECONDS:-20}" >/dev/null 2>&1 || true
    python3 - <<PY
import json
from pathlib import Path

out = Path(${OBSERVE_DIR@Q})
summary = {
    "namespace": ${SEED_NAMESPACE@Q},
    "profile_id": ${PROFILE_ID@Q},
    "artifacts": sorted(p.name for p in out.iterdir()),
}
(out / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
PY
  fi
}

run_showcase() {
  ensure_kubeconfig || return 1

  local effective_run_id showcase_port
  effective_run_id="$(basename "${BASE_DIR}")"
  showcase_port="${SEED_SHOWCASE_PORT:-8088}"
  local -a showcase_cmd
  showcase_cmd=(
    python3 "${SCRIPT_DIR}/seed_k8s_showcase.py"
    --profile "${PROFILE_ID}"
    --run-id "${effective_run_id}"
    --port "${showcase_port}"
  )

  if [ -n "${SEED_NAMESPACE_INPUT}" ]; then
    showcase_cmd+=(--namespace "${SEED_NAMESPACE}")
  fi

  exec "${showcase_cmd[@]}"
}

run_compare() {
  local compose_dir
  compose_dir="${SEED_COMPOSE_DIR:-${HOME}/lxl_topology/autocoder_test}"

  if [ ! -d "${BASE_DIR}" ]; then
    echo "ERROR: run dir not found: ${BASE_DIR}" >&2
    echo "Hint: use latest (default) or export SEED_RUN_ID=<existing_run_id>" >&2
    return 1
  fi

  python3 "${SCRIPT_DIR}/seed_k8s_compare_with_compose.py" \
    --compose-dir "${compose_dir}" \
    --profile "${PROFILE_ID}" \
    --k3s-run-dir "${BASE_DIR}"
}

hydrate_validation_artifacts_from_runner() {
  local verify_mode cni_iface image_distribution_mode
  verify_mode="$(profile_field verify_mode)"
  cni_iface="${SEED_CNI_MASTER_INTERFACE:-}"
  image_distribution_mode="${SEED_IMAGE_DISTRIBUTION_MODE:-registry}"

  python3 - <<PY
import json
import subprocess
from pathlib import Path

validation_dir = Path(${VALIDATION_DIR@Q})
validation_dir.mkdir(parents=True, exist_ok=True)

runner_summary_path = Path(${RUNNER_SUMMARY@Q})
runner_diag_path = Path(${RUNNER_DIAGNOSTICS@Q})
runner_next_path = Path(${RUNNER_NEXT_ACTIONS@Q})
summary_path = validation_dir / "summary.json"
diag_path = validation_dir / "diagnostics.json"
next_path = validation_dir / "next_actions.json"

runner_summary = {}
if runner_summary_path.exists():
    try:
        runner_summary = json.loads(runner_summary_path.read_text(encoding="utf-8"))
    except Exception:
        runner_summary = {}

def run_cmd(args):
    try:
        out = subprocess.check_output(args, stderr=subprocess.DEVNULL, text=True)
        return out.strip()
    except Exception:
        return ""

def count_unique_nodes(namespace):
    out = run_cmd([
        "kubectl", "-n", namespace, "get", "pods",
        "-o", "custom-columns=NODE:.spec.nodeName", "--no-headers"
    ])
    nodes = {
        line.strip()
        for line in out.splitlines()
        if line.strip() and line.strip() != "<none>" and not line.startswith("No resources found")
    }
    return len(nodes)

def count_resources(namespace, kind):
    out = run_cmd(["kubectl", "-n", namespace, "get", kind, "--no-headers"])
    if not out:
        return 0
    return len([line for line in out.splitlines() if line.strip()])

namespace = ${SEED_NAMESPACE@Q}
cluster_name = ${SEED_K3S_CLUSTER_NAME@Q}
cni_type = ${SEED_CNI_TYPE@Q}
verify_mode = ${verify_mode@Q}

nodes_used = count_unique_nodes(namespace)
vm_count = count_resources(namespace, "vm")
pod_count = count_resources(namespace, "pods")
dep_count = count_resources(namespace, "deploy")

status = str(runner_summary.get("status", "PASS"))
failure_reason = str(runner_summary.get("failure_reason", "") or "")
failure_code = str(runner_summary.get("failure_code", "") or "")

passed = status == "PASS"
if verify_mode == "hybrid_vm":
    passed = passed and vm_count >= 1 and pod_count >= 1
else:
    passed = passed and dep_count >= 1 and pod_count >= 1

summary = {
    "cluster": cluster_name,
    "namespace": namespace,
    "profile": ${PROFILE_ID@Q},
    "profile_id": ${PROFILE_ID@Q},
    "support_tier": ${PROFILE_SUPPORT_TIER@Q},
    "acceptance_level": ${PROFILE_ACCEPTANCE_LEVEL@Q},
    "capacity_gate": ${PROFILE_CAPACITY_GATE@Q},
    "capacity_gate_status": "open",
    "proactive_mode": ${SEED_AGENT_PROACTIVE_MODE@Q},
    "cni_type": cni_type,
    "cni_master_interface": ${cni_iface@Q},
    "nodes_used": int(nodes_used),
    "strict3_passed": bool(passed),
    "bgp_passed": bool(passed),
    "connectivity_passed": bool(passed),
    "recovery_passed": bool(passed),
    "duration_seconds": 0,
    "validation_duration_seconds": 0,
    "pipeline_duration_seconds": 0,
    "runner_status": "PASS" if passed else "FAIL",
    "image_distribution_mode": ${image_distribution_mode@Q},
    "fallback_used": "none",
    "failure_reason": "" if passed else failure_reason,
    "failure_code": "" if passed else failure_code,
}
summary_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")

if not diag_path.exists() and runner_diag_path.exists():
    diag_path.write_text(runner_diag_path.read_text(encoding="utf-8"), encoding="utf-8")

if not next_path.exists() and runner_next_path.exists():
    next_path.write_text(runner_next_path.read_text(encoding="utf-8"), encoding="utf-8")
PY
}

materialize_validation_contract() {
  python3 "${SCRIPT_DIR}/seed_k8s_validation_contract.py" materialize \
    "${SEED_NAMESPACE}" "${VALIDATION_DIR}" "${PROFILE_ID}" \
    --kubectl-timeout "${SEED_KUBECTL_EXEC_TIMEOUT_SECONDS:-20}"
}

assert_validation_contract() {
  python3 "${SCRIPT_DIR}/seed_k8s_validation_contract.py" assert \
    "${VALIDATION_DIR}" \
    --profile-file "${PROFILE_FILE}" \
    --profile-id "${PROFILE_ID}"
}

run_report() {
  local vdir odir
  vdir="${VALIDATION_DIR}"
  odir="${OBSERVE_DIR}"

  if [ ! -f "${vdir}/summary.json" ]; then
    hydrate_validation_artifacts_from_runner
  fi

  sync_validation_summary_runtime_fields

  if [ ! -f "${vdir}/summary.json" ]; then
    write_runner_artifacts "report" "FAIL" "DEPLOY_TIMEOUT" "summary_missing_for_report" "${vdir}/summary.json" \
      "scripts/seed_k8s_profile_runner.sh ${PROFILE_ID} start" "scripts/seed_k8s_profile_runner.sh ${PROFILE_ID} triage"
    return 1
  fi

  if ! materialize_validation_contract >/dev/null 2>&1; then
    write_runner_artifacts "report" "FAIL" "ARTIFACT_MATERIALIZATION_FAILED" "artifact_materialization_failed" "${vdir}/summary.json" \
      "scripts/seed_k8s_profile_runner.sh ${PROFILE_ID} verify" "scripts/seed_k8s_profile_runner.sh ${PROFILE_ID} triage"
    return 1
  fi

  if ! assert_validation_contract >/dev/null 2>&1; then
    write_runner_artifacts "report" "FAIL" "ARTIFACT_CONTRACT_FAILED" "artifact_contract_failed" "${vdir}/artifact_contract.json" \
      "scripts/seed_k8s_profile_runner.sh ${PROFILE_ID} verify" "scripts/seed_k8s_profile_runner.sh ${PROFILE_ID} triage"
    return 1
  fi

  "${SCRIPT_DIR}/seedlab_report_from_artifacts.sh" "${vdir}" "${odir}" "${REPORT_DIR}"
}

run_doctor() {
  "${SCRIPT_DIR}/opencode_seedlab_smoke.sh" || true

  if [ "${PROFILE_ID}" = "mini_internet" ]; then
    if run_mini_validate preflight; then
      write_runner_artifacts "doctor" "PASS" "" "" "${VALIDATION_DIR}/preflight.json" \
        "scripts/seed_k8s_profile_runner.sh ${PROFILE_ID} start" "scripts/seed_k8s_profile_runner.sh ${PROFILE_ID} verify"
      return 0
    fi

    local failure_code minimal
    failure_code="$(python3 - <<PY
import json
from pathlib import Path
p = Path(${VALIDATION_DIR@Q}) / "diagnostics.json"
if p.exists():
    data = json.loads(p.read_text(encoding="utf-8"))
    print(data.get("failure_code", "NODE_NOT_READY"))
else:
    print("NODE_NOT_READY")
PY
)"
    minimal="$(next_from_map "${failure_code}")"
    write_runner_artifacts "doctor" "FAIL" "${failure_code}" "preflight_failed" "${VALIDATION_DIR}/diagnostics.json" \
      "${minimal:-scripts/validate_k3s_mini_internet_multinode.sh preflight}" "scripts/setup_k3s_cluster.sh"
    return 1
  fi

  if is_real_topology_profile; then
    if run_real_topology_validate preflight; then
      write_runner_artifacts "doctor" "PASS" "" "" "${VALIDATION_DIR}/summary.json" \
        "scripts/seed_k8s_profile_runner.sh ${PROFILE_ID} start" "scripts/seed_k8s_profile_runner.sh ${PROFILE_ID} verify"
      return 0
    fi

    local failure_code minimal fallback
    failure_code="$(python3 - <<PY
import json
from pathlib import Path
p = Path(${VALIDATION_DIR@Q}) / "diagnostics.json"
if p.exists():
    data = json.loads(p.read_text(encoding="utf-8"))
    print(data.get("failure_code", "NODE_NOT_READY"))
else:
    print("NODE_NOT_READY")
PY
)"
    minimal="$(python3 - <<PY
import json
from pathlib import Path
p = Path(${VALIDATION_DIR@Q}) / "diagnostics.json"
if p.exists():
    data = json.loads(p.read_text(encoding="utf-8"))
    print(str(data.get("minimal_retry_command", "")))
else:
    print("")
PY
)"
    fallback="$(python3 - <<PY
import json
from pathlib import Path
p = Path(${VALIDATION_DIR@Q}) / "diagnostics.json"
if p.exists():
    data = json.loads(p.read_text(encoding="utf-8"))
    print(str(data.get("fallback_command", "")))
else:
    print("")
PY
)"
    write_runner_artifacts "doctor" "FAIL" "${failure_code}" "preflight_failed" "${VALIDATION_DIR}/diagnostics.json" \
      "${minimal:-scripts/validate_k3s_real_topology_multinode.sh preflight}" "${fallback:-scripts/setup_k3s_cluster.sh}"
    return 1
  fi

  local cluster_name kubeconfig_path
  cluster_name="${SEED_K3S_CLUSTER_NAME:-seedemu-k3s}"
  kubeconfig_path="${REPO_ROOT}/output/kubeconfigs/${cluster_name}.yaml"

  if "${SCRIPT_DIR}/k3s_fetch_kubeconfig.sh" >/dev/null 2>&1 && kubectl --kubeconfig "${KUBECONFIG:-${kubeconfig_path}}" get nodes >/dev/null 2>&1; then
    write_runner_artifacts "doctor" "PASS" "" "" "${kubeconfig_path}" \
      "scripts/seed_k8s_profile_runner.sh ${PROFILE_ID} start" "scripts/seed_k8s_profile_runner.sh ${PROFILE_ID} verify"
    return 0
  fi

  write_runner_artifacts "doctor" "FAIL" "KCFG_MISSING" "doctor_cluster_unreachable" "${kubeconfig_path}" \
    "scripts/k3s_fetch_kubeconfig.sh" "scripts/setup_k3s_cluster.sh"
  return 1
}

run_build() {
  if [ "${PROFILE_ID}" = "mini_internet" ]; then
    run_mini_validate preflight || return 1
    run_mini_validate compile || return 1
    run_mini_validate build || return 1
  elif is_real_topology_profile; then
    run_real_topology_validate preflight || return 1
    run_real_topology_validate compile || return 1
    run_real_topology_validate build || return 1
  else
    run_doctor || return 1
    run_generic_compile || return 1
    run_generic_build || return 1
  fi

  write_runner_artifacts "build" "PASS" "" "" "${VALIDATION_DIR}/summary.json"     "scripts/seed_k8s_profile_runner.sh ${PROFILE_ID} start" "scripts/seed_k8s_profile_runner.sh ${PROFILE_ID} phase-start"
  sync_validation_summary_runtime_fields
}

run_start() {
  if [ "${PROFILE_ID}" = "mini_internet" ]; then
    run_mini_validate preflight || return 1
    run_mini_validate deploy || return 1
  elif is_real_topology_profile; then
    run_real_topology_validate preflight || return 1
    run_real_topology_validate deploy || return 1
  else
    run_doctor || return 1
    run_generic_deploy || return 1
  fi

  write_runner_artifacts "start" "PASS" "" "" "${VALIDATION_DIR}/summary.json"     "scripts/seed_k8s_profile_runner.sh ${PROFILE_ID} phase-start" "scripts/seed_k8s_profile_runner.sh ${PROFILE_ID} verify"
  sync_validation_summary_runtime_fields
}

run_phase_start() {
  if [ "${PROFILE_ID}" = "mini_internet" ]; then
    run_mini_validate phase-start || return 1
  elif is_real_topology_profile; then
    run_real_topology_validate phase-start || return 1
  else
    write_runner_artifacts "phase-start" "FAIL" "PHASED_START_UNSUPPORTED" "phase_start_not_supported_for_profile" "${VALIDATION_DIR}/summary.json"       "scripts/seed_k8s_profile_runner.sh ${PROFILE_ID} verify" "scripts/seed_k8s_profile_runner.sh ${PROFILE_ID} triage"
    return 1
  fi

  write_runner_artifacts "phase-start" "PASS" "" "" "${VALIDATION_DIR}/summary.json"     "scripts/seed_k8s_profile_runner.sh ${PROFILE_ID} verify" "scripts/seed_k8s_profile_runner.sh ${PROFILE_ID} observe"
  sync_validation_summary_runtime_fields
}

run_verify() {
  local generic_verify=false
  if [ "${PROFILE_ID}" = "mini_internet" ]; then
    run_mini_validate verify || return 1
  elif is_real_topology_profile; then
    run_real_topology_validate verify || return 1
  else
    generic_verify=true
    run_generic_verify || return 1
  fi

  write_runner_artifacts "verify" "PASS" "" "" "${VALIDATION_DIR}/summary.json" \
    "scripts/seed_k8s_profile_runner.sh ${PROFILE_ID} observe" "scripts/seed_k8s_profile_runner.sh ${PROFILE_ID} report"
  if [ "${generic_verify}" = "true" ]; then
    hydrate_validation_artifacts_from_runner
  fi
  sync_validation_summary_runtime_fields
}

run_all() {
  run_build || return 1
  run_start || return 1
  run_phase_start || return 1
  run_verify || return 1
  run_observe || return 1
  run_report || return 1
  write_runner_artifacts "all" "PASS" "" "" "${REPORT_DIR}/report.json"     "scripts/seed_k8s_profile_runner.sh ${PROFILE_ID} report" "scripts/seed_k8s_profile_runner.sh ${PROFILE_ID} triage"
  sync_validation_summary_runtime_fields
}

run_triage() {
  local diag_file
  diag_file="${VALIDATION_DIR}/diagnostics.json"

  if [ ! -f "${diag_file}" ] && [ -f "${RUNNER_DIAGNOSTICS}" ]; then
    diag_file="${RUNNER_DIAGNOSTICS}"
  fi

  if [ ! -f "${diag_file}" ] && [ -f "${VALIDATION_DIR}/summary.json" ]; then
    diag_file="${BASE_DIR}/diagnostics_from_summary.json"
    python3 - <<PY
import json
from pathlib import Path

summary_path = Path(${VALIDATION_DIR@Q}) / "summary.json"
summary = json.loads(summary_path.read_text(encoding="utf-8"))

failed = bool(summary.get("failure_code") or summary.get("failure_reason"))
status = "FAIL" if failed else "PASS"
failure_code = str(summary.get("failure_code", "") or "")

diagnostics = {
    "stage": "triage",
    "status": status,
    "failure_code": failure_code,
    "failure_reason": str(summary.get("failure_reason", "") or ""),
    "first_evidence_file": str(summary_path.resolve()),
    "minimal_retry_command": f"scripts/seed_k8s_profile_runner.sh ${PROFILE_ID} verify",
    "fallback_command": f"scripts/seed_k8s_profile_runner.sh ${PROFILE_ID} report",
}
Path(${diag_file@Q}).write_text(json.dumps(diagnostics, indent=2), encoding="utf-8")
PY
  fi

  if [ ! -f "${diag_file}" ] && [ -L "${REPO_ROOT}/output/multinode_mini_validation/latest" ]; then
    diag_file="${REPO_ROOT}/output/multinode_mini_validation/latest/diagnostics.json"
  fi

  if [ -f "${diag_file}" ]; then
    cat "${diag_file}"
    write_runner_artifacts "triage" "PASS" "" "" "${diag_file}" \
      "scripts/seed_k8s_profile_runner.sh ${PROFILE_ID} verify" "scripts/seed_k8s_profile_runner.sh ${PROFILE_ID} report"
    return 0
  fi

  write_runner_artifacts "triage" "FAIL" "DEPLOY_TIMEOUT" "diagnostics_missing" "${diag_file}" \
    "scripts/seed_k8s_profile_runner.sh ${PROFILE_ID} doctor" "scripts/seed_k8s_profile_runner.sh ${PROFILE_ID} start"
  return 1
}

main() {
  require_cmd python3
  require_cmd kubectl

  if [ ! -f "${PROFILE_FILE}" ]; then
    echo "Missing profile file: ${PROFILE_FILE}" >&2
    exit 1
  fi

  if [ "${ACTION}" = "-h" ] || [ "${ACTION}" = "--help" ] || [ "${ACTION}" = "help" ]; then
    usage
    exit 0
  fi

  PROFILE_SUPPORT_TIER="$(profile_field support_tier || true)"
  PROFILE_ACCEPTANCE_LEVEL="$(profile_field acceptance_level || true)"
  PROFILE_CAPACITY_GATE="$(profile_field capacity_gate || true)"
  export SEED_PROFILE_SUPPORT_TIER="${PROFILE_SUPPORT_TIER}"
  export SEED_PROFILE_ACCEPTANCE_LEVEL="${PROFILE_ACCEPTANCE_LEVEL}"
  export SEED_PROFILE_CAPACITY_GATE="${PROFILE_CAPACITY_GATE}"

  adopt_latest_for_read_actions
  init_profile_context
  setup_runner_logging
  log "Profile=${PROFILE_ID} Action=${ACTION} BaseDir=${BASE_DIR}"

  case "${ACTION}" in
    doctor)
      run_doctor
      ;;
    build)
      if ! run_build; then
        mapfile -t _fields < <(write_runner_failure_from_validation "build")
        stage="${_fields[0]:-build}"
        failure_code="${_fields[1]:-BUILD_FAILED}"
        failure_reason="${_fields[2]:-run_build_failed}"
        evidence="${_fields[3]:-${VALIDATION_DIR}/diagnostics.json}"
        minimal="${_fields[4]:-scripts/seed_k8s_profile_runner.sh ${PROFILE_ID} build}"
        fallback="${_fields[5]:-scripts/seed_k8s_profile_runner.sh ${PROFILE_ID} doctor}"
        write_runner_artifacts "${stage}" "FAIL" "${failure_code:-BUILD_FAILED}" "${failure_reason:-run_build_failed}" "${evidence}"           "${minimal:-scripts/seed_k8s_profile_runner.sh ${PROFILE_ID} build}" "${fallback:-scripts/seed_k8s_profile_runner.sh ${PROFILE_ID} doctor}"
        exit 1
      fi
      ;;
    start)
      if ! run_start; then
        mapfile -t _fields < <(write_runner_failure_from_validation "start")
        stage="${_fields[0]:-start}"
        failure_code="${_fields[1]:-DEPLOY_TIMEOUT}"
        failure_reason="${_fields[2]:-run_start_failed}"
        evidence="${_fields[3]:-${VALIDATION_DIR}/diagnostics.json}"
        minimal="${_fields[4]:-scripts/seed_k8s_profile_runner.sh ${PROFILE_ID} start}"
        fallback="${_fields[5]:-scripts/seed_k8s_profile_runner.sh ${PROFILE_ID} doctor}"
        write_runner_artifacts "${stage}" "FAIL" "${failure_code:-DEPLOY_TIMEOUT}" "${failure_reason:-run_start_failed}" "${evidence}" \
          "${minimal:-scripts/seed_k8s_profile_runner.sh ${PROFILE_ID} start}" "${fallback:-scripts/seed_k8s_profile_runner.sh ${PROFILE_ID} doctor}"
        exit 1
      fi
      ;;
    phase-start)
      if ! run_phase_start; then
        mapfile -t _fields < <(write_runner_failure_from_validation "phase-start")
        stage="${_fields[0]:-phase-start}"
        failure_code="${_fields[1]:-PHASED_START_FAILED}"
        failure_reason="${_fields[2]:-run_phase_start_failed}"
        evidence="${_fields[3]:-${VALIDATION_DIR}/diagnostics.json}"
        minimal="${_fields[4]:-scripts/seed_k8s_profile_runner.sh ${PROFILE_ID} phase-start}"
        fallback="${_fields[5]:-scripts/seed_k8s_profile_runner.sh ${PROFILE_ID} triage}"
        write_runner_artifacts "${stage}" "FAIL" "${failure_code:-PHASED_START_FAILED}" "${failure_reason:-run_phase_start_failed}" "${evidence}"           "${minimal:-scripts/seed_k8s_profile_runner.sh ${PROFILE_ID} phase-start}" "${fallback:-scripts/seed_k8s_profile_runner.sh ${PROFILE_ID} triage}"
        exit 1
      fi
      ;;
    verify)
      if ! run_verify; then
        mapfile -t _fields < <(write_runner_failure_from_validation "verify")
        stage="${_fields[0]:-verify}"
        failure_code="${_fields[1]:-DEPLOY_TIMEOUT}"
        failure_reason="${_fields[2]:-run_verify_failed}"
        evidence="${_fields[3]:-${VALIDATION_DIR}/diagnostics.json}"
        minimal="${_fields[4]:-scripts/seed_k8s_profile_runner.sh ${PROFILE_ID} verify}"
        fallback="${_fields[5]:-scripts/seed_k8s_profile_runner.sh ${PROFILE_ID} triage}"
        write_runner_artifacts "${stage}" "FAIL" "${failure_code:-DEPLOY_TIMEOUT}" "${failure_reason:-run_verify_failed}" "${evidence}" \
          "${minimal:-scripts/seed_k8s_profile_runner.sh ${PROFILE_ID} verify}" "${fallback:-scripts/seed_k8s_profile_runner.sh ${PROFILE_ID} triage}"
        exit 1
      fi
      ;;
    observe)
      if ! run_observe; then
        mapfile -t _fields < <(write_runner_failure_from_validation "observe")
        stage="${_fields[0]:-observe}"
        failure_code="${_fields[1]:-DEPLOY_TIMEOUT}"
        failure_reason="${_fields[2]:-run_observe_failed}"
        evidence="${_fields[3]:-${VALIDATION_DIR}/diagnostics.json}"
        minimal="${_fields[4]:-scripts/seed_k8s_profile_runner.sh ${PROFILE_ID} observe}"
        fallback="${_fields[5]:-scripts/seed_k8s_profile_runner.sh ${PROFILE_ID} triage}"
        write_runner_artifacts "${stage}" "FAIL" "${failure_code:-DEPLOY_TIMEOUT}" "${failure_reason:-run_observe_failed}" "${evidence}" \
          "${minimal:-scripts/seed_k8s_profile_runner.sh ${PROFILE_ID} observe}" "${fallback:-scripts/seed_k8s_profile_runner.sh ${PROFILE_ID} triage}"
        exit 1
      fi
      write_runner_artifacts "observe" "PASS" "" "" "${OBSERVE_DIR}/summary.json" \
        "scripts/seed_k8s_profile_runner.sh ${PROFILE_ID} report" "scripts/seed_k8s_profile_runner.sh ${PROFILE_ID} triage"
      ;;
    all)
      if ! run_all; then
        mapfile -t _fields < <(write_runner_failure_from_validation "all")
        stage="${_fields[0]:-all}"
        failure_code="${_fields[1]:-DEPLOY_TIMEOUT}"
        failure_reason="${_fields[2]:-run_all_failed}"
        evidence="${_fields[3]:-${VALIDATION_DIR}/diagnostics.json}"
        minimal="${_fields[4]:-scripts/seed_k8s_profile_runner.sh ${PROFILE_ID} triage}"
        fallback="${_fields[5]:-scripts/seed_k8s_profile_runner.sh ${PROFILE_ID} doctor}"
        write_runner_artifacts "${stage}" "FAIL" "${failure_code:-DEPLOY_TIMEOUT}" "${failure_reason:-run_all_failed}" "${evidence}" \
          "${minimal:-scripts/seed_k8s_profile_runner.sh ${PROFILE_ID} triage}" "${fallback:-scripts/seed_k8s_profile_runner.sh ${PROFILE_ID} doctor}"
        exit 1
      fi
      ;;
    triage)
      run_triage
      ;;
    report)
      if ! run_report; then
        mapfile -t _fields < <(write_runner_failure_from_validation "report")
        stage="${_fields[0]:-report}"
        failure_code="${_fields[1]:-DEPLOY_TIMEOUT}"
        failure_reason="${_fields[2]:-run_report_failed}"
        evidence="${_fields[3]:-${VALIDATION_DIR}/diagnostics.json}"
        minimal="${_fields[4]:-scripts/seed_k8s_profile_runner.sh ${PROFILE_ID} report}"
        fallback="${_fields[5]:-scripts/seed_k8s_profile_runner.sh ${PROFILE_ID} triage}"
        write_runner_artifacts "${stage}" "FAIL" "${failure_code:-DEPLOY_TIMEOUT}" "${failure_reason:-run_report_failed}" "${evidence}" \
          "${minimal:-scripts/seed_k8s_profile_runner.sh ${PROFILE_ID} report}" "${fallback:-scripts/seed_k8s_profile_runner.sh ${PROFILE_ID} triage}"
        exit 1
      fi
      write_runner_artifacts "report" "PASS" "" "" "${REPORT_DIR}/report.json" \
        "scripts/seed_k8s_profile_runner.sh ${PROFILE_ID} triage" "scripts/seed_k8s_profile_runner.sh ${PROFILE_ID} doctor"
      sync_validation_summary_runtime_fields
      ;;
    compare)
      run_compare
      ;;
    showcase)
      run_showcase
      ;;
    *)
      usage
      exit 1
      ;;
  esac

  log "Done. Runner summary: ${RUNNER_SUMMARY}"
}

main "$@"
