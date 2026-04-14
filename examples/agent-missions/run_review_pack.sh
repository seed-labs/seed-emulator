#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${SCRIPT_DIR}/_common/env.sh"

WORK_DIR="${WORK_DIR:-examples/agent-missions/reports}"
SEED_TOKEN="${SEED_TOKEN:-seed-local-token}"
SEEDOPS_TOKEN="${SEEDOPS_TOKEN:-}"
SEEDAGENT_TOKEN="${SEEDAGENT_TOKEN:-}"
KEEP_SERVICES=0
MANAGE_RUNTIME=1
ROOT_SEED_CODEX="${SEED_EMAIL_ROOT}/scripts/seed-codex"

usage() {
  cat <<'EOF'
Usage: examples/agent-missions/run_review_pack.sh [options]

Options:
  --work-dir <path>         Report output root (default: examples/agent-missions/reports)
  --seed-token <token>      Shared fallback token if both MCP services use the same bearer token
  --seedops-token <token>   SeedOps MCP bearer token (overrides --seed-token)
  --seedagent-token <token> SeedAgent MCP bearer token (overrides --seed-token)
  --manage-runtime on|off   Sequentially down/up compose targets before grouped tasks (default: on)
  --keep-services           Do not stop services at script exit
  -h, --help
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --work-dir) WORK_DIR="${2:-examples/agent-missions/reports}"; shift 2 ;;
    --seed-token) SEED_TOKEN="${2:-seed-local-token}"; shift 2 ;;
    --seedops-token) SEEDOPS_TOKEN="${2:-}"; shift 2 ;;
    --seedagent-token) SEEDAGENT_TOKEN="${2:-}"; shift 2 ;;
    --manage-runtime)
      case "${2:-on}" in
        on) MANAGE_RUNTIME=1 ;;
        off) MANAGE_RUNTIME=0 ;;
        *) echo "--manage-runtime must be on|off" >&2; exit 2 ;;
      esac
      shift 2
      ;;
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

if [[ ! -x "${ROOT_SEED_CODEX}" ]]; then
  echo "repo-root seed-codex not found or not executable: ${ROOT_SEED_CODEX}" >&2
  exit 2
fi

WORK_DIR_ABS="$(mission_abs_path "${WORK_DIR}" "${SEED_EMAIL_ROOT}")"
TS="$(date -u +%Y%m%dT%H%M%SZ)"
RUN_DIR="${WORK_DIR_ABS}/${TS}"
mkdir -p "${RUN_DIR}"

UP_LOG="${RUN_DIR}/seed-codex.up.log"
DOWN_LOG="${RUN_DIR}/seed-codex.down.log"
CONTROL_LOG="${RUN_DIR}/seed-codex.control.log"
SUMMARY_JSON="${RUN_DIR}/review_summary.json"
REPORT_MD="${RUN_DIR}/review_report.md"
CURRENT_RUNTIME_ATTACH_DIR=""

runtime_key() {
  python - "$1" <<'PY'
import re
import sys
text = sys.argv[1]
print(re.sub(r'[^A-Za-z0-9._-]+', '_', text).strip('_') or 'runtime')
PY
}

