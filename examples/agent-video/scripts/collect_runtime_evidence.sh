#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VIDEO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
REPO_ROOT="$(cd "${VIDEO_ROOT}/../.." && pwd)"

WORK_DIR="/tmp/seed-agent-video-evidence"
TASK_ID="RS_B00_CONVERGENCE_COMPARISON"
OBJECTIVE="Compare convergence behavior"
RISK="off"
SEED_TOKEN="${SEED_TOKEN:-seed-local-token}"
KEEP_SERVICES=0

usage() {
  cat <<'EOF'
Usage: examples/agent-video/scripts/collect_runtime_evidence.sh [options]

Options:
  --work-dir <path>     Evidence work dir (default: /tmp/seed-agent-video-evidence)
  --task <id>           Task id (default: RS_B00_CONVERGENCE_COMPARISON)
  --objective <text>    Objective (default: Compare convergence behavior)
  --risk on|off         Also capture risk-gate evidence (default: off)
  --seed-token <token>  MCP bearer token for both SeedOps and Seed-Agent (default: seed-local-token)
  --keep-services       Do not stop services at script exit
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --work-dir) WORK_DIR="${2:-}"; shift 2 ;;
    --task) TASK_ID="${2:-}"; shift 2 ;;
    --objective) OBJECTIVE="${2:-}"; shift 2 ;;
    --risk) RISK="${2:-off}"; shift 2 ;;
    --seed-token) SEED_TOKEN="${2:-seed-local-token}"; shift 2 ;;
    --keep-services) KEEP_SERVICES=1; shift ;;
    -h|--help) usage; exit 0 ;;
    *) echo "Unknown arg: $1" >&2; usage; exit 2 ;;
  esac
done

case "${RISK}" in
  on|off) ;;
  *) echo "--risk must be on|off" >&2; exit 2 ;;
esac

EVID_DIR="${WORK_DIR}/run"
mkdir -p "${EVID_DIR}"

echo "[seed-video] Evidence work dir: ${EVID_DIR}"

if [[ ! -x "${REPO_ROOT}/examples/agent-missions/run_task_demo.sh" ]]; then
  echo "Missing: examples/agent-missions/run_task_demo.sh" >&2
  exit 2
fi

source "${REPO_ROOT}/examples/agent-missions/_common/env.sh"

if [[ ! -x "${SEED_AGENT_DIR}/scripts/seed-codex" ]]; then
  echo "Missing seed-codex: ${SEED_AGENT_DIR}/scripts/seed-codex" >&2
  exit 2
fi

cleanup() {
  if [[ "${KEEP_SERVICES}" -eq 0 ]]; then
    (
      cd "${SEED_AGENT_DIR}" && ./scripts/seed-codex down >/dev/null 2>&1
    ) || true
  fi
}
trap cleanup EXIT

export SEED_MCP_TOKEN="${SEED_MCP_TOKEN:-${SEED_TOKEN}}"
export SEED_AGENT_MCP_TOKEN="${SEED_AGENT_MCP_TOKEN:-${SEED_TOKEN}}"
export SEED_AGENT_MCP_URL="${SEED_AGENT_MCP_URL:-http://127.0.0.1:8100/mcp}"

(
  cd "${SEED_AGENT_DIR}" && ./scripts/seed-codex up >/dev/null
)

RUN_LOG="${EVID_DIR}/task_run.log"
SUMMARY_GLOB="${EVID_DIR}/summary.json"

set +e
(
  cd "${REPO_ROOT}"
  examples/agent-missions/run_task_demo.sh \
    --task "${TASK_ID}" \
    --objective "${OBJECTIVE}" \
    --work-dir "${EVID_DIR}" \
    --risk off \
    --context-json '{"comparison_target":"AS2-AS3"}'
) 2>&1 | tee "${RUN_LOG}"
RC=$?
set -e

if [[ "${RC}" -ne 0 ]]; then
  echo "[seed-video] task run failed with rc=${RC}" >&2
  exit "${RC}"
fi

LATEST_SUMMARY="$(ls -1 "${EVID_DIR}/${TASK_ID}/"*/summary.json 2>/dev/null | tail -n 1 || true)"
if [[ -z "${LATEST_SUMMARY}" ]]; then
  echo "Failed to locate summary.json under: ${EVID_DIR}/${TASK_ID}" >&2
  exit 1
fi

LATEST_RUN_DIR="$(python - "${LATEST_SUMMARY}" <<'PY'
import json, sys
obj = json.load(open(sys.argv[1], "r", encoding="utf-8"))
print(obj.get("run_dir") or "")
PY
)"
if [[ -z "${LATEST_RUN_DIR}" ]]; then
  echo "Missing run_dir in summary: ${LATEST_SUMMARY}" >&2
  exit 1
fi

READ_EXECUTE_JSON="${LATEST_RUN_DIR}/execute.json"
if [[ ! -f "${READ_EXECUTE_JSON}" ]]; then
  echo "Missing execute.json in run_dir: ${READ_EXECUTE_JSON}" >&2
  exit 1
fi

