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

SCENARIO_ID="S04_b29_packetloss_experiment"
BASELINE="B29"
WORKSPACE_NAME="lab1"
PLAYBOOK_FILE="${THIS_DIR}/playbook.fallback.yaml"
DEFAULT_POLICY="read_only"
GATE_TOKEN_EXPECTED="YES_RUN_DYNAMIC_FAULTS"

BASELINE_REQUEST="Attach to \${B29_OUTPUT_DIR}; focus on ASN 200/201 only; run read-only baseline observation and collect operational mail logs."
EXPERIMENT_REQUEST="Attach to \${B29_OUTPUT_DIR}; focus on ASN 200/201 only; inject packet loss fault (inject_fault packet_loss) in net_ops and collect mail logs during impact."
ROLLBACK_REQUEST="Attach to \${B29_OUTPUT_DIR}; focus on ASN 200/201 only; rollback packet-loss fault using inject_fault reset and collect post-rollback mail logs."

MODE="both"
POLICY="${DEFAULT_POLICY}"
OUTPUT_DIR_OVERRIDE=""
ARTIFACTS_ROOT="${THIS_DIR}/artifacts"
RISK="off"
CONFIRM_TOKEN=""
FALLBACK_TIMEOUT_SECONDS="${FALLBACK_TIMEOUT_SECONDS:-1200}"
SEED_AGENT_FOLLOW_JOB="${SEED_AGENT_FOLLOW_JOB:-1}"