collect_managed_conflicts() {
  local attach_dir="$1"
  python - "${SEED_EMAIL_ROOT}" "${attach_dir}" <<'PY'
import os
import re
import subprocess
import sys

repo_root = os.path.abspath(sys.argv[1])
attach_dir = os.path.abspath(sys.argv[2])
cmd = [
    "docker",
    "ps",
    "--format",
    "{{.Names}}\t{{.Label \"com.docker.compose.project\"}}\t{{.Label \"com.docker.compose.project.working_dir\"}}\t{{.Label \"com.docker.compose.project.config_files\"}}",
]
proc = subprocess.run(cmd, text=True, capture_output=True, check=False)
if proc.returncode != 0:
    raise SystemExit(0)

groups = {}
for raw_line in proc.stdout.splitlines():
    if not raw_line.strip():
        continue
    parts = raw_line.split("\t")
    while len(parts) < 4:
        parts.append("")
    name, project, working_dir, config_files = parts[:4]
    key = project or working_dir
    if not key:
        continue
    groups.setdefault(key, {"project": project, "working_dir": working_dir, "names": [], "config_files": set()})
    groups[key]["names"].append(name)
    if config_files:
        groups[key]["config_files"].add(config_files)

seed_name_pattern = re.compile(r"^(?:as\d+(?:brd|rtr|h)-|seedemu_|mail-)")

for key in sorted(groups):
    data = groups[key]
    project = data["project"]
    working_dir = data["working_dir"]
    abs_dir = os.path.abspath(working_dir) if working_dir else ""
    if abs_dir == attach_dir:
        continue
    names = sorted(data["names"])
    compose_file = ""
    for candidate in sorted(data["config_files"]):
        if candidate:
            compose_file = candidate
            break
    if not compose_file:
        for filename in ("docker-compose.yml", "compose.yml"):
            candidate = os.path.join(abs_dir, filename)
            if os.path.exists(candidate):
                compose_file = candidate
                break
    if not compose_file:
        continue

    reasons = []
    if abs_dir and (abs_dir == repo_root or abs_dir.startswith(repo_root + os.sep)):
        reasons.append("repo_local")
    base = os.path.basename(abs_dir).lower()
    if base.startswith("output") or base.endswith("output"):
        reasons.append("output_dir")
    if any(seed_name_pattern.match(name) for name in names):
        reasons.append("seed_container_pattern")
    if not reasons:
        continue

    print("\t".join([
        project,
        abs_dir,
        compose_file,
        ",".join(reasons),
        ",".join(names),
    ]))
PY
}

runtime_isolate_conflicts() {
  local attach_dir="$1"
  local runtime_dir="$2"
  local isolation_log="${runtime_dir}/isolation.log"
  : > "${isolation_log}"

  while IFS=$'\t' read -r project working_dir compose_file reasons container_names; do
    [[ -n "${project}${working_dir}" ]] || continue
    echo "[runtime-isolation] stopping project=${project:-unknown} dir=${working_dir:-missing} reasons=${reasons} containers=${container_names}" >>"${isolation_log}"
    if [[ -n "${working_dir}" && -d "${working_dir}" && -n "${compose_file}" ]]; then
      (
        cd "${working_dir}" && docker-compose down --remove-orphans >>"${isolation_log}" 2>&1
      ) || true
      continue
    fi

    if [[ -n "${project}" ]]; then
      docker ps -aq --filter "label=com.docker.compose.project=${project}" | while read -r container_id; do
        [[ -n "${container_id}" ]] || continue
        docker rm -f "${container_id}" >>"${isolation_log}" 2>&1 || true
      done
      docker network ls -q --filter "label=com.docker.compose.project=${project}" | while read -r network_id; do
        [[ -n "${network_id}" ]] || continue
        docker network rm "${network_id}" >>"${isolation_log}" 2>&1 || true
      done
    fi
  done < <(collect_managed_conflicts "${attach_dir}")
}

cleanup_dangling_seed_networks() {
  local runtime_dir="$1"
  local network_log="${runtime_dir}/network_cleanup.log"
  : > "${network_log}"

  python <<'PY' | while read -r network_name; do
import json
import re
import subprocess

pattern = re.compile(r"^(output($|_)|b29_|red_blue_|output_e2e_demo_|seedemu_)")
ls_proc = subprocess.run(["docker", "network", "ls", "--format", "{{.Name}}"], text=True, capture_output=True, check=False)
for name in ls_proc.stdout.splitlines():
    if not pattern.match(name):
        continue
    inspect = subprocess.run(["docker", "network", "inspect", name], text=True, capture_output=True, check=False)
    if inspect.returncode != 0:
        continue
    try:
        payload = json.loads(inspect.stdout)[0]
    except Exception:
        continue
    containers = payload.get("Containers") or {}
    if not containers:
        print(name)
PY
    [[ -n "${network_name}" ]] || continue
    echo "[runtime-network-cleanup] removing dangling network ${network_name}" >>"${network_log}"
    docker network rm "${network_name}" >>"${network_log}" 2>&1 || true
  done
}

