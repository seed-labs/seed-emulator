#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${SCRIPT_DIR}/env_seedemu.sh"

SUITE="${1:-all}"
TS="$(date +%Y%m%d_%H%M%S)"
OUT_DIR="${REPO_ROOT}/output/acceptance/${TS}"
mkdir -p "${OUT_DIR}"

log() {
  echo "[acceptance] $*"
}

profile_namespace() {
  local profile="$1"
  PROFILE_LOOKUP="${profile}" python3 - <<'PY'
import os
from pathlib import Path

try:
    import yaml  # type: ignore
except Exception as exc:
    raise SystemExit(f"PyYAML required to parse profile file: {exc}")

profile = os.environ["PROFILE_LOOKUP"]
override = os.environ.get("SEED_NAMESPACE", "").strip()
if override:
    print(override)
    raise SystemExit(0)

repo_root = Path(os.environ["REPO_ROOT"])
config_path = repo_root / "configs/seed_k8s_profiles.yaml"
data = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}
profiles = data.get("profiles", {}) if isinstance(data, dict) else {}
entry = profiles.get(profile, {})
if not isinstance(entry, dict):
    raise SystemExit(f"Unknown profile: {profile}")
print(str(entry.get("default_namespace", "") or ""))
PY
}

cleanup_profile_runtime() {
  local profile="$1"
  local namespace
  namespace="$(profile_namespace "${profile}")"

  if [ -z "${namespace}" ]; then
    log "Skip cleanup for ${profile}: namespace not resolved"
    return 0
  fi

  if ! kubectl get namespace "${namespace}" >/dev/null 2>&1; then
    log "Namespace already clean for ${profile}: ${namespace}"
    return 0
  fi

  log "Cleaning namespace for ${profile}: ${namespace}"
  kubectl delete namespace "${namespace}" --ignore-not-found >/dev/null 2>&1 || true

  local waited=0
  until ! kubectl get namespace "${namespace}" >/dev/null 2>&1; do
    if [ "${waited}" -ge 30 ]; then
      kubectl -n "${namespace}" delete pod --all --force --grace-period=0 >/dev/null 2>&1 || true
    fi
    sleep 5
    waited=$((waited + 5))
    if [ "${waited}" -ge "${SEED_ACCEPTANCE_NAMESPACE_DELETE_TIMEOUT_SECONDS:-600}" ]; then
      echo "Timed out waiting for namespace deletion: ${namespace}" >&2
      return 1
    fi
  done

  log "Namespace deleted for ${profile}: ${namespace}"
}

run_runtime_profile() {
  local profile="$1"
  shift
  local acceptance_distribution_mode
  acceptance_distribution_mode="${SEED_IMAGE_DISTRIBUTION_MODE:-${SEED_ACCEPTANCE_IMAGE_DISTRIBUTION_MODE:-registry}}"

  cleanup_profile_runtime "${profile}"
  log "Runtime image distribution for ${profile}: ${acceptance_distribution_mode}"

  if ! SEED_IMAGE_DISTRIBUTION_MODE="${acceptance_distribution_mode}" run_profile_pipeline "${profile}" "$@"; then
    record_result "runtime-${profile}" "FAIL" "pipeline_failed"
    cleanup_profile_runtime "${profile}" || true
    return 1
  fi

  record_result "runtime-${profile}" "PASS" ""
  cleanup_profile_runtime "${profile}"
}

record_result() {
  local suite_name="$1"
  local status="$2"
  local detail="${3:-}"
  python3 - <<PY
import json
from pathlib import Path

path = Path(${OUT_DIR@Q}) / "summary.json"
if path.exists():
    data = json.loads(path.read_text(encoding="utf-8"))
else:
    data = {"results": []}
data.setdefault("results", []).append(
    {"suite": ${suite_name@Q}, "status": ${status@Q}, "detail": ${detail@Q}}
)
path.write_text(json.dumps(data, indent=2), encoding="utf-8")
PY
}

run_docs_suite() {
  log "Running docs hygiene and shortcut smoke"
  "${SCRIPT_DIR}/check_doc_hygiene.sh" || return 1
  (
    source "${SCRIPT_DIR}/env_seedemu.sh"
    for cmd in k3sdoctor k3sbuild k3sup k3sphase k3sverify k3sobserve k3sreport k3sall k3scompare k3sdown k3sps k3slogs k3sexec k3stop k3sevents; do
      command -v "${cmd}" >/dev/null 2>&1
      "${cmd}" --help >/dev/null 2>&1 || "${cmd}" help >/dev/null 2>&1 || true
    done
  ) || return 1
}

run_unit_suite() {
  log "Running Python unit and compiler tests"
  python3 -m unittest \
    tests.ibgp_route_reflector_test \
    tests.routing_scale_profiles_test \
    tests.kubernetes_by_as_hard_test \
    tests.seed_k8s_profile_contract_test \
    tests.seed_k8s_validation_contract_test \
    tests.seed_k8s_cluster_inventory_test \
    tests.seed_k8s_bgp_health_test \
    tests.seed_k8s_failure_injection_test \
    tests.kubevirt_compiler_test \
    -v || return 1
}

example_tier() {
  case "$1" in
    k8s_mini_internet.py|k8s_real_topology_rr.py) echo "tier1" ;;
    k8s_transit_as.py|k8s_mini_internet_with_visualization.py|k8s_hybrid_kubevirt_demo.py) echo "tier2" ;;
    *) echo "tier3" ;;
  esac
}

