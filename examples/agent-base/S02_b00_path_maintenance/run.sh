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

SCENARIO_ID="S02_b00_path_maintenance"
BASELINE="B00"
DEFAULT_POLICY="read_only"
WORKSPACE_NAME="lab1"
PLAYBOOK_FILE="${THIS_DIR}/playbook.fallback.yaml"
REQUEST_TEMPLATE="Attach to \${B00_OUTPUT_DIR}; collect BGP summary, route snapshots, and traceroute diagnostics for router groups; identify probable path breakpoints."

MODE="both"
POLICY="${DEFAULT_POLICY}"
OUTPUT_DIR_OVERRIDE=""
ARTIFACTS_ROOT="${THIS_DIR}/artifacts"

usage() {
  cat <<'EOF'
Usage: S02_b00_path_maintenance/run.sh [options]

Options:
  --mode canonical|fallback|both
  --policy read_only|net_ops|danger
  --output-dir <path>
  --artifacts-root <path>
  --risk on|off                 (ignored for maintenance)
  --confirm-token <token>       (ignored for maintenance)
  -h, --help
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --mode) MODE="${2:-}"; shift 2 ;;
    --policy) POLICY="${2:-}"; shift 2 ;;
    --output-dir) OUTPUT_DIR_OVERRIDE="${2:-}"; shift 2 ;;
    --artifacts-root) ARTIFACTS_ROOT="${2:-}"; shift 2 ;;
    --risk) shift 2 ;;
    --confirm-token) shift 2 ;;
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
DIAG_DIR="${RUN_DIR}/diagnostics"
seed_ensure_dir "${CANONICAL_DIR}"
seed_ensure_dir "${FALLBACK_DIR}"
seed_ensure_dir "${DIAG_DIR}"

PLAN_JSON="${CANONICAL_DIR}/plan.json"
RUN_JSON="${CANONICAL_DIR}/run.json"
FALLBACK_JSON="${FALLBACK_DIR}/response.fallback.json"
ROUTES_TXT="${DIAG_DIR}/routes.txt"
TRACE_TXT="${DIAG_DIR}/trace.txt"

plan_status="ok"
canonical_status="ok"
fallback_status="ok"

run_canonical() {
  seed_log_info "[S02] Running canonical plan + run"
  local pybin
  pybin="$(seed_python_bin)"
  B00_OUTPUT_DIR="${OUTPUT_DIR}" \
  "${pybin}" "${COMMON_DIR}/invoke_seed_agent.py" plan \
    --url "${SEED_AGENT_MCP_URL}" \
    --token "${SEED_AGENT_MCP_TOKEN:-}" \
    --request "${REQUEST_TEMPLATE}" \
    --workspace-name "${WORKSPACE_NAME}" \
    --attach-output-dir "${OUTPUT_DIR}" \
    --policy-profile "${POLICY}" \
    > "${PLAN_JSON}"

  plan_status="$(seed_json_status "${PLAN_JSON}")"
  if [[ "${plan_status}" != "ok" ]]; then
    canonical_status="${plan_status}"
    cp "${PLAN_JSON}" "${RUN_JSON}"
    return 0
  fi

  B00_OUTPUT_DIR="${OUTPUT_DIR}" \
  "${pybin}" "${COMMON_DIR}/invoke_seed_agent.py" run \
    --url "${SEED_AGENT_MCP_URL}" \
    --token "${SEED_AGENT_MCP_TOKEN:-}" \
    --request "${REQUEST_TEMPLATE}" \
    --workspace-name "${WORKSPACE_NAME}" \
    --attach-output-dir "${OUTPUT_DIR}" \
    --policy-profile "${POLICY}" \
    --follow-job \
    --download-artifacts \
    --artifacts-dir "${CANONICAL_DIR}/downloads" \
    > "${RUN_JSON}"

  canonical_status="$(seed_json_status "${RUN_JSON}")"
  if [[ "${canonical_status}" == "ok" ]]; then
    seed_assert_summary_job_terminal "${RUN_JSON}"
    seed_assert_field_nonempty "${RUN_JSON}" "summary.workspace_id"
    seed_assert_field_nonempty "${RUN_JSON}" "summary.job_id"
  fi
}