runtime_cleanup() {
  local attach_dir="$1"
  [[ -n "${attach_dir}" ]] || return 0
  if [[ "${MANAGE_RUNTIME}" -ne 1 ]]; then
    return 0
  fi
  if [[ ! -f "${attach_dir}/docker-compose.yml" ]]; then
    return 0
  fi
  local key runtime_dir
  key="$(runtime_key "${attach_dir}")"
  runtime_dir="${RUN_DIR}/runtime/${key}"
  mkdir -p "${runtime_dir}"
  (
    cd "${attach_dir}" && docker-compose down --remove-orphans >"${runtime_dir}/down.log" 2>&1
  ) || true
}

runtime_prepare() {
  local attach_dir="$1"
  [[ -n "${attach_dir}" ]] || return 1
  if [[ "${MANAGE_RUNTIME}" -ne 1 ]]; then
    CURRENT_RUNTIME_ATTACH_DIR="${attach_dir}"
    return 0
  fi
  if [[ "${CURRENT_RUNTIME_ATTACH_DIR}" == "${attach_dir}" ]]; then
    return 0
  fi
  if [[ -n "${CURRENT_RUNTIME_ATTACH_DIR}" ]]; then
    runtime_cleanup "${CURRENT_RUNTIME_ATTACH_DIR}"
  fi
  if [[ ! -f "${attach_dir}/docker-compose.yml" ]]; then
    return 1
  fi

  local key runtime_dir down_rc up_rc
  key="$(runtime_key "${attach_dir}")"
  runtime_dir="${RUN_DIR}/runtime/${key}"
  mkdir -p "${runtime_dir}"

  runtime_isolate_conflicts "${attach_dir}" "${runtime_dir}"
  cleanup_dangling_seed_networks "${runtime_dir}"

  set +e
  (
    cd "${attach_dir}" && docker-compose down --remove-orphans >"${runtime_dir}/down.log" 2>&1
  )
  down_rc=$?
  (
    cd "${attach_dir}" && docker-compose up -d >"${runtime_dir}/up.log" 2>&1
  )
  up_rc=$?
  set -e

  python - "${runtime_dir}/state.json" "${attach_dir}" "${down_rc}" "${up_rc}" <<'PY'
import json
import pathlib
import sys

out_path = pathlib.Path(sys.argv[1])
attach_dir = sys.argv[2]
down_rc = int(sys.argv[3])
up_rc = int(sys.argv[4])
payload = {
    "attach_output_dir": attach_dir,
    "down_rc": down_rc,
    "up_rc": up_rc,
    "status": "ok" if up_rc == 0 else "error",
}
out_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
PY

  if [[ "${up_rc}" -ne 0 ]]; then
    return 1
  fi
  CURRENT_RUNTIME_ATTACH_DIR="${attach_dir}"
  return 0
}

ensure_control_plane() {
  local status_output=""
  set +e
  status_output="$(
    cd "${SEED_EMAIL_ROOT}" && "${ROOT_SEED_CODEX}" status 2>/dev/null
  )"
  set -e

  if grep -Eq 'SeedOps MCP: (running|running-external) .*http=(200|202|401)' <<<"${status_output}" \
    && grep -Eq 'SeedAgent MCP: (running|running-external) .*http=(200|202|401)' <<<"${status_output}"; then
    return 0
  fi

  echo "[review-pack] control plane unhealthy; restarting seed-codex services" >>"${CONTROL_LOG}"
  (
    cd "${SEED_EMAIL_ROOT}" && "${ROOT_SEED_CODEX}" restart >>"${CONTROL_LOG}" 2>&1
  )
}

