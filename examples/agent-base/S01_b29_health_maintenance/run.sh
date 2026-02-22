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

SCENARIO_ID="S01_b29_health_maintenance"
BASELINE="B29"
DEFAULT_POLICY="read_only"
WORKSPACE_NAME="lab1"
PLAYBOOK_FILE="${THIS_DIR}/playbook.fallback.yaml"
REQUEST_TEMPLATE="Attach to \${B29_OUTPUT_DIR}; focus on ASN 200/201 only; refresh inventory; summarize BGP on border/router nodes; collect minimal operational logs; return anomalies and next actions."

MODE="both"
POLICY="${DEFAULT_POLICY}"
OUTPUT_DIR_OVERRIDE=""
ARTIFACTS_ROOT="${THIS_DIR}/artifacts"
FALLBACK_TIMEOUT_SECONDS="${FALLBACK_TIMEOUT_SECONDS:-1200}"
SEED_AGENT_FOLLOW_JOB="${SEED_AGENT_FOLLOW_JOB:-1}"

usage() {
  cat <<'EOF'
Usage: S01_b29_health_maintenance/run.sh [options]

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
seed_ensure_dir "${CANONICAL_DIR}"
seed_ensure_dir "${FALLBACK_DIR}"

CANONICAL_JSON="${CANONICAL_DIR}/response.canonical.json"
CANONICAL_STEPS="${CANONICAL_DIR}/job.steps.json"
CANONICAL_ARTS="${CANONICAL_DIR}/artifacts.list.json"
CANONICAL_SUMMARY="${CANONICAL_DIR}/summary.md"

FALLBACK_JSON="${FALLBACK_DIR}/response.fallback.json"
FALLBACK_SUMMARY="${FALLBACK_DIR}/summary.md"

canonical_status="ok"
fallback_status="ok"

render_common_outputs() {
  local source_json="$1"
  local out_response="$2"
  local out_steps="$3"
  local out_arts="$4"
  local out_summary="$5"
  local pybin
  pybin="$(seed_python_bin)"
  "$pybin" - "$source_json" "$out_response" "$out_steps" "$out_arts" "$out_summary" <<'PY'
import json
import sys
from pathlib import Path

src = Path(sys.argv[1])
resp_out = Path(sys.argv[2])
steps_out = Path(sys.argv[3])
arts_out = Path(sys.argv[4])
summary_out = Path(sys.argv[5])

with src.open("r", encoding="utf-8") as f:
    data = json.load(f)

resp_out.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

steps = data.get("job", {}).get("steps", {})
steps_out.write_text(json.dumps(steps, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

arts = data.get("artifacts", {}).get("list", {})
arts_out.write_text(json.dumps(arts, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

summary = data.get("summary", {})
status = data.get("status", "error")
job_status = summary.get("job_status", "")
artifact_count = summary.get("artifact_count", 0)
lines = [
    "# S01 Summary",
    "",
    f"- status: `{status}`",
    f"- job_status: `{job_status}`",
    f"- artifact_count: `{artifact_count}`",
    f"- workspace_id: `{summary.get('workspace_id', '')}`",
    f"- job_id: `{summary.get('job_id', '')}`",
]
summary_out.write_text("\n".join(lines) + "\n", encoding="utf-8")
PY
}

run_canonical() {
  seed_log_info "[S01] Running canonical seed_agent_run"
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
    --request "${REQUEST_TEMPLATE}" \
    --workspace-name "${WORKSPACE_NAME}" \
    --attach-output-dir "${OUTPUT_DIR}" \
    --policy-profile "${POLICY}" \
    "${follow_args[@]}" \
    --no-download-artifacts \
    --artifacts-dir "${CANONICAL_DIR}/downloads" \
    > "${CANONICAL_JSON}"

  canonical_status="$(seed_json_status "${CANONICAL_JSON}")"
  render_common_outputs "${CANONICAL_JSON}" "${CANONICAL_JSON}" "${CANONICAL_STEPS}" "${CANONICAL_ARTS}" "${CANONICAL_SUMMARY}"

  if [[ "${canonical_status}" == "ok" ]]; then
    seed_assert_policy_allowed "${CANONICAL_JSON}"
    if [[ "${SEED_AGENT_FOLLOW_JOB}" == "1" ]]; then
      seed_assert_summary_job_terminal "${CANONICAL_JSON}"
      seed_assert_artifact_count_ge "${CANONICAL_JSON}" 1
    fi
  fi
}

run_fallback() {
  seed_log_info "[S01] Running fallback seedops playbook"
  local pybin
  pybin="$(seed_python_bin)"
  "${pybin}" "${COMMON_DIR}/invoke_seedops_fallback.py" run-playbook-flow \
    --url "${SEEDOPS_MCP_URL}" \
    --token "${SEEDOPS_MCP_TOKEN:-${SEED_MCP_TOKEN:-}}" \
    --workspace-name "${WORKSPACE_NAME}" \
    --output-dir "${OUTPUT_DIR}" \
    --playbook-file "${PLAYBOOK_FILE}" \
    --timeout-seconds "${FALLBACK_TIMEOUT_SECONDS}" \
    --download-artifacts \
    --artifacts-dir "${FALLBACK_DIR}/downloads" \
    > "${FALLBACK_JSON}"

  fallback_status="$(seed_json_status "${FALLBACK_JSON}")"
  local pybin_local
  pybin_local="$(seed_python_bin)"
  "${pybin_local}" - "${FALLBACK_JSON}" "${FALLBACK_SUMMARY}" <<'PY'
import json
import sys
from pathlib import Path

data = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
summary_path = Path(sys.argv[2])
summary = data.get("summary", {})
lines = [
    "# S01 Fallback Summary",
    "",
    f"- status: `{data.get('status', 'error')}`",
    f"- job_status: `{summary.get('job_status', '')}`",
    f"- artifact_count: `{summary.get('artifact_count', 0)}`",
    f"- downloaded_count: `{summary.get('downloaded_count', 0)}`",
]
summary_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
PY

  if [[ "${fallback_status}" == "ok" ]]; then
    seed_assert_summary_job_terminal "${FALLBACK_JSON}"
    seed_assert_artifact_count_ge "${FALLBACK_JSON}" 1
  fi
}

if [[ "${MODE}" == "canonical" || "${MODE}" == "both" ]]; then
  run_canonical
fi

if [[ "${MODE}" == "fallback" || "${MODE}" == "both" ]]; then
  run_fallback
fi

if [[ "${MODE}" == "both" ]]; then
  seed_assert_status_consistent "${CANONICAL_JSON}" "${FALLBACK_JSON}"
fi

PRIMARY_JSON="${CANONICAL_JSON}"
if [[ "${MODE}" == "fallback" ]]; then
  PRIMARY_JSON="${FALLBACK_JSON}"
fi

if [[ ! -f "${CANONICAL_JSON}" && -f "${FALLBACK_JSON}" ]]; then
  cp "${FALLBACK_JSON}" "${CANONICAL_JSON}"
fi

render_common_outputs "${PRIMARY_JSON}" "${RUN_DIR}/response.canonical.json" "${RUN_DIR}/job.steps.json" "${RUN_DIR}/artifacts.list.json" "${RUN_DIR}/summary.md"

final_code="$(seed_resolve_mode_exit_code "${MODE}" "${canonical_status}" "${fallback_status}")"
seed_log_info "[S01] completed with exit_code=${final_code}, run_dir=${RUN_DIR}"
exit "${final_code}"