run_fallback() {
  seed_log_info "[S02] Running fallback playbook"
  local pybin
  pybin="$(seed_python_bin)"
  "${pybin}" "${COMMON_DIR}/invoke_seedops_fallback.py" run-playbook-flow \
    --url "${SEEDOPS_MCP_URL}" \
    --token "${SEEDOPS_MCP_TOKEN:-${SEED_MCP_TOKEN:-}}" \
    --workspace-name "${WORKSPACE_NAME}" \
    --output-dir "${OUTPUT_DIR}" \
    --playbook-file "${PLAYBOOK_FILE}" \
    --download-artifacts \
    --artifacts-dir "${FALLBACK_DIR}/downloads" \
    > "${FALLBACK_JSON}"

  fallback_status="$(seed_json_status "${FALLBACK_JSON}")"
  if [[ "${fallback_status}" == "ok" ]]; then
    seed_assert_summary_job_terminal "${FALLBACK_JSON}"
    seed_assert_field_nonempty "${FALLBACK_JSON}" "summary.workspace_id"
    seed_assert_field_nonempty "${FALLBACK_JSON}" "summary.job_id"
  fi
}

extract_diagnostics_from_fallback() {
  if [[ ! -f "${FALLBACK_JSON}" ]]; then
    return 1
  fi
  local pybin
  pybin="$(seed_python_bin)"
  "${pybin}" - "${FALLBACK_JSON}" "${ROUTES_TXT}" "${TRACE_TXT}" <<'PY'
import json
import sys
from pathlib import Path

data = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
routes_path = Path(sys.argv[2])
trace_path = Path(sys.argv[3])

artifacts = data.get("artifacts", {}).get("list", {}).get("artifacts", []) or []
downloaded = data.get("artifacts", {}).get("downloaded", []) or []
name_by_id = {}
for row in artifacts:
    if isinstance(row, dict):
        aid = str(row.get("artifact_id") or "")
        if aid:
            name_by_id[aid] = str(row.get("name") or "")

def collect_outputs(obj):
    outputs = []
    if isinstance(obj, dict):
        if isinstance(obj.get("results"), list):
            for row in obj["results"]:
                if isinstance(row, dict):
                    text = row.get("output")
                    if isinstance(text, str) and text.strip():
                        outputs.append(text.strip())
        for v in obj.values():
            outputs.extend(collect_outputs(v))
    elif isinstance(obj, list):
        for item in obj:
            outputs.extend(collect_outputs(item))
    return outputs

routes_text = ""
trace_text = ""

for row in downloaded:
    if not isinstance(row, dict):
        continue
    aid = str(row.get("artifact_id") or "")
    name = name_by_id.get(aid, "")
    out_path = Path(str(row.get("out_path") or ""))
    if not out_path.exists():
        continue
    try:
        content = json.loads(out_path.read_text(encoding="utf-8"))
    except Exception:
        continue
    outputs = collect_outputs(content)
    merged = "\n\n".join(outputs).strip()
    if not merged:
        continue
    lower_name = name.lower()
    if "route" in lower_name:
        routes_text = merged
    if "trace" in lower_name:
        trace_text = merged

if not routes_text:
    routes_text = "[no route output extracted from fallback artifacts]"
if not trace_text:
    trace_text = "[no traceroute output extracted from fallback artifacts]"

routes_path.write_text(routes_text + "\n", encoding="utf-8")
trace_path.write_text(trace_text + "\n", encoding="utf-8")
PY
}

if [[ "${MODE}" == "canonical" || "${MODE}" == "both" ]]; then
  run_canonical
fi

if [[ "${MODE}" == "fallback" || "${MODE}" == "both" ]]; then
  run_fallback
fi

# Ensure diagnostics are always generated from deterministic low-level data.
if [[ "${MODE}" == "canonical" && ! -f "${FALLBACK_JSON}" ]]; then
  run_fallback
fi

extract_diagnostics_from_fallback

if [[ "${MODE}" == "both" ]]; then
  seed_assert_status_consistent "${RUN_JSON}" "${FALLBACK_JSON}"
fi

if [[ ! -f "${PLAN_JSON}" ]]; then
  cat > "${PLAN_JSON}" <<EOF
{
  "status": "${fallback_status}",
  "warnings": ["Canonical planning was not executed in fallback-only mode."],
  "errors": []
}
EOF
fi

PRIMARY_RUN_JSON="${RUN_JSON}"
if [[ "${MODE}" == "fallback" ]]; then
  PRIMARY_RUN_JSON="${FALLBACK_JSON}"
fi

cp "${PLAN_JSON}" "${RUN_DIR}/plan.json"
cp "${PRIMARY_RUN_JSON}" "${RUN_DIR}/run.json"
# diagnostics files are already generated in ${RUN_DIR}/diagnostics/

final_code="$(seed_resolve_mode_exit_code "${MODE}" "${canonical_status}" "${fallback_status}")"
seed_log_info "[S02] completed with exit_code=${final_code}, run_dir=${RUN_DIR}"
exit "${final_code}"
