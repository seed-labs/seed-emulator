#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${SCRIPT_DIR}/_common/env.sh"

TASK_ID=""
OBJECTIVE=""
WORKSPACE_NAME="lab1"
ATTACH_OUTPUT_DIR=""
ATTACH_NAME_REGEX=""
CONTEXT_JSON="{}"
ANSWERS_JSON="{}"
RISK="off"
CONFIRM_TOKEN="YES_RUN_DYNAMIC_FAULTS"
WORK_DIR="/tmp/seed-agent-mission-demo"

usage() {
  cat <<'EOF'
Usage: examples/agent-missions/run_task_demo.sh [options]

Options:
  --task <id>                  Required mission task_id
  --objective <text>           Required objective
  --workspace-name <name>      Default: lab1
  --attach-output-dir <path>   Optional attach output directory
  --attach-name-regex <regex>  Optional label attach regex
  --context-json <json>        Optional begin context JSON object
  --answers-json <json>        Optional extra answers for reply stage
  --risk on|off                Enable risky execution with confirmation token
  --confirm-token <token>      Default: YES_RUN_DYNAMIC_FAULTS
  --work-dir <path>            Default: /tmp/seed-agent-mission-demo
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --task) TASK_ID="${2:-}"; shift 2 ;;
    --objective) OBJECTIVE="${2:-}"; shift 2 ;;
    --workspace-name) WORKSPACE_NAME="${2:-lab1}"; shift 2 ;;
    --attach-output-dir) ATTACH_OUTPUT_DIR="${2:-}"; shift 2 ;;
    --attach-name-regex) ATTACH_NAME_REGEX="${2:-}"; shift 2 ;;
    --context-json)
      CONTEXT_JSON="${2:-}"
      if [[ -z "${CONTEXT_JSON}" ]]; then
        CONTEXT_JSON="{}"
      fi
      shift 2
      ;;
    --answers-json)
      ANSWERS_JSON="${2:-}"
      if [[ -z "${ANSWERS_JSON}" ]]; then
        ANSWERS_JSON="{}"
      fi
      shift 2
      ;;
    --risk) RISK="${2:-off}"; shift 2 ;;
    --confirm-token) CONFIRM_TOKEN="${2:-YES_RUN_DYNAMIC_FAULTS}"; shift 2 ;;
    --work-dir) WORK_DIR="${2:-/tmp/seed-agent-mission-demo}"; shift 2 ;;
    -h|--help) usage; exit 0 ;;
    *)
      echo "Unknown argument: $1" >&2
      usage
      exit 2
      ;;
  esac
done

if [[ -z "${TASK_ID}" || -z "${OBJECTIVE}" ]]; then
  echo "--task and --objective are required" >&2
  exit 2
fi

case "${RISK}" in
  on|off) ;;
  *)
    echo "--risk must be on|off" >&2
    exit 2
    ;;
esac

mission_require_cmd python
mission_require_env SEED_AGENT_MCP_URL
mission_require_env SEED_AGENT_MCP_TOKEN

if [[ -z "${ATTACH_OUTPUT_DIR}" ]]; then
  ATTACH_OUTPUT_DIR="$(mission_resolve_output_dir "${TASK_ID}")"
else
  ATTACH_OUTPUT_DIR="$(mission_abs_path "${ATTACH_OUTPUT_DIR}" "${SEED_EMAIL_ROOT}")"
fi

TS="$(date -u +%Y%m%dT%H%M%SZ)"
RUN_DIR="${WORK_DIR}/${TASK_ID}/${TS}"
mkdir -p "${RUN_DIR}"

BEGIN_JSON="${RUN_DIR}/begin.json"
REPLY_JSON="${RUN_DIR}/reply.json"
EXECUTE_JSON="${RUN_DIR}/execute.json"
STATUS_JSON="${RUN_DIR}/status.json"
SUMMARY_JSON="${RUN_DIR}/summary.json"

python "${SCRIPT_DIR}/_common/invoke_task_api.py" begin \
  --url "${SEED_AGENT_MCP_URL}" \
  --token "${SEED_AGENT_MCP_TOKEN}" \
  --task-id "${TASK_ID}" \
  --objective "${OBJECTIVE}" \
  --workspace-name "${WORKSPACE_NAME}" \
  --attach-output-dir "${ATTACH_OUTPUT_DIR}" \
  --attach-name-regex "${ATTACH_NAME_REGEX}" \
  --context-json "${CONTEXT_JSON}" | tee "${BEGIN_JSON}" >/dev/null

SESSION_ID="$(python - "${BEGIN_JSON}" <<'PY'
import json, sys
obj = json.load(open(sys.argv[1], "r", encoding="utf-8"))
print(((obj.get("session") or {}).get("session_id")) or "")
PY
)"
STATUS="$(python - "${BEGIN_JSON}" <<'PY'
import json, sys
obj = json.load(open(sys.argv[1], "r", encoding="utf-8"))
print(obj.get("status") or "")
PY
)"

if [[ -z "${SESSION_ID}" ]]; then
  echo "Missing session_id from begin response" >&2
  exit 1
fi

if [[ "${STATUS}" == "needs_input" ]]; then
  REPLY_PAYLOAD="$(python - "${ATTACH_OUTPUT_DIR}" "${ANSWERS_JSON}" <<'PY'