write_runtime_failure_summary() {
  local task_dir="$1"
  local task_id="$2"
  local scenario_class="$3"
  local attach_dir="$4"
  local runtime_dir="$5"
  python - "${task_dir}" "${task_id}" "${scenario_class}" "${attach_dir}" "${runtime_dir}" <<'PY'
import json
import pathlib
import sys

task_dir = pathlib.Path(sys.argv[1])
task_id = sys.argv[2]
scenario_class = sys.argv[3]
attach_dir = sys.argv[4]
runtime_dir = pathlib.Path(sys.argv[5])

def tail(path: pathlib.Path, n: int = 20) -> str:
    if not path.exists():
        return ""
    lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    return "\n".join(lines[-n:])

summary = {
    "task_id": task_id,
    "scenario_class": scenario_class,
    "attach_output_dir": attach_dir,
    "start_status": "skipped_runtime_unavailable",
    "execute_status": None,
    "approved_execute_status": None,
    "status_status": "skipped_runtime_unavailable",
    "planner_mode": None,
    "verification_status": "not_started",
    "rollback_status": "not_started",
    "artifact_count": 0,
    "risky_action_count": 0,
    "selected_scope": None,
    "runtime_scale": None,
    "scale_hint": None,
    "action_count": 0,
    "latency_seconds": None,
    "attach_success": False,
    "planner_fallback": False,
    "unresolved_issues": [
        {
            "severity": "high",
            "failure_type": "runtime_asset_unavailable",
            "suspected_root_cause": "compose target could not be started cleanly in the current docker environment",
            "recommended_fix": "run this scenario in isolation, clean conflicting exited containers/networks, or switch to an attachable runtime with SEED labels",
            "owner": "unassigned",
            "runtime_isolation_log_tail": tail(runtime_dir / "isolation.log"),
            "runtime_up_log_tail": tail(runtime_dir / "up.log"),
        }
    ],
    "rc": {"start": None, "execute": None, "approve": None, "status": None},
    "manual_review": {
        "objective_understanding": None,
        "environment_awareness": None,
        "scope_choice_quality": None,
        "evidence_conclusion_consistency": None,
        "unnecessary_action_rate": None,
        "reviewer_notes": "",
    },
    "passed": False,
}
(task_dir / "task_summary.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")
PY
}

write_start_failure_summary() {
  local task_dir="$1"
  local task_id="$2"
  local scenario_class="$3"
  local attach_dir="$4"
  local start_rc="$5"
  python - "${task_dir}" "${task_id}" "${scenario_class}" "${attach_dir}" "${start_rc}" <<'PY'
import json
import pathlib
import sys

task_dir = pathlib.Path(sys.argv[1])
task_id = sys.argv[2]
scenario_class = sys.argv[3]
attach_dir = sys.argv[4]
start_rc = int(sys.argv[5])

def tail(path: pathlib.Path, n: int = 60) -> str:
    if not path.exists():
        return ""
    lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    return "\n".join(lines[-n:])

def read_json(path: pathlib.Path):
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}

stderr_tail = tail(task_dir / "start.stderr")
start_json = read_json(task_dir / "start.json")
error_blob = json.dumps(start_json, ensure_ascii=False)
failure_type = (
    "control_plane_unavailable"
    if (
        "ConnectError" in stderr_tail
        or "All connection attempts failed" in stderr_tail
        or "ConnectError" in error_blob
        or "All connection attempts failed" in error_blob
    )
    else "task_start_failed"
)
recommended_fix = (
    "restart the SeedOps/SeedAgent control plane, verify the MCP HTTP endpoints, and rerun the task"
    if failure_type == "control_plane_unavailable"
    else "inspect task inputs, task registry metadata, and start.stderr for the failing start path"
)

summary = {
    "task_id": task_id,
    "scenario_class": scenario_class,
    "attach_output_dir": attach_dir,
    "start_status": "start_failed",
    "execute_status": None,
    "approved_execute_status": None,
    "status_status": "not_started",
    "planner_mode": None,
    "verification_status": "not_started",
    "rollback_status": "not_started",
    "artifact_count": 0,
    "risky_action_count": 0,
    "selected_scope": None,
    "runtime_scale": None,
    "scale_hint": None,
    "action_count": 0,
    "latency_seconds": None,
    "attach_success": False,
    "planner_fallback": False,
    "unresolved_issues": [
        {
            "severity": "high",
            "failure_type": failure_type,
            "suspected_root_cause": "mission start did not complete successfully",
            "recommended_fix": recommended_fix,
            "owner": "unassigned",
            "start_stderr_tail": stderr_tail,
            "start_json": start_json,
        }
    ],
    "rc": {"start": start_rc, "execute": None, "approve": None, "status": None},
    "manual_review": {
        "objective_understanding": None,
        "environment_awareness": None,
        "scope_choice_quality": None,
        "evidence_conclusion_consistency": None,
        "unnecessary_action_rate": None,
        "reviewer_notes": "",
    },
    "passed": False,
}
(task_dir / "task_summary.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")
PY
}

