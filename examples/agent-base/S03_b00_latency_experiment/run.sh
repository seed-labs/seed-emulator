#!/usr/bin/env bash
set -euo pipefail

THIS_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
COMMON_DIR="${THIS_DIR}/../_common"

# shellcheck source=/dev/null
source "${COMMON_DIR}/env.sh"
# shellcheck source=/dev/null
source "${COMMON_DIR}/io.sh"
# shellcheck source=/dev/null
source "${COMMON_DIR}/assertions.sh"

SCENARIO_ID="S03_b00_latency_experiment"
BASELINE="B00"
WORKSPACE_NAME="lab1"
PLAYBOOK_FILE="${THIS_DIR}/playbook.fallback.yaml"
DEFAULT_POLICY="read_only"
GATE_TOKEN_EXPECTED="YES_RUN_DYNAMIC_FAULTS"

BASELINE_REQUEST="Attach to \${B00_OUTPUT_DIR}; run read-only baseline observation for BGP and path health."
EXPERIMENT_REQUEST="Attach to \${B00_OUTPUT_DIR}; inject latency fault on router links using inject_fault latency, then collect traceroute and evidence."
ROLLBACK_REQUEST="Attach to \${B00_OUTPUT_DIR}; rollback latency experiment using inject_fault reset and verify post-rollback path health."

MODE="both"
POLICY="${DEFAULT_POLICY}"
OUTPUT_DIR_OVERRIDE=""
ARTIFACTS_ROOT="${THIS_DIR}/artifacts"
RISK="off"
CONFIRM_TOKEN=""

usage() {
  cat <<'EOF'
Usage: S03_b00_latency_experiment/run.sh [options]

Options:
  --mode canonical|fallback|both
  --policy read_only|net_ops|danger      (baseline policy; experiment uses net_ops)
  --output-dir <path>
  --artifacts-root <path>
  --risk on|off
  --confirm-token YES_RUN_DYNAMIC_FAULTS
  -h, --help
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --mode) MODE="${2:-}"; shift 2 ;;
    --policy) POLICY="${2:-}"; shift 2 ;;
    --output-dir) OUTPUT_DIR_OVERRIDE="${2:-}"; shift 2 ;;
    --artifacts-root) ARTIFACTS_ROOT="${2:-}"; shift 2 ;;
    --risk) RISK="${2:-}"; shift 2 ;;
    --confirm-token) CONFIRM_TOKEN="${2:-}"; shift 2 ;;
    -h|--help) usage; exit 0 ;;
    *)
      seed_log_error "Unknown argument: $1"
      usage
      exit 2
      ;;
  esac
done

seed_validate_mode "${MODE}"
seed_require_file "${PLAYBOOK_FILE}"

OUTPUT_DIR="$(seed_resolve_output_dir "${BASELINE}" "${OUTPUT_DIR_OVERRIDE}")"
if [[ ! -d "${OUTPUT_DIR}" ]]; then
  seed_log_warn "Output directory not found, returning needs_input: ${OUTPUT_DIR}"
  exit 2
fi

RUN_DIR="$(seed_make_run_dir "${ARTIFACTS_ROOT}" "${SCENARIO_ID}")"
CANONICAL_DIR="${RUN_DIR}/canonical"
FALLBACK_DIR="${RUN_DIR}/fallback"
seed_ensure_dir "${CANONICAL_DIR}"
seed_ensure_dir "${FALLBACK_DIR}"

CAN_BASELINE_JSON="${CANONICAL_DIR}/baseline.canonical.json"
CAN_EXPERIMENT_JSON="${CANONICAL_DIR}/experiment.canonical.json"
CAN_ROLLBACK_JSON="${CANONICAL_DIR}/rollback.canonical.json"
CAN_POLICY_JSON="${CANONICAL_DIR}/policy_check.json"

FB_BASELINE_JSON="${FALLBACK_DIR}/baseline.fallback.json"
FB_EXPERIMENT_JSON="${FALLBACK_DIR}/experiment.fallback.json"
FB_ROLLBACK_JSON="${FALLBACK_DIR}/rollback.fallback.json"

