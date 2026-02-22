#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${SCRIPT_DIR}/_common/env.sh"

WORK_DIR="${WORK_DIR:-examples/agent-missions/reports}"
SEED_TOKEN="${SEED_TOKEN:-seed-local-token}"
KEEP_SERVICES=0

usage() {
  cat <<'EOF'
Usage: examples/agent-missions/run_review_pack.sh [options]

Options:
  --work-dir <path>         Report output root (default: examples/agent-missions/reports)
  --seed-token <token>      MCP token used for both SeedOps and Seed-Agent (default: seed-local-token)
  --keep-services           Do not stop services at script exit
  -h, --help
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --work-dir) WORK_DIR="${2:-examples/agent-missions/reports}"; shift 2 ;;
    --seed-token) SEED_TOKEN="${2:-seed-local-token}"; shift 2 ;;
    --keep-services) KEEP_SERVICES=1; shift ;;
    -h|--help) usage; exit 0 ;;
    *)
      echo "Unknown argument: $1" >&2
      usage
      exit 2
      ;;
  esac
done

mission_require_cmd python
mission_require_cmd bash

if [[ ! -x "${SEED_AGENT_DIR}/scripts/seed-codex" ]]; then
  echo "seed-codex not found or not executable: ${SEED_AGENT_DIR}/scripts/seed-codex" >&2
  exit 2
fi

WORK_DIR_ABS="$(mission_abs_path "${WORK_DIR}" "${SEED_EMAIL_ROOT}")"
TS="$(date -u +%Y%m%dT%H%M%SZ)"
RUN_DIR="${WORK_DIR_ABS}/${TS}"
mkdir -p "${RUN_DIR}"

UP_LOG="${RUN_DIR}/seed-codex.up.log"
DOWN_LOG="${RUN_DIR}/seed-codex.down.log"

cleanup() {
  if [[ "${KEEP_SERVICES}" -eq 0 ]]; then
    (
      cd "${SEED_AGENT_DIR}" && ./scripts/seed-codex down >"${DOWN_LOG}" 2>&1
    ) || true
  fi
}
trap cleanup EXIT

export SEED_MCP_TOKEN="${SEED_MCP_TOKEN:-${SEED_TOKEN}}"
export SEED_AGENT_MCP_TOKEN="${SEED_AGENT_MCP_TOKEN:-${SEED_TOKEN}}"

(
  cd "${SEED_AGENT_DIR}" && ./scripts/seed-codex up >"${UP_LOG}" 2>&1
)

CATALOG_JSON="${RUN_DIR}/mission_catalog.json"
READ_START_JSON="${RUN_DIR}/read_only.start.json"
READ_EXEC_JSON="${RUN_DIR}/read_only.execute.json"
READ_STATUS_JSON="${RUN_DIR}/read_only.status.json"
RISK_START_JSON="${RUN_DIR}/risk.start.json"
RISK_EXEC_WAIT_JSON="${RUN_DIR}/risk.execute.awaiting_confirmation.json"
RISK_EXEC_OK_JSON="${RUN_DIR}/risk.execute.approved.json"
RISK_STATUS_JSON="${RUN_DIR}/risk.status.json"
SUMMARY_JSON="${RUN_DIR}/review_summary.json"
REPORT_MD="${RUN_DIR}/review_report.md"

(
  cd "${SEED_AGENT_DIR}" && ./scripts/seed-codex mission list > "${CATALOG_JSON}"
)

B00_ATTACH="$(mission_abs_path "${B00_OUTPUT_DIR}" "${SEED_EMAIL_ROOT}")"
B29_ATTACH="$(mission_abs_path "${B29_OUTPUT_DIR}" "${SEED_EMAIL_ROOT}")"