cleanup() {
  if [[ "${KEEP_SERVICES}" -eq 0 && -n "${CURRENT_RUNTIME_ATTACH_DIR}" ]]; then
    runtime_cleanup "${CURRENT_RUNTIME_ATTACH_DIR}"
  fi
  if [[ "${KEEP_SERVICES}" -eq 0 ]]; then
    (
      cd "${SEED_EMAIL_ROOT}" && "${ROOT_SEED_CODEX}" down >"${DOWN_LOG}" 2>&1
    ) || true
  fi
}
trap cleanup EXIT

export SEED_MCP_TOKEN="${SEED_MCP_TOKEN:-${SEEDOPS_TOKEN:-${SEED_TOKEN}}}"
export SEED_AGENT_MCP_TOKEN="${SEED_AGENT_MCP_TOKEN:-${SEEDAGENT_TOKEN:-${SEED_TOKEN}}}"

(
  cd "${SEED_EMAIL_ROOT}" && "${ROOT_SEED_CODEX}" restart >"${UP_LOG}" 2>&1
)

task_scenario_class() {
  case "$1" in
    TS_B00_BGP_FLAP_ROOTCAUSE) echo "Diagnosis / Maintenance" ;;
    RS_B29_FAULT_IMPACT_ABLATION) echo "Disturbance Recovery" ;;
    TS_B00_PREFIX_HIJACK_LIVE) echo "Routing Security" ;;
    TS_B29_MAIL_REACHABILITY_DEBUG) echo "Service Reachability" ;;
    SEC_B29_DNS_MAIL_ABUSE_RESPONSE) echo "Security Offense-Defense" ;;
    RS_B00_CONVERGENCE_COMPARISON) echo "Research Experiments" ;;
    *) echo "Unclassified" ;;
  esac
}

task_objective() {
  case "$1" in
    TS_B00_BGP_FLAP_ROOTCAUSE) echo "Attach to live B00 runtime, diagnose BGP instability, and leave verified maintenance evidence." ;;
    RS_B29_FAULT_IMPACT_ABLATION) echo "Run a bounded packet-loss disturbance, observe impact, roll back, and verify recovery." ;;
    TS_B00_PREFIX_HIJACK_LIVE) echo "Run a live prefix hijack drill with explicit rollback and post-rollback verification." ;;
    TS_B29_MAIL_REACHABILITY_DEBUG) echo "Diagnose end-to-end mail reachability and verify service recovery when action is required." ;;
    SEC_B29_DNS_MAIL_ABUSE_RESPONSE) echo "Investigate DNS/mail abuse indicators, perform bounded containment checks, and validate post-action state." ;;
    RS_B00_CONVERGENCE_COMPARISON) echo "Compare routing convergence observations and produce quantitative evidence with assumptions." ;;
    *) echo "Run mission task." ;;
  esac
}

task_context_json() {
  python - "$1" <<'PY'
import json
import sys

task_id = sys.argv[1]
payloads = {
    "TS_B00_BGP_FLAP_ROOTCAUSE": {"suspect_router": "as151/router0"},
    "RS_B29_FAULT_IMPACT_ABLATION": {"fault_target": "as150/router0", "fault_type": "packet_loss"},
    "TS_B00_PREFIX_HIJACK_LIVE": {"target_prefix": "10.150.0.0/24", "attacker_asn": "151"},
    "TS_B29_MAIL_REACHABILITY_DEBUG": {"source_node": "as151/host_0", "destination_node": "as202/dns-auth-gmail"},
    "SEC_B29_DNS_MAIL_ABUSE_RESPONSE": {"suspected_domain": "gmail.com", "suspected_mail_node": "as202/dns-auth-gmail"},
    "RS_B00_CONVERGENCE_COMPARISON": {"comparison_target": "AS2-AS3"},
}
print(json.dumps(payloads.get(task_id, {}), ensure_ascii=False))
PY
}

task_requires_approval() {
  case "$1" in
    RS_B29_FAULT_IMPACT_ABLATION|TS_B00_PREFIX_HIJACK_LIVE|TS_B29_MAIL_REACHABILITY_DEBUG|SEC_B29_DNS_MAIL_ABUSE_RESPONSE)
      echo "1"
      ;;
    *)
      echo "0"
      ;;
  esac
}