RISK_GATE_STATUS=""
if [[ "${RISK}" == "on" ]]; then
  RISK_TASK="RS_B29_FAULT_IMPACT_ABLATION"
  RISK_OBJECTIVE="Run controlled packet loss fault impact with rollback"
  RISK_ATTACH="$(mission_abs_path "${B29_OUTPUT_DIR}" "${SEED_EMAIL_ROOT}")"

  TS="$(date -u +%Y%m%dT%H%M%SZ)"
  RISK_DIR="${EVID_DIR}/${RISK_TASK}/${TS}"
  mkdir -p "${RISK_DIR}"
  RISK_BEGIN_JSON="${RISK_DIR}/begin.json"
  RISK_EXEC_JSON="${RISK_DIR}/execute.awaiting_confirmation.json"

  python "${REPO_ROOT}/examples/agent-missions/_common/invoke_task_api.py" begin \
    --url "${SEED_AGENT_MCP_URL}" \
    --token "${SEED_AGENT_MCP_TOKEN}" \
    --task-id "${RISK_TASK}" \
    --objective "${RISK_OBJECTIVE}" \
    --workspace-name "lab1" \
    --attach-output-dir "${RISK_ATTACH}" \
    --context-json '{"fault_target":"as150/router0","fault_type":"packet_loss"}' \
    | tee "${RISK_BEGIN_JSON}" >/dev/null

  RISK_SESSION_ID="$(python - "${RISK_BEGIN_JSON}" <<'PY'
import json, sys
obj = json.load(open(sys.argv[1], "r", encoding="utf-8"))
print(((obj.get("session") or {}).get("session_id")) or "")
PY
)"
  if [[ -z "${RISK_SESSION_ID}" ]]; then
    echo "Missing session_id from risk begin response: ${RISK_BEGIN_JSON}" >&2
    exit 1
  fi

  python "${REPO_ROOT}/examples/agent-missions/_common/invoke_task_api.py" execute \
    --url "${SEED_AGENT_MCP_URL}" \
    --token "${SEED_AGENT_MCP_TOKEN}" \
    --session-id "${RISK_SESSION_ID}" \
    --follow-job \
    --no-download-artifacts \
    --artifacts-dir "${RISK_DIR}/artifacts" \
    | tee "${RISK_EXEC_JSON}" >/dev/null

  RISK_GATE_STATUS="$(python - "${RISK_EXEC_JSON}" <<'PY'
import json, sys
obj = json.load(open(sys.argv[1], "r", encoding="utf-8"))
print(obj.get("status") or "")
PY
)"
fi

python - "${READ_EXECUTE_JSON}" "${VIDEO_ROOT}/assets/evidence/runtime_snapshot.json" "${RISK_GATE_STATUS}" <<'PY'
import json
import sys
from datetime import datetime, timezone

execute_path = sys.argv[1]
dst = sys.argv[2]
risk_gate_status = sys.argv[3] or None

execute = json.load(open(execute_path, "r", encoding="utf-8"))
session = execute.get("session") or {}
exec_refs = session.get("execution_refs") or {}

snapshot = {
    "generated_at_utc": datetime.now(timezone.utc).isoformat(),
    "source": execute_path,
    "task_id": session.get("task_id"),
    "objective": session.get("objective"),
    "session_id": session.get("session_id"),
    "begin_status": None,
    "execute_status": execute.get("status"),
    "task_status": (session.get("stage") == "done" and "ok") or None,
    "job_id": exec_refs.get("job_id"),
    "job_status": exec_refs.get("job_status"),
    "planner_mode": exec_refs.get("planner_mode"),
    "risk_gate_status": risk_gate_status,
    "notes": [
        "Collected by examples/agent-video/scripts/collect_runtime_evidence.sh",
        "This is a minimal snapshot for the 120s video overlay.",
    ],
}
open(dst, "w", encoding="utf-8").write(json.dumps(snapshot, indent=2, ensure_ascii=False))
print(dst)
PY

tail -n 80 "${RUN_LOG}" > "${VIDEO_ROOT}/assets/evidence/log_tail.txt" || true
{
  echo ""
  echo "---- seedagent_mcp log tail ----"
  tail -n 40 "${SEED_AGENT_DIR}/.run_logs/seedagent.log" 2>/dev/null || true
  echo ""
  echo "---- seedops_mcp log tail ----"
  tail -n 40 "${SEED_AGENT_DIR}/.run_logs/seedops.log" 2>/dev/null || true
} >> "${VIDEO_ROOT}/assets/evidence/log_tail.txt"

python - "${VIDEO_ROOT}/assets/evidence/log_tail.txt" "${VIDEO_ROOT}/assets/evidence/log_tail.json" <<'PY'
import json
import sys
from pathlib import Path

src = Path(sys.argv[1])
dst = Path(sys.argv[2])
lines = src.read_text(encoding="utf-8", errors="ignore").splitlines()
tail = lines[-30:]
dst.write_text(json.dumps({"lines": tail}, indent=2, ensure_ascii=False), encoding="utf-8")
print(dst)
PY

echo "[seed-video] Wrote:"
  echo "  - ${VIDEO_ROOT}/assets/evidence/runtime_snapshot.json"
echo "  - ${VIDEO_ROOT}/assets/evidence/log_tail.txt"
echo "  - ${VIDEO_ROOT}/assets/evidence/log_tail.json"