READ_CONTEXT_JSON="$(python - <<'PY'
import json
print(json.dumps({"comparison_target": "AS2-AS3"}))
PY
)"
(
  cd "${SEED_AGENT_DIR}" && ./scripts/seed-codex mission start \
    --task RS_B00_CONVERGENCE_COMPARISON \
    --objective "Compare convergence behavior for AS2-AS3" \
    --workspace-name lab1 \
    --attach-output-dir "${B00_ATTACH}" \
    --context-json "${READ_CONTEXT_JSON}" > "${READ_START_JSON}"
)

READ_SESSION_ID="$(python - "${READ_START_JSON}" <<'PY'
import json, sys
obj = json.load(open(sys.argv[1], "r", encoding="utf-8"))
print(((obj.get("session") or {}).get("session_id")) or "")
PY
)"
if [[ -z "${READ_SESSION_ID}" ]]; then
  echo "Failed to get read-only session id: ${READ_START_JSON}" >&2
  exit 1
fi

(
  cd "${SEED_AGENT_DIR}" && ./scripts/seed-codex mission execute \
    --session "${READ_SESSION_ID}" > "${READ_EXEC_JSON}"
)
(
  cd "${SEED_AGENT_DIR}" && ./scripts/seed-codex mission status \
    --session "${READ_SESSION_ID}" > "${READ_STATUS_JSON}"
)

RISK_CONTEXT_JSON="$(python - <<'PY'
import json
print(json.dumps({"fault_target": "as150/router0", "fault_type": "packet_loss"}))
PY
)"
(
  cd "${SEED_AGENT_DIR}" && ./scripts/seed-codex mission start \
    --task RS_B29_FAULT_IMPACT_ABLATION \
    --objective "Run controlled packet loss fault impact with rollback" \
    --workspace-name lab1 \
    --attach-output-dir "${B29_ATTACH}" \
    --context-json "${RISK_CONTEXT_JSON}" > "${RISK_START_JSON}"
)

RISK_SESSION_ID="$(python - "${RISK_START_JSON}" <<'PY'
import json, sys
obj = json.load(open(sys.argv[1], "r", encoding="utf-8"))
print(((obj.get("session") or {}).get("session_id")) or "")
PY
)"
if [[ -z "${RISK_SESSION_ID}" ]]; then
  echo "Failed to get risk session id: ${RISK_START_JSON}" >&2
  exit 1
fi

(
  cd "${SEED_AGENT_DIR}" && ./scripts/seed-codex mission execute \
    --session "${RISK_SESSION_ID}" > "${RISK_EXEC_WAIT_JSON}"
)
(
  cd "${SEED_AGENT_DIR}" && ./scripts/seed-codex mission execute \
    --session "${RISK_SESSION_ID}" \
    --approve YES_RUN_DYNAMIC_FAULTS > "${RISK_EXEC_OK_JSON}"
)
(
  cd "${SEED_AGENT_DIR}" && ./scripts/seed-codex mission status \
    --session "${RISK_SESSION_ID}" > "${RISK_STATUS_JSON}"
)

python - "${RUN_DIR}" "${SUMMARY_JSON}" "${REPORT_MD}" <<'PY'
import json
import pathlib
import sys
from datetime import datetime, timezone

run_dir = pathlib.Path(sys.argv[1])
summary_path = pathlib.Path(sys.argv[2])
report_path = pathlib.Path(sys.argv[3])

def read(name: str):
    p = run_dir / name
    if not p.exists():
        return {}
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return {}

catalog = read("mission_catalog.json")
read_start = read("read_only.start.json")
read_exec = read("read_only.execute.json")
read_status = read("read_only.status.json")
risk_start = read("risk.start.json")
risk_wait = read("risk.execute.awaiting_confirmation.json")
risk_exec = read("risk.execute.approved.json")
risk_status = read("risk.status.json")

def status(obj):
    return str(obj.get("status") or "")

def report_value(obj, *keys):
    cur = obj
    for key in keys:
        if not isinstance(cur, dict):
            return None
        cur = cur.get(key)
    return cur