json_field() {
  python - "$1" "$2" <<'PY'
import json
import sys

path = sys.argv[2].split(".")
try:
    obj = json.load(open(sys.argv[1], "r", encoding="utf-8"))
except Exception:
    print("")
    raise SystemExit(0)

cur = obj
for key in path:
    if isinstance(cur, dict):
        cur = cur.get(key)
    else:
        cur = None
        break
if cur is None:
    print("")
elif isinstance(cur, (dict, list)):
    print(json.dumps(cur, ensure_ascii=False))
else:
    print(cur)
PY
}

run_task() {
  local task_id="$1"
  local scenario_class objective context_json attach_dir runtime_dir
  local task_dir start_json execute_json approved_json status_json
  local start_rc exec_rc approve_rc status_rc session_id exec_status

  scenario_class="$(task_scenario_class "${task_id}")"
  objective="$(task_objective "${task_id}")"
  context_json="$(task_context_json "${task_id}")"
  attach_dir="$(mission_resolve_output_dir "${task_id}")"

  task_dir="${RUN_DIR}/${task_id}"
  mkdir -p "${task_dir}"
  start_json="${task_dir}/start.json"
  execute_json="${task_dir}/execute.json"
  approved_json="${task_dir}/execute.approved.json"
  status_json="${task_dir}/status.json"
  runtime_dir="${RUN_DIR}/runtime/$(runtime_key "${attach_dir}")"

  if ! runtime_prepare "${attach_dir}"; then
    echo "[review-pack] runtime prepare failed for ${task_id} (${scenario_class})" >&2
    write_runtime_failure_summary "${task_dir}" "${task_id}" "${scenario_class}" "${attach_dir}" "${runtime_dir}"
    return 0
  fi

  ensure_control_plane

  set +e
  (
    cd "${SEED_EMAIL_ROOT}" && "${ROOT_SEED_CODEX}" mission start \
      --task "${task_id}" \
      --objective "${objective}" \
      --workspace-name lab1 \
      --attach-output-dir "${attach_dir}" \
      --context-json "${context_json}"
  ) >"${start_json}" 2>"${task_dir}/start.stderr"
  start_rc=$?
  set -e

  session_id="$(json_field "${start_json}" "session.session_id")"
  if [[ -z "${session_id}" ]]; then
    echo "[review-pack] start failed for ${task_id} (${scenario_class})" >&2
    write_start_failure_summary "${task_dir}" "${task_id}" "${scenario_class}" "${attach_dir}" "${start_rc}"
    return 0
  fi

  set +e
  (
    cd "${SEED_EMAIL_ROOT}" && "${ROOT_SEED_CODEX}" mission execute \
      --session "${session_id}"
  ) >"${execute_json}" 2>"${task_dir}/execute.stderr"
  exec_rc=$?
  set -e

  exec_status="$(json_field "${execute_json}" "status")"
  approve_rc=0
  if [[ "${exec_status}" == "awaiting_confirmation" ]]; then
    set +e
    (
      cd "${SEED_EMAIL_ROOT}" && "${ROOT_SEED_CODEX}" mission execute \
        --session "${session_id}" \
        --approve YES_RUN_DYNAMIC_FAULTS
    ) >"${approved_json}" 2>"${task_dir}/execute.approved.stderr"
    approve_rc=$?
    set -e
  fi

  set +e
  (
    cd "${SEED_EMAIL_ROOT}" && "${ROOT_SEED_CODEX}" mission status \
      --session "${session_id}"
  ) >"${status_json}" 2>"${task_dir}/status.stderr"
  status_rc=$?
  set -e

  python - "${task_dir}" "${task_id}" "${scenario_class}" "${attach_dir}" "${start_rc}" "${exec_rc}" "${approve_rc}" "${status_rc}" <<'PY'
import json
import pathlib
import sys

task_dir = pathlib.Path(sys.argv[1])
task_id = sys.argv[2]
scenario_class = sys.argv[3]
attach_dir = sys.argv[4]
start_rc, exec_rc, approve_rc, status_rc = [int(x) for x in sys.argv[5:9]]

def read(name: str):
    p = task_dir / name
    if not p.exists():
        return {}
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return {}

start = read("start.json")
execute = read("execute.json")
approved = read("execute.approved.json")
status = read("status.json")
final_execution = approved or execute
report = status.get("report_summary") or final_execution.get("report_summary") or {}
execution = final_execution.get("execution") or {}
summary = execution.get("summary") or {}
expected_min_risky_actions = {
    "TS_B00_PREFIX_HIJACK_LIVE": 2,
    "RS_B29_FAULT_IMPACT_ABLATION": 1,
    "SEC_B29_DNS_MAIL_ABUSE_RESPONSE": 1,
}
allowed_verification_states = {"verified", "verified_with_warnings"}
min_risky_actions = expected_min_risky_actions.get(task_id, 0)
verification_status = summary.get("verification_status") or report.get("verification_status")
rollback_status = summary.get("rollback_status") or report.get("rollback_status")
risky_action_count = int(summary.get("risky_action_count") or 0)
attach_success = bool((summary.get("environment_snapshot") or {}).get("attach"))
verification_ok = verification_status in allowed_verification_states if verification_status else False
rollback_required = bool(report.get("rollback_required") or summary.get("rollback_expected"))
mutation_ok = risky_action_count >= min_risky_actions
rollback_ok = True
if min_risky_actions > 0 and rollback_required:
    rollback_ok = rollback_status == "verified"
extra_issues = []
if min_risky_actions > 0 and not mutation_ok:
    extra_issues.append({
        "severity": "high",
        "failure_type": "expected_mutation_missing",
        "suspected_root_cause": "task completed without executing the required risky operation for this scenario class",
        "recommended_fix": "tighten planner/task grounding so the approved execution performs the expected disturbance or containment action",
        "owner": "unassigned",
    })
if min_risky_actions > 0 and rollback_required and mutation_ok and not rollback_ok:
    extra_issues.append({
        "severity": "high",
        "failure_type": "rollback_not_verified",
        "suspected_root_cause": "task mutated runtime state but did not verify rollback successfully",
        "recommended_fix": "require explicit rollback verification before treating the run as successful",
        "owner": "unassigned",
    })

task_summary = {
    "task_id": task_id,
    "scenario_class": scenario_class,
    "attach_output_dir": attach_dir,
    "start_status": start.get("status"),
    "execute_status": execute.get("status"),
    "approved_execute_status": approved.get("status"),
    "status_status": status.get("status"),
    "planner_mode": ((execution.get("compiled_plan") or {}).get("planner_mode")),
    "verification_status": verification_status,
    "rollback_status": rollback_status,
    "artifact_count": summary.get("artifact_count"),
    "risky_action_count": risky_action_count,
    "selected_scope": summary.get("selected_scope"),
    "runtime_scale": summary.get("runtime_scale"),
    "scale_hint": summary.get("scale_hint"),
    "action_count": summary.get("action_count"),
    "latency_seconds": summary.get("latency_seconds"),
    "attach_success": attach_success,
    "planner_fallback": bool(((execution.get("compiled_plan") or {}).get("fallback_used"))),
    "expected_min_risky_actions": min_risky_actions,
    "unresolved_issues": (report.get("unresolved_issues") or summary.get("unresolved_issues") or []) + extra_issues,
    "rc": {
        "start": start_rc,
        "execute": exec_rc,
        "approve": approve_rc,
        "status": status_rc,
    },
    "manual_review": {
        "objective_understanding": None,
        "environment_awareness": None,
        "scope_choice_quality": None,
        "evidence_conclusion_consistency": None,
        "unnecessary_action_rate": None,
        "reviewer_notes": "",
    },
}
base_pass = bool(
    task_summary["start_status"] in {"ok", "awaiting_confirmation"}
    and (task_summary["status_status"] == "ok" or task_summary["approved_execute_status"] == "ok" or task_summary["execute_status"] == "ok")
)
task_summary["passed"] = bool(
    base_pass
    and attach_success
    and verification_ok
    and mutation_ok
    and rollback_ok
)
(task_dir / "task_summary.json").write_text(json.dumps(task_summary, indent=2, ensure_ascii=False), encoding="utf-8")
PY
}