import json
import sys

attach_output_dir = sys.argv[1]
answers_json = sys.argv[2]
payload = {"attach_output_dir": attach_output_dir}
try:
    extra = json.loads(answers_json)
    if isinstance(extra, dict):
        payload.update(extra)
except Exception:
    pass
print(json.dumps(payload, ensure_ascii=False))
PY
)"
  python "${SCRIPT_DIR}/_common/invoke_task_api.py" reply \
    --url "${SEED_AGENT_MCP_URL}" \
    --token "${SEED_AGENT_MCP_TOKEN}" \
    --session-id "${SESSION_ID}" \
    --answers-json "${REPLY_PAYLOAD}" | tee "${REPLY_JSON}" >/dev/null
  STATUS="$(python - "${REPLY_JSON}" <<'PY'
import json, sys
obj = json.load(open(sys.argv[1], "r", encoding="utf-8"))
print(obj.get("status") or "")
PY
)"
fi

APPROVAL=""
if [[ "${STATUS}" == "awaiting_confirmation" ]]; then
  if [[ "${RISK}" != "on" ]]; then
    echo "Task is awaiting confirmation. Re-run with --risk on --confirm-token ${CONFIRM_TOKEN}" >&2
    exit 3
  fi
  APPROVAL="${CONFIRM_TOKEN}"
fi

python "${SCRIPT_DIR}/_common/invoke_task_api.py" execute \
  --url "${SEED_AGENT_MCP_URL}" \
  --token "${SEED_AGENT_MCP_TOKEN}" \
  --session-id "${SESSION_ID}" \
  ${APPROVAL:+--approval-token "${APPROVAL}"} \
  --follow-job \
  --no-download-artifacts \
  --artifacts-dir "${RUN_DIR}/artifacts" | tee "${EXECUTE_JSON}" >/dev/null

python "${SCRIPT_DIR}/_common/invoke_task_api.py" status \
  --url "${SEED_AGENT_MCP_URL}" \
  --token "${SEED_AGENT_MCP_TOKEN}" \
  --session-id "${SESSION_ID}" | tee "${STATUS_JSON}" >/dev/null

python - "${BEGIN_JSON}" "${REPLY_JSON}" "${EXECUTE_JSON}" "${STATUS_JSON}" "${SUMMARY_JSON}" "${RUN_DIR}" <<'PY'
import json
import pathlib
import sys

begin_path, reply_path, execute_path, status_path, out_path, run_dir = sys.argv[1:7]

def read(path):
    p = pathlib.Path(path)
    if not p.exists():
        return {}
    return json.loads(p.read_text(encoding="utf-8"))

begin = read(begin_path)
reply = read(reply_path)
execute = read(execute_path)
status = read(status_path)

summary = {
    "run_dir": run_dir,
    "session_id": ((begin.get("session") or {}).get("session_id")) or "",
    "begin_status": begin.get("status"),
    "reply_status": reply.get("status"),
    "execute_status": execute.get("status"),
    "task_status": status.get("status"),
    "job_id": (((execute.get("execution") or {}).get("summary") or {}).get("job_id")),
    "job_status": (((execute.get("execution") or {}).get("summary") or {}).get("job_status")),
    "scenario_class": (((status.get("report_summary") or {}).get("scenario_class")) or ""),
    "planner_mode": ((((execute.get("execution") or {}).get("compiled_plan") or {}).get("planner_mode")) or ""),
    "scale_hint": (((execute.get("execution") or {}).get("summary") or {}).get("scale_hint")),
    "selected_scope": (((execute.get("execution") or {}).get("summary") or {}).get("selected_scope")),
    "action_count": (((execute.get("execution") or {}).get("summary") or {}).get("action_count")),
    "risky_action_count": (((execute.get("execution") or {}).get("summary") or {}).get("risky_action_count")),
    "rollback_status": (((execute.get("execution") or {}).get("summary") or {}).get("rollback_status")),
    "verification_status": (((execute.get("execution") or {}).get("summary") or {}).get("verification_status")),
    "artifact_count": (((execute.get("execution") or {}).get("summary") or {}).get("artifact_count")),
    "latency_seconds": (((execute.get("execution") or {}).get("summary") or {}).get("latency_seconds")),
    "unresolved_issues": (((status.get("report_summary") or {}).get("unresolved_issues")) or []),
    "manual_review": {
        "objective_understanding": None,
        "environment_awareness": None,
        "scope_choice_quality": None,
        "evidence_conclusion_consistency": None,
        "unnecessary_action_rate": None,
        "reviewer_notes": "",
    },
}
pathlib.Path(out_path).write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")
print(json.dumps(summary, indent=2, ensure_ascii=False))
PY

FINAL_STATUS="$(python - "${EXECUTE_JSON}" <<'PY'
import json, sys
obj = json.load(open(sys.argv[1], "r", encoding="utf-8"))
print(obj.get("status") or "")
PY
)"

case "${FINAL_STATUS}" in
  ok) exit 0 ;;
  needs_input) exit 2 ;;
  awaiting_confirmation|blocked) exit 3 ;;
  upstream_error|timeout) exit 4 ;;
  *) exit 1 ;;
esac