usage() {
  cat <<'EOF'
Usage: S04_b29_packetloss_experiment/run.sh [options]

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

MAIL_BEFORE="${RUN_DIR}/mail_logs.before.txt"
MAIL_DURING="${RUN_DIR}/mail_logs.during.txt"
MAIL_AFTER="${RUN_DIR}/mail_logs.after.txt"
REPORT_MD="${RUN_DIR}/experiment_report.md"

TMP_BASELINE_PLAYBOOK="${RUN_DIR}/_tmp_baseline.playbook.yaml"
TMP_ROLLBACK_PLAYBOOK="${RUN_DIR}/_tmp_rollback.playbook.yaml"

cat > "${TMP_BASELINE_PLAYBOOK}" <<'YAML'
version: 1
name: s04_baseline_mail_logs
defaults:
  selector:
    asn: [200, 201]
    role: ["Host"]
  timeout_seconds: 20
  parallelism: 20
  max_output_chars: 12000
steps:
  - action: workspace_refresh
    id: refresh
    save_as: baseline_refresh
  - action: ops_logs
    id: mail_logs_before_fault
    tail: 200
    save_as: mail_logs_before
YAML

cat > "${TMP_ROLLBACK_PLAYBOOK}" <<'YAML'
version: 1
name: s04_packetloss_rollback
defaults:
  selector:
    asn: [200, 201]
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
  - action: ops_logs
    id: mail_logs_after_fault
    selector:
      asn: [200, 201]
      role: ["Host"]
    tail: 200
    save_as: mail_logs_after
YAML

run_seed_agent() {
  local request_text="$1"
  local policy_profile="$2"
  local out_file="$3"
  local pybin
  pybin="$(seed_python_bin)"
  local -a follow_args=(--follow-job)
  if [[ "${SEED_AGENT_FOLLOW_JOB}" != "1" ]]; then
    follow_args=(--no-follow-job)
  fi
  B29_OUTPUT_DIR="${OUTPUT_DIR}" \
  "${pybin}" "${COMMON_DIR}/invoke_seed_agent.py" run \
    --url "${SEED_AGENT_MCP_URL}" \
    --token "${SEED_AGENT_MCP_TOKEN:-}" \
    --request "${request_text}" \
    --workspace-name "${WORKSPACE_NAME}" \
    --attach-output-dir "${OUTPUT_DIR}" \
    --policy-profile "${policy_profile}" \
    "${follow_args[@]}" \
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
    --timeout-seconds "${FALLBACK_TIMEOUT_SECONDS}" \
    --download-artifacts \
    --artifacts-dir "${downloads_dir}" \
    > "${out_file}"
}

extract_mail_logs() {
  local src_json="$1"
  local expected_name="$2"
  local out_file="$3"
  local pybin
  pybin="$(seed_python_bin)"
  "${pybin}" - "${src_json}" "${expected_name}" "${out_file}" <<'PY'
import json
import sys
from pathlib import Path

payload = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
expected = str(sys.argv[2]).lower()
out_file = Path(sys.argv[3])

artifacts = payload.get("artifacts", {}).get("list", {}).get("artifacts", []) or []
downloaded = payload.get("artifacts", {}).get("downloaded", []) or []
name_by_id = {}
for row in artifacts:
    if isinstance(row, dict):
        aid = str(row.get("artifact_id") or "")
        if aid:
            name_by_id[aid] = str(row.get("name") or "")

log_text = ""
for row in downloaded:
    if not isinstance(row, dict):
        continue
    aid = str(row.get("artifact_id") or "")
    name = name_by_id.get(aid, "")
    if expected not in name.lower():
        continue
    p = Path(str(row.get("out_path") or ""))
    if not p.exists():
        continue
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        continue
    logs = data.get("logs") if isinstance(data, dict) else None
    if isinstance(logs, list):
        chunks = []
        for item in logs:
            if isinstance(item, dict):
                node_id = str(item.get("node_id") or "unknown")
                log = str(item.get("log") or "").strip()
                if log:
                    chunks.append(f"=== {node_id} ===\n{log}")
        log_text = "\n\n".join(chunks).strip()
        if log_text:
            break

if not log_text:
    log_text = f"[no logs extracted for {expected}]"

out_file.write_text(log_text + "\n", encoding="utf-8")
PY
}

canonical_baseline_status="ok"
canonical_experiment_status="ok"
canonical_rollback_status="ok"
fallback_baseline_status="ok"
fallback_experiment_status="ok"
fallback_rollback_status="ok"

# Baseline stage
if [[ "${MODE}" == "canonical" || "${MODE}" == "both" ]]; then
  seed_log_info "[S04] canonical baseline"
  run_seed_agent "${BASELINE_REQUEST}" "${POLICY}" "${CAN_BASELINE_JSON}"
  canonical_baseline_status="$(seed_json_status "${CAN_BASELINE_JSON}")"
  if [[ "${canonical_baseline_status}" == "ok" && "${SEED_AGENT_FOLLOW_JOB}" == "1" ]]; then
    seed_assert_summary_job_terminal "${CAN_BASELINE_JSON}"
  fi
fi

if [[ "${MODE}" == "fallback" || "${MODE}" == "both" ]]; then
  seed_log_info "[S04] fallback baseline (for deterministic mail logs)"
  run_seedops_playbook "${TMP_BASELINE_PLAYBOOK}" "${FB_BASELINE_JSON}" "${FALLBACK_DIR}/downloads_baseline"
  fallback_baseline_status="$(seed_json_status "${FB_BASELINE_JSON}")"
  if [[ "${fallback_baseline_status}" == "ok" ]]; then
    seed_assert_summary_job_terminal "${FB_BASELINE_JSON}"
  fi
  extract_mail_logs "${FB_BASELINE_JSON}" "mail_logs_before" "${MAIL_BEFORE}"
else
  seed_log_info "[S04] canonical mode: skip fallback baseline"
  echo "[canonical mode: fallback baseline skipped]" > "${MAIL_BEFORE}"
fi

gate_enabled=false
if [[ "${RISK}" == "on" && "${CONFIRM_TOKEN}" == "${GATE_TOKEN_EXPECTED}" ]]; then
  gate_enabled=true
fi

if [[ "${gate_enabled}" != "true" ]]; then
  seed_log_warn "[S04] Risk gate blocked experiment stage"
  cat > "${PRIMARY_EXPERIMENT}" <<EOF
{
  "status": "blocked",
  "errors": ["risk gate disabled or confirm token mismatch"],
  "warnings": [],
  "request_id": "gate-blocked"
}
EOF
  cp "${PRIMARY_EXPERIMENT}" "${PRIMARY_ROLLBACK}"
  echo "[blocked by risk gate]" > "${MAIL_DURING}"
  echo "[blocked by risk gate]" > "${MAIL_AFTER}"

  if [[ "${MODE}" == "fallback" ]]; then
    cp "${FB_BASELINE_JSON}" "${PRIMARY_BASELINE}"
  else
    cp "${CAN_BASELINE_JSON}" "${PRIMARY_BASELINE}"
  fi

  cat > "${REPORT_MD}" <<EOF
# S04 Experiment Report

- baseline_status: \`${canonical_baseline_status}\` (canonical) / \`${fallback_baseline_status}\` (fallback)
- experiment_stage: blocked by risk gate
- rollback_stage: blocked by risk gate
EOF
  exit 3
fi

# Experiment + rollback stages
if [[ "${MODE}" == "canonical" || "${MODE}" == "both" ]]; then
  seed_log_info "[S04] canonical policy precheck + experiment + rollback"
  run_seed_agent_policy_check "tc qdisc add dev eth0 root netem loss 25%" "net_ops" "${CAN_POLICY_JSON}"
  run_seed_agent "${EXPERIMENT_REQUEST}" "net_ops" "${CAN_EXPERIMENT_JSON}"
  run_seed_agent "${ROLLBACK_REQUEST}" "net_ops" "${CAN_ROLLBACK_JSON}"
  canonical_experiment_status="$(seed_json_status "${CAN_EXPERIMENT_JSON}")"
  canonical_rollback_status="$(seed_json_status "${CAN_ROLLBACK_JSON}")"
  if [[ "${canonical_experiment_status}" == "ok" && "${SEED_AGENT_FOLLOW_JOB}" == "1" ]]; then
    seed_assert_summary_job_terminal "${CAN_EXPERIMENT_JSON}"
  fi
  if [[ "${canonical_rollback_status}" == "ok" && "${SEED_AGENT_FOLLOW_JOB}" == "1" ]]; then
    seed_assert_summary_job_terminal "${CAN_ROLLBACK_JSON}"
  fi
fi

if [[ "${MODE}" == "fallback" || "${MODE}" == "both" ]]; then
  seed_log_info "[S04] fallback experiment + rollback (for deterministic logs/evidence)"
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

  extract_mail_logs "${FB_EXPERIMENT_JSON}" "mail_logs_during" "${MAIL_DURING}"
  extract_mail_logs "${FB_ROLLBACK_JSON}" "mail_logs_after" "${MAIL_AFTER}"
else
  seed_log_info "[S04] canonical mode: skip fallback experiment/rollback"
  echo "[canonical mode: fallback experiment skipped]" > "${MAIL_DURING}"
  echo "[canonical mode: fallback rollback skipped]" > "${MAIL_AFTER}"
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
"${pybin}" - "${PRIMARY_BASELINE}" "${PRIMARY_EXPERIMENT}" "${PRIMARY_ROLLBACK}" "${REPORT_MD}" "${MAIL_BEFORE}" "${MAIL_DURING}" "${MAIL_AFTER}" <<'PY'
import json
import sys
from pathlib import Path

baseline = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
experiment = json.loads(Path(sys.argv[2]).read_text(encoding="utf-8"))
rollback = json.loads(Path(sys.argv[3]).read_text(encoding="utf-8"))
report_path = Path(sys.argv[4])
mail_before = Path(sys.argv[5]).read_text(encoding="utf-8").strip()
mail_during = Path(sys.argv[6]).read_text(encoding="utf-8").strip()
mail_after = Path(sys.argv[7]).read_text(encoding="utf-8").strip()

def job_status(payload):
    summary = payload.get("summary", {})
    if isinstance(summary, dict) and summary.get("job_status"):
        return summary.get("job_status")
    return ((payload.get("job") or {}).get("final") or {}).get("job", {}).get("status", "")

rollback_has_reset = "reset" in json.dumps(rollback, ensure_ascii=False).lower()

lines = [
    "# S04 Experiment Report",
    "",
    f"- baseline.status: `{baseline.get('status', 'error')}`",
    f"- baseline.job_status: `{job_status(baseline)}`",
    f"- experiment.status: `{experiment.get('status', 'error')}`",
    f"- experiment.job_status: `{job_status(experiment)}`",
    f"- rollback.status: `{rollback.get('status', 'error')}`",
    f"- rollback.job_status: `{job_status(rollback)}`",
    f"- rollback_contains_reset: `{rollback_has_reset}`",
    "",
    "## Mail Logs Snapshot",
    "",
    f"- before_chars: `{len(mail_before)}`",
    f"- during_chars: `{len(mail_during)}`",
    f"- after_chars: `{len(mail_after)}`",
]
report_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
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

final_code="${canonical_code}"
if [[ "${MODE}" == "fallback" ]]; then
  final_code="${fallback_code}"
elif [[ "${MODE}" == "both" ]]; then
  if [[ "${fallback_code}" -gt "${final_code}" ]]; then
    final_code="${fallback_code}"
  fi
fi

seed_log_info "[S04] completed with exit_code=${final_code}, run_dir=${RUN_DIR}"
exit "${final_code}"