PRIMARY_BASELINE="${RUN_DIR}/baseline.json"
PRIMARY_EXPERIMENT="${RUN_DIR}/experiment.json"
PRIMARY_ROLLBACK="${RUN_DIR}/rollback.json"
COMPARISON_MD="${RUN_DIR}/comparison.md"

TMP_BASELINE_PLAYBOOK="${RUN_DIR}/_tmp_baseline.playbook.yaml"
TMP_ROLLBACK_PLAYBOOK="${RUN_DIR}/_tmp_rollback.playbook.yaml"

cat > "${TMP_BASELINE_PLAYBOOK}" <<'YAML'
version: 1
name: s03_baseline_read_only
defaults:
  selector:
    role: ["BorderRouter", "Router"]
  timeout_seconds: 20
  parallelism: 20
  max_output_chars: 12000
steps:
  - action: workspace_refresh
    id: refresh
    save_as: baseline_refresh
  - action: routing_bgp_summary
    id: bgp
    save_as: baseline_bgp
  - action: traceroute
    id: trace
    dst: 1.1.1.1
    save_as: baseline_trace
YAML

cat > "${TMP_ROLLBACK_PLAYBOOK}" <<'YAML'
version: 1
name: s03_latency_rollback
defaults:
  selector:
    role: ["BorderRouter", "Router"]
  timeout_seconds: 20
  parallelism: 20
  max_output_chars: 12000
steps:
  - action: inject_fault
    id: rollback_reset
    fault_type: reset
    interface: eth0
    save_as: rollback_reset_result
  - action: sleep
    id: settle_after_reset
    seconds: 2
  - action: traceroute
    id: trace_after_reset
    dst: 1.1.1.1
    save_as: trace_after_reset
YAML

run_seed_agent() {
  local request_text="$1"
  local policy_profile="$2"
  local out_file="$3"
  local pybin
  pybin="$(seed_python_bin)"
  B00_OUTPUT_DIR="${OUTPUT_DIR}" \
  "${pybin}" "${COMMON_DIR}/invoke_seed_agent.py" run \
    --url "${SEED_AGENT_MCP_URL}" \
    --token "${SEED_AGENT_MCP_TOKEN:-}" \
    --request "${request_text}" \
    --workspace-name "${WORKSPACE_NAME}" \
    --attach-output-dir "${OUTPUT_DIR}" \
    --policy-profile "${policy_profile}" \
    --follow-job \
    --no-download-artifacts \
    --artifacts-dir "${CANONICAL_DIR}/downloads" \
    > "${out_file}"
}

run_seed_agent_policy_check() {
  local command_text="$1"
  local policy_profile="$2"
  local out_file="$3"
  local pybin
  pybin="$(seed_python_bin)"
  "${pybin}" "${COMMON_DIR}/invoke_seed_agent.py" policy-check \
    --url "${SEED_AGENT_MCP_URL}" \
    --token "${SEED_AGENT_MCP_TOKEN:-}" \
    --command "${command_text}" \
    --policy-profile "${policy_profile}" \
    > "${out_file}"
}

run_seedops_playbook() {
  local playbook_file="$1"
  local out_file="$2"
  local downloads_dir="$3"
  local pybin
  pybin="$(seed_python_bin)"
  "${pybin}" "${COMMON_DIR}/invoke_seedops_fallback.py" run-playbook-flow \
    --url "${SEEDOPS_MCP_URL}" \
    --token "${SEEDOPS_MCP_TOKEN:-${SEED_MCP_TOKEN:-}}" \
    --workspace-name "${WORKSPACE_NAME}" \
    --output-dir "${OUTPUT_DIR}" \
    --playbook-file "${playbook_file}" \
    --download-artifacts \
    --artifacts-dir "${downloads_dir}" \
    > "${out_file}"
}

canonical_baseline_status="ok"
canonical_experiment_status="ok"
canonical_rollback_status="ok"
fallback_baseline_status="ok"
fallback_experiment_status="ok"
fallback_rollback_status="ok"

