#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
COMMON_DIR="${SCRIPT_DIR}/_common"

# shellcheck source=/dev/null
source "${COMMON_DIR}/env.sh"
# shellcheck source=/dev/null
source "${COMMON_DIR}/io.sh"

TIER="all"
MODE="both"
RISK="off"
CONFIRM_TOKEN=""
ARTIFACTS_ROOT="${SCRIPT_DIR}"
OUTPUT_B29=""
OUTPUT_B00=""

usage() {
  cat <<'EOF'
Usage: examples/agent-base/run_all.sh [options]

Options:
  --tier all|maintenance|experiment
  --mode canonical|fallback|both
  --risk on|off
  --confirm-token <token>
  --artifacts-root <path>
  --b29-output-dir <path>
  --b00-output-dir <path>
  -h, --help
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --tier) TIER="${2:-}"; shift 2 ;;
    --mode) MODE="${2:-}"; shift 2 ;;
    --risk) RISK="${2:-}"; shift 2 ;;
    --confirm-token) CONFIRM_TOKEN="${2:-}"; shift 2 ;;
    --artifacts-root) ARTIFACTS_ROOT="${2:-}"; shift 2 ;;
    --b29-output-dir) OUTPUT_B29="${2:-}"; shift 2 ;;
    --b00-output-dir) OUTPUT_B00="${2:-}"; shift 2 ;;
    -h|--help) usage; exit 0 ;;
    *)
      seed_log_error "Unknown argument: $1"
      usage
      exit 2
      ;;
  esac
done

seed_validate_mode "${MODE}"

if [[ -n "${OUTPUT_B29}" ]]; then
  export B29_OUTPUT_DIR="${OUTPUT_B29}"
fi
if [[ -n "${OUTPUT_B00}" ]]; then
  export B00_OUTPUT_DIR="${OUTPUT_B00}"
fi

scenario_paths=()
case "${TIER}" in
  all)
    scenario_paths+=(
      "${SCRIPT_DIR}/S01_b29_health_maintenance/run.sh"
      "${SCRIPT_DIR}/S02_b00_path_maintenance/run.sh"
      "${SCRIPT_DIR}/S03_b00_latency_experiment/run.sh"
      "${SCRIPT_DIR}/S04_b29_packetloss_experiment/run.sh"
    )
    ;;
  maintenance)
    scenario_paths+=(
      "${SCRIPT_DIR}/S01_b29_health_maintenance/run.sh"
      "${SCRIPT_DIR}/S02_b00_path_maintenance/run.sh"
    )
    ;;
  experiment)
    scenario_paths+=(
      "${SCRIPT_DIR}/S03_b00_latency_experiment/run.sh"
      "${SCRIPT_DIR}/S04_b29_packetloss_experiment/run.sh"
    )
    ;;
  *)
    seed_log_error "Invalid --tier value: ${TIER}"
    exit 2
    ;;
esac

fail_count=0
for scenario_run in "${scenario_paths[@]}"; do
  seed_log_info "Running scenario: ${scenario_run}"
  set +e
  "${scenario_run}" \
    --mode "${MODE}" \
    --risk "${RISK}" \
    --confirm-token "${CONFIRM_TOKEN}" \
    --artifacts-root "${ARTIFACTS_ROOT}"
  rc=$?
  set -e
  if [[ ${rc} -ne 0 ]]; then
    seed_log_error "Scenario failed (rc=${rc}): ${scenario_run}"
    fail_count=$((fail_count + 1))
  else
    seed_log_info "Scenario succeeded: ${scenario_run}"
  fi
done

if [[ ${fail_count} -gt 0 ]]; then
  seed_log_error "run_all completed with ${fail_count} failed scenario(s)"
  exit 1
fi

seed_log_info "run_all completed successfully"