TASKS=(
  TS_B00_BGP_FLAP_ROOTCAUSE
  TS_B00_PREFIX_HIJACK_LIVE
  RS_B00_CONVERGENCE_COMPARISON
  RS_B29_FAULT_IMPACT_ABLATION
  TS_B29_MAIL_REACHABILITY_DEBUG
  SEC_B29_DNS_MAIL_ABUSE_RESPONSE
)

for task_id in "${TASKS[@]}"; do
  run_task "${task_id}"
done

python - "${RUN_DIR}" "${SUMMARY_JSON}" "${REPORT_MD}" <<'PY'
import json
import pathlib
import sys
from datetime import datetime, timezone

run_dir = pathlib.Path(sys.argv[1])
summary_path = pathlib.Path(sys.argv[2])
report_path = pathlib.Path(sys.argv[3])

task_summaries = []
for task_dir in sorted(run_dir.iterdir()):
    if not task_dir.is_dir():
        continue
    summary_file = task_dir / "task_summary.json"
    if not summary_file.exists():
        continue
    task_summaries.append(json.loads(summary_file.read_text(encoding="utf-8")))

by_class = {}
for item in task_summaries:
    bucket = by_class.setdefault(item["scenario_class"], {"total": 0, "passed": 0, "tasks": []})
    bucket["total"] += 1
    bucket["passed"] += 1 if item.get("passed") else 0
    bucket["tasks"].append(item)