compile_one_example() {
  local script_path="$1"
  local script_name out_dir
  script_name="$(basename "${script_path}")"
  out_dir="${OUT_DIR}/compile/${script_name%.py}"
  mkdir -p "${out_dir}"

  local -a env_prefix
  env_prefix=(
    env
    "PYTHONPATH=${REPO_ROOT}"
    "SEED_NAMESPACE=seedemu-acceptance-${script_name%.py}"
    "SEED_REGISTRY=${SEED_REGISTRY:-192.168.122.110:5000}"
    "SEED_CNI_TYPE=${SEED_CNI_TYPE:-macvlan}"
    "SEED_CNI_MASTER_INTERFACE=${SEED_CNI_MASTER_INTERFACE:-ens2}"
    "SEED_SCHEDULING_STRATEGY=${SEED_SCHEDULING_STRATEGY:-auto}"
    "SEED_OUTPUT_DIR=${out_dir}"
  )

  case "${script_name}" in
    k8s_real_topology_rr.py)
      env_prefix+=(
        "SEED_REAL_TOPOLOGY_DIR=${SEED_REAL_TOPOLOGY_DIR:-$HOME/lxl_topology/autocoder_test}"
        "SEED_ASSIGNMENT_FILE=${SEED_ASSIGNMENT_FILE:-${SEED_REAL_TOPOLOGY_DIR:-$HOME/lxl_topology/autocoder_test}/assignment.pkl}"
        "SEED_TOPOLOGY_SIZE=${SEED_TOPOLOGY_SIZE:-214}"
      )
      ;;
    k8s_hybrid_kubevirt_demo.py)
      env_prefix+=("SEED_RUNTIME_PROFILE=${SEED_RUNTIME_PROFILE:-degraded}")
      ;;
  esac

  (
    cd "${REPO_ROOT}"
    "${env_prefix[@]}" python3 "${script_path}"
  ) > "${out_dir}/compile.log" 2>&1

  test -f "${out_dir}/k8s.yaml"
  test -x "${out_dir}/build_images.sh"
}

run_compile_all_suite() {
  log "Running compile smoke for all Kubernetes examples"
  local script_path
  while IFS= read -r script_path; do
    log "Compile smoke: ${script_path} ($(example_tier "$(basename "${script_path}")"))"
    compile_one_example "${script_path}" || return 1
  done < <(find "${REPO_ROOT}/examples/kubernetes" -maxdepth 1 -name 'k8s_*.py' | sort)
}

run_profile_pipeline() {
  local profile="$1"
  shift
  local step
  for step in "$@"; do
    log "Profile ${profile}: ${step}"
    if ! "${SCRIPT_DIR}/seed_k8s_profile_runner.sh" "${profile}" "${step}"; then
      return 1
    fi
  done
}

run_tier1_runtime_suite() {
  log "Running Tier-1 runtime acceptance"
  cleanup_profile_runtime mini_internet || return 1
  cleanup_profile_runtime real_topology_rr || return 1
  cleanup_profile_runtime real_topology_rr_scale || return 1

  run_runtime_profile mini_internet all || return 1
  SEED_TOPOLOGY_SIZE=214 run_runtime_profile real_topology_rr all || return 1
  SEED_TOPOLOGY_SIZE=214 run_runtime_profile real_topology_rr_scale all || return 1
}

run_tier2_runtime_suite() {
  log "Running Tier-2 runtime acceptance"
  cleanup_profile_runtime transit_as || return 1
  cleanup_profile_runtime mini_internet_viz || return 1
  cleanup_profile_runtime hybrid_kubevirt || return 1

  run_runtime_profile transit_as build start verify observe report || return 1
  run_runtime_profile mini_internet_viz build start verify observe report || return 1

  if kubectl api-resources 2>/dev/null | grep -qi '^virtualmachines[[:space:]]'; then
    SEED_RUNTIME_PROFILE=auto run_runtime_profile hybrid_kubevirt build start verify observe report || return 1
  else
    log "hybrid_kubevirt capability-gated: VirtualMachine resources are not available on this cluster"
    record_result "tier2-runtime-hybrid_kubevirt" "CAPABILITY_GATED" "VirtualMachine resources are not available on this cluster"
  fi
}

run_suite() {
  case "$1" in
    docs) run_docs_suite ;;
    unit) run_unit_suite ;;
    compile-all) run_compile_all_suite ;;
    tier1-runtime) run_tier1_runtime_suite ;;
    tier2-runtime) run_tier2_runtime_suite ;;
    all)
      run_docs_suite || return 1
      run_unit_suite || return 1
      run_compile_all_suite || return 1
      run_tier1_runtime_suite || return 1
      run_tier2_runtime_suite || return 1
      ;;
    *)
      echo "Usage: scripts/seed_k8s_acceptance.sh [docs|unit|compile-all|tier1-runtime|tier2-runtime|all]" >&2
      exit 2
      ;;
  esac
}

if run_suite "${SUITE}"; then
  record_result "${SUITE}" "PASS" ""
  log "Acceptance suite passed: ${SUITE}"
else
  record_result "${SUITE}" "FAIL" ""
  log "Acceptance suite failed: ${SUITE}"
  exit 1
fi