if [[ "${MODE}" == "canonical" || "${MODE}" == "both" ]]; then
  seed_log_info "[S03] canonical baseline"
  run_seed_agent "${BASELINE_REQUEST}" "${POLICY}" "${CAN_BASELINE_JSON}"
  canonical_baseline_status="$(seed_json_status "${CAN_BASELINE_JSON}")"
  if [[ "${canonical_baseline_status}" == "ok" ]]; then
    seed_assert_summary_job_terminal "${CAN_BASELINE_JSON}"
  fi
fi

if [[ "${MODE}" == "fallback" || "${MODE}" == "both" ]]; then
  seed_log_info "[S03] fallback baseline"
  run_seedops_playbook "${TMP_BASELINE_PLAYBOOK}" "${FB_BASELINE_JSON}" "${FALLBACK_DIR}/downloads_baseline"
  fallback_baseline_status="$(seed_json_status "${FB_BASELINE_JSON}")"
  if [[ "${fallback_baseline_status}" == "ok" ]]; then
    seed_assert_summary_job_terminal "${FB_BASELINE_JSON}"
  fi
fi

gate_enabled=false
if [[ "${RISK}" == "on" && "${CONFIRM_TOKEN}" == "${GATE_TOKEN_EXPECTED}" ]]; then
  gate_enabled=true
fi

if [[ "${gate_enabled}" != "true" ]]; then
  seed_log_warn "[S03] Risk gate blocked experiment stage"
  cat > "${PRIMARY_EXPERIMENT}" <<EOF
{
  "status": "blocked",
  "errors": ["risk gate disabled or confirm token mismatch"],
  "warnings": [],
  "request_id": "gate-blocked"
}
EOF
  cp "${PRIMARY_EXPERIMENT}" "${PRIMARY_ROLLBACK}"
  if [[ "${MODE}" == "canonical" || "${MODE}" == "both" ]]; then
    cp "${CAN_BASELINE_JSON}" "${PRIMARY_BASELINE}"
  else
    cp "${FB_BASELINE_JSON}" "${PRIMARY_BASELINE}"
  fi
  cat > "${COMPARISON_MD}" <<EOF
# S03 Comparison