summary = {
    "generated_at_utc": datetime.now(timezone.utc).isoformat(),
    "run_dir": str(run_dir),
    "catalog": {
        "status": status(catalog),
        "task_count": report_value(catalog, "report_summary", "task_count"),
    },
    "read_only_flow": {
        "session_id": report_value(read_start, "session", "session_id"),
        "start_status": status(read_start),
        "execute_status": status(read_exec),
        "status_status": status(read_status),
        "job_id": report_value(read_exec, "execution", "summary", "job_id"),
        "job_status": report_value(read_exec, "execution", "summary", "job_status"),
    },
    "risk_flow": {
        "session_id": report_value(risk_start, "session", "session_id"),
        "start_status": status(risk_start),
        "awaiting_confirmation_status": status(risk_wait),
        "approved_execute_status": status(risk_exec),
        "status_status": status(risk_status),
        "job_id": report_value(risk_exec, "execution", "summary", "job_id"),
        "job_status": report_value(risk_exec, "execution", "summary", "job_status"),
    },
}

summary["assertions"] = {
    "catalog_ok": summary["catalog"]["status"] == "ok" and int(summary["catalog"]["task_count"] or 0) >= 6,
    "read_only_ok": (
        summary["read_only_flow"]["start_status"] == "ok"
        and summary["read_only_flow"]["execute_status"] == "ok"
        and summary["read_only_flow"]["status_status"] == "ok"
    ),
    "risk_gate_ok": summary["risk_flow"]["awaiting_confirmation_status"] == "awaiting_confirmation",
    "risk_execute_ok": (
        summary["risk_flow"]["approved_execute_status"] == "ok"
        and summary["risk_flow"]["status_status"] == "ok"
    ),
}
summary["all_passed"] = all(summary["assertions"].values())

summary_path.write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")

lines = [
    "# Seed-Agent Mission Review Pack",
    "",
    f"- Generated (UTC): `{summary['generated_at_utc']}`",
    f"- Run dir: `{summary['run_dir']}`",
    "",
    "## Assertions",
    f"- catalog_ok: `{summary['assertions']['catalog_ok']}`",
    f"- read_only_ok: `{summary['assertions']['read_only_ok']}`",
    f"- risk_gate_ok: `{summary['assertions']['risk_gate_ok']}`",
    f"- risk_execute_ok: `{summary['assertions']['risk_execute_ok']}`",
    f"- all_passed: `{summary['all_passed']}`",
    "",
    "## Read-only mission (RS_B00_CONVERGENCE_COMPARISON)",
    f"- session_id: `{summary['read_only_flow']['session_id']}`",
    f"- start/execute/status: `{summary['read_only_flow']['start_status']}` / `{summary['read_only_flow']['execute_status']}` / `{summary['read_only_flow']['status_status']}`",
    f"- job: `{summary['read_only_flow']['job_id']}` (`{summary['read_only_flow']['job_status']}`)",
    "",
    "## Risk mission (RS_B29_FAULT_IMPACT_ABLATION)",
    f"- session_id: `{summary['risk_flow']['session_id']}`",
    f"- start status: `{summary['risk_flow']['start_status']}`",
    f"- execute without approval: `{summary['risk_flow']['awaiting_confirmation_status']}`",
    f"- execute with approval: `{summary['risk_flow']['approved_execute_status']}`",
    f"- final status call: `{summary['risk_flow']['status_status']}`",
    f"- job: `{summary['risk_flow']['job_id']}` (`{summary['risk_flow']['job_status']}`)",
    "",
    "## Raw JSON Evidence",
    "- `mission_catalog.json`",
    "- `read_only.start.json`",
    "- `read_only.execute.json`",
    "- `read_only.status.json`",
    "- `risk.start.json`",
    "- `risk.execute.awaiting_confirmation.json`",
    "- `risk.execute.approved.json`",
    "- `risk.status.json`",
    "- `review_summary.json`",
]
report_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
print(json.dumps(summary, indent=2, ensure_ascii=False))
PY

echo
echo "Review pack generated:"
echo "  ${RUN_DIR}"
echo "  ${SUMMARY_JSON}"
echo "  ${REPORT_MD}"