summary = {
    "generated_at_utc": datetime.now(timezone.utc).isoformat(),
    "run_dir": str(run_dir),
    "task_count": len(task_summaries),
    "classes": {
        key: {
            "total": value["total"],
            "passed": value["passed"],
            "failed": value["total"] - value["passed"],
        }
        for key, value in sorted(by_class.items())
    },
    "tasks": task_summaries,
}
summary["aggregate_metrics"] = {
    "attach_success_count": sum(1 for item in task_summaries if item.get("attach_success")),
    "verification_success_count": sum(1 for item in task_summaries if item.get("verification_status") in {"verified", "verified_with_warnings"}),
    "rollback_verified_count": sum(1 for item in task_summaries if item.get("rollback_status") == "verified"),
    "planner_fallback_count": sum(1 for item in task_summaries if item.get("planner_fallback")),
    "total_risky_actions": sum(int(item.get("risky_action_count") or 0) for item in task_summaries),
}
summary["overall"] = {
    "status": "passed" if all(item.get("passed") for item in task_summaries) and task_summaries else "needs_review",
    "passed_tasks": sum(1 for item in task_summaries if item.get("passed")),
    "failed_tasks": sum(1 for item in task_summaries if not item.get("passed")),
}
summary["human_review_fields"] = [
    "objective_understanding",
    "environment_awareness",
    "scope_choice_quality",
    "evidence_conclusion_consistency",
    "unnecessary_action_rate",
]
summary["all_passed"] = all(item.get("passed") for item in task_summaries) if task_summaries else False
summary_path.write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")

lines = [
    "# Seed Agent Six-Class Review Pack",
    "",
    f"- Generated at (UTC): {summary['generated_at_utc']}",
    f"- Run dir: `{run_dir}`",
    f"- Overall: `{'passed' if summary['all_passed'] else 'needs review'}`",
    "",
    "## Class Summary",
]
for key, value in sorted(summary["classes"].items()):
    lines.append(f"- {key}: passed {value['passed']}/{value['total']}, failed {value['failed']}")

lines.append("")
lines.append("## Task Summary")
for item in task_summaries:
    lines.append(f"- `{item['task_id']}` ({item['scenario_class']}):")
    lines.append(f"  start={item.get('start_status')} execute={item.get('execute_status')} approved={item.get('approved_execute_status')} status={item.get('status_status')}")
    lines.append(f"  planner={item.get('planner_mode')} scale={item.get('scale_hint')} attach={item.get('attach_success')} actions={item.get('action_count')} risky_actions={item.get('risky_action_count')} verification={item.get('verification_status')} rollback={item.get('rollback_status')}")
    unresolved = item.get("unresolved_issues") or []
    if unresolved:
        for issue in unresolved[:3]:
            if isinstance(issue, dict):
                lines.append(f"  unresolved: {issue.get('failure_type')} / {issue.get('recommended_fix')}")
            else:
                lines.append(f"  unresolved: {issue}")
    else:
        lines.append("  unresolved: none")
    lines.append("  manual_review: objective_understanding=?, environment_awareness=?, scope_choice_quality=?, evidence_conclusion_consistency=?, unnecessary_action_rate=?")

report_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
PY

echo "Review pack written to: ${RUN_DIR}"