- baseline_status: \`${canonical_baseline_status}\` (canonical) / \`${fallback_baseline_status}\` (fallback)
- experiment_stage: blocked by risk gate
- rollback_stage: blocked by risk gate
EOF
  exit 3
fi

if [[ "${MODE}" == "canonical" || "${MODE}" == "both" ]]; then
  seed_log_info "[S03] canonical policy precheck + experiment + rollback"
  run_seed_agent_policy_check "tc qdisc add dev eth0 root netem delay 120ms" "net_ops" "${CAN_POLICY_JSON}"
  run_seed_agent "${EXPERIMENT_REQUEST}" "net_ops" "${CAN_EXPERIMENT_JSON}"
  run_seed_agent "${ROLLBACK_REQUEST}" "net_ops" "${CAN_ROLLBACK_JSON}"
  canonical_experiment_status="$(seed_json_status "${CAN_EXPERIMENT_JSON}")"
  canonical_rollback_status="$(seed_json_status "${CAN_ROLLBACK_JSON}")"
  if [[ "${canonical_experiment_status}" == "ok" ]]; then
    seed_assert_summary_job_terminal "${CAN_EXPERIMENT_JSON}"
  fi
  if [[ "${canonical_rollback_status}" == "ok" ]]; then
    seed_assert_summary_job_terminal "${CAN_ROLLBACK_JSON}"
  fi
fi

if [[ "${MODE}" == "fallback" || "${MODE}" == "both" ]]; then
  seed_log_info "[S03] fallback experiment + rollback"
  run_seedops_playbook "${PLAYBOOK_FILE}" "${FB_EXPERIMENT_JSON}" "${FALLBACK_DIR}/downloads_experiment"
  run_seedops_playbook "${TMP_ROLLBACK_PLAYBOOK}" "${FB_ROLLBACK_JSON}" "${FALLBACK_DIR}/downloads_rollback"
  fallback_experiment_status="$(seed_json_status "${FB_EXPERIMENT_JSON}")"
  fallback_rollback_status="$(seed_json_status "${FB_ROLLBACK_JSON}")"
  if [[ "${fallback_experiment_status}" == "ok" ]]; then
    seed_assert_summary_job_terminal "${FB_EXPERIMENT_JSON}"
  fi
  if [[ "${fallback_rollback_status}" == "ok" ]]; then
    seed_assert_summary_job_terminal "${FB_ROLLBACK_JSON}"
  fi
fi

if [[ "${MODE}" == "both" ]]; then
  seed_assert_status_consistent "${CAN_BASELINE_JSON}" "${FB_BASELINE_JSON}"
  seed_assert_status_consistent "${CAN_EXPERIMENT_JSON}" "${FB_EXPERIMENT_JSON}"
  seed_assert_status_consistent "${CAN_ROLLBACK_JSON}" "${FB_ROLLBACK_JSON}"
fi

if [[ "${MODE}" == "fallback" ]]; then
  cp "${FB_BASELINE_JSON}" "${PRIMARY_BASELINE}"
  cp "${FB_EXPERIMENT_JSON}" "${PRIMARY_EXPERIMENT}"
  cp "${FB_ROLLBACK_JSON}" "${PRIMARY_ROLLBACK}"
else
  cp "${CAN_BASELINE_JSON}" "${PRIMARY_BASELINE}"
  cp "${CAN_EXPERIMENT_JSON}" "${PRIMARY_EXPERIMENT}"
  cp "${CAN_ROLLBACK_JSON}" "${PRIMARY_ROLLBACK}"
fi

pybin="$(seed_python_bin)"
"${pybin}" - "${PRIMARY_BASELINE}" "${PRIMARY_EXPERIMENT}" "${PRIMARY_ROLLBACK}" "${COMPARISON_MD}" <<'PY'
import json
import sys
from pathlib import Path

baseline = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
experiment = json.loads(Path(sys.argv[2]).read_text(encoding="utf-8"))
rollback = json.loads(Path(sys.argv[3]).read_text(encoding="utf-8"))
out = Path(sys.argv[4])

def job_status(payload):
    summary = payload.get("summary", {})
    if isinstance(summary, dict) and summary.get("job_status"):
        return summary.get("job_status")
    return ((payload.get("job") or {}).get("final") or {}).get("job", {}).get("status", "")

rollback_has_reset = "reset" in json.dumps(rollback, ensure_ascii=False).lower()

lines = [
    "# S03 Comparison",
    "",
    f"- baseline.status: `{baseline.get('status', 'error')}`",
    f"- baseline.job_status: `{job_status(baseline)}`",
    f"- experiment.status: `{experiment.get('status', 'error')}`",
    f"- experiment.job_status: `{job_status(experiment)}`",
    f"- rollback.status: `{rollback.get('status', 'error')}`",
    f"- rollback.job_status: `{job_status(rollback)}`",
    f"- rollback_contains_reset: `{rollback_has_reset}`",
]
out.write_text("\n".join(lines) + "\n", encoding="utf-8")
PY

canonical_code=0
fallback_code=0
for s in "${canonical_baseline_status}" "${canonical_experiment_status}" "${canonical_rollback_status}"; do
  c="$(seed_status_to_exit_code "${s}")"
  if [[ "${c}" -gt "${canonical_code}" ]]; then
    canonical_code="${c}"
  fi
done
for s in "${fallback_baseline_status}" "${fallback_experiment_status}" "${fallback_rollback_status}"; do
  c="$(seed_status_to_exit_code "${s}")"
  if [[ "${c}" -gt "${fallback_code}" ]]; then
    fallback_code="${c}"
  fi
done

final_code=0
if [[ "${MODE}" == "canonical" ]]; then
  final_code="${canonical_code}"
elif [[ "${MODE}" == "fallback" ]]; then
  final_code="${fallback_code}"
else
  final_code="${canonical_code}"
  if [[ "${fallback_code}" -gt "${final_code}" ]]; then
    final_code="${fallback_code}"
  fi
fi

seed_log_info "[S03] completed with exit_code=${final_code}, run_dir=${RUN_DIR}"
exit "${final_code}"
