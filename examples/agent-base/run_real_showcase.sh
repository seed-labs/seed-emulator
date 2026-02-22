#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
SEED_AGENT_DIR="${SEED_AGENT_DIR:-${REPO_ROOT}/subrepos/seed-agent}"
SEED_AGENT_DIR="$(python - <<'PY' "$SEED_AGENT_DIR"
import os, sys
print(os.path.abspath(os.path.expanduser(sys.argv[1])))
PY
)"
if [[ ! -d "${SEED_AGENT_DIR}" ]]; then
  echo "Seed-Agent directory not found: ${SEED_AGENT_DIR}" >&2
  echo "Initialize submodule first: git submodule update --init --recursive" >&2
  exit 2
fi
if [[ ! -f "${SEED_AGENT_DIR}/serve_seedagent_http.py" ]]; then
  echo "Invalid Seed-Agent directory: ${SEED_AGENT_DIR}" >&2
  echo "Expected file missing: serve_seedagent_http.py" >&2
  exit 2
fi
ENV_FILE="${ENV_FILE:-}"
if [[ -z "${ENV_FILE}" && -f "${REPO_ROOT}/.env" ]]; then
  ENV_FILE="${REPO_ROOT}/.env"
fi

WORK_DIR="${WORK_DIR:-/tmp/seed-agent-real-showcase}"
KEEP_WORK_DIR=0
SEED_TOKEN="${SEED_TOKEN:-seed-local-token}"
S01_MODE="${S01_MODE:-fallback}"
S04_MODE="${S04_MODE:-fallback}"
RUN_B29_CANONICAL_QUICK=1

B00_SRC="${REPO_ROOT}/examples/internet/B00_mini_internet/output"
B29_SRC="${REPO_ROOT}/examples/internet/B29_email_dns/output"
B00_TMP="${WORK_DIR}/B00_output"
B29_TMP="${WORK_DIR}/B29_output"
LOG_DIR="${WORK_DIR}/logs"
SUMMARY_JSON="${WORK_DIR}/real_showcase_summary.json"

SEEDOPS_PID=""
SEEDAGENT_PID=""
RUNNING_B00=0
RUNNING_B29=0
RC_S01=99
RC_S02=99
RC_S03=99
RC_S04=99

usage() {
  cat <<'EOF'
Usage: examples/agent-base/run_real_showcase.sh [options]

Options:
  --work-dir <path>            Temp work directory (default: /tmp/seed-agent-real-showcase)
  --seed-token <token>         Shared MCP bearer token for this run
  --env-file <path>            Optional env file for LLM credentials (default: ./.env if present)
  --s01-mode canonical|fallback|both
  --s04-mode canonical|fallback|both
  --skip-b29-canonical-quick   Disable quick canonical seed_agent_run check on B29
  --keep-work-dir              Keep temp copied compose outputs after run
  -h, --help
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --work-dir)
      WORK_DIR="${2:-}"
      shift 2
      ;;
    --seed-token)
      SEED_TOKEN="${2:-}"
      shift 2
      ;;
    --env-file)
      ENV_FILE="${2:-}"
      shift 2
      ;;
    --s01-mode)
      S01_MODE="${2:-}"
      shift 2
      ;;
    --s04-mode)
      S04_MODE="${2:-}"
      shift 2
      ;;
    --skip-b29-canonical-quick)
      RUN_B29_CANONICAL_QUICK=0
      shift
      ;;
    --keep-work-dir)
      KEEP_WORK_DIR=1
      shift
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "Unknown argument: $1" >&2
      usage
      exit 2
      ;;
  esac
done

WORK_DIR="$(python - <<'PY' "$WORK_DIR"
import os, sys
print(os.path.abspath(os.path.expanduser(sys.argv[1])))
PY
)"
B00_TMP="${WORK_DIR}/B00_output"
B29_TMP="${WORK_DIR}/B29_output"
LOG_DIR="${WORK_DIR}/logs"
SUMMARY_JSON="${WORK_DIR}/real_showcase_summary.json"

validate_mode() {
  local mode="$1"
  case "$mode" in
    canonical|fallback|both) return 0 ;;
    *)
      echo "Invalid mode: ${mode}" >&2
      exit 2
      ;;
  esac
}

validate_mode "${S01_MODE}"
validate_mode "${S04_MODE}"

load_env_file() {
  local env_file="$1"
  if [[ ! -f "${env_file}" ]]; then
    echo "Env file not found: ${env_file}" >&2
    exit 2
  fi
  set -a
  # shellcheck disable=SC1090
  source "${env_file}"
  set +a
}

if [[ -n "${ENV_FILE}" ]]; then
  load_env_file "${ENV_FILE}"
fi

if [[ -z "${OPENAI_API_KEY:-}" && -n "${LLM_API_KEY:-}" ]]; then
  OPENAI_API_KEY="${LLM_API_KEY}"
fi
if [[ -z "${OPENAI_API_BASE:-}" && -n "${LLM_BASE_URL:-}" ]]; then
  OPENAI_API_BASE="${LLM_BASE_URL}"
fi
if [[ -z "${GOOGLE_API_KEY:-}" && -n "${GEMINI_API_KEY:-}" ]]; then
  GOOGLE_API_KEY="${GEMINI_API_KEY}"
fi
if [[ -z "${LLM_MODEL:-}" ]]; then
  LLM_MODEL="gpt-4o-mini"
fi

require_cmd() {
  local cmd="$1"
  if ! command -v "$cmd" >/dev/null 2>&1; then
    echo "Missing required command: ${cmd}" >&2
    exit 2
  fi
}

require_cmd python
require_cmd docker
require_cmd docker-compose

mkdir -p "${WORK_DIR}" "${LOG_DIR}"
rm -rf "${B00_TMP}" "${B29_TMP}"
cp -a "${B00_SRC}" "${B00_TMP}"
cp -a "${B29_SRC}" "${B29_TMP}"

export SEED_MCP_TOKEN="${SEED_TOKEN}"
export SEEDOPS_MCP_TOKEN="${SEED_TOKEN}"
export SEED_AGENT_MCP_TOKEN="${SEED_TOKEN}"
export SEED_MCP_URL="http://127.0.0.1:8000/mcp"
export SEEDOPS_MCP_URL="http://127.0.0.1:8000/mcp"
export SEED_AGENT_MCP_URL="http://127.0.0.1:8100/mcp"

patch_compose_and_clear_conflicts() {
  local compose_file="$1"
  python - "${compose_file}" <<'PY'
import subprocess
import yaml
from pathlib import Path
import sys

compose_file = Path(sys.argv[1])
obj = yaml.safe_load(compose_file.read_text(encoding="utf-8")) or {}
subnet_map = {
    "10.100.0.0/24": "172.30.100.0/24",
    "10.150.0.0/24": "172.30.150.0/24",
}
prefix_map = {
    "10.100.": "172.30.100.",
    "10.150.": "172.30.150.",
}

for cfg in (obj.get("networks") or {}).values():
    for ipam_cfg in ((cfg or {}).get("ipam") or {}).get("config") or []:
        subnet = ipam_cfg.get("subnet")
        if subnet in subnet_map:
            ipam_cfg["subnet"] = subnet_map[subnet]

for svc in (obj.get("services") or {}).values():
    networks = svc.get("networks")
    if isinstance(networks, dict):
        for net_cfg in networks.values():
            if not isinstance(net_cfg, dict):
                continue
            ip = net_cfg.get("ipv4_address")
            if isinstance(ip, str):
                for old, new in prefix_map.items():
                    if ip.startswith(old):
                        net_cfg["ipv4_address"] = new + ip.split(".")[-1]

existing = set(
    subprocess.check_output(["docker", "ps", "-a", "--format", "{{.Names}}"])
    .decode()
    .splitlines()
)
for svc in (obj.get("services") or {}).values():
    container_name = svc.get("container_name")
    if isinstance(container_name, str) and container_name in existing:
        subprocess.run(
            ["docker", "rm", "-f", container_name],
            check=False,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )

compose_file.write_text(yaml.safe_dump(obj, sort_keys=False), encoding="utf-8")
print(f"patched: {compose_file}")
PY
}

patch_compose_and_clear_conflicts "${B00_TMP}/docker-compose.yml"
patch_compose_and_clear_conflicts "${B29_TMP}/docker-compose.yml"

wait_mcp_ready() {
  python - <<'PY'
import time
import urllib.request

urls = ["http://127.0.0.1:8000/mcp", "http://127.0.0.1:8100/mcp"]
deadline = time.time() + 30

while time.time() < deadline:
    ok = True
    for url in urls:
        try:
            urllib.request.urlopen(url, timeout=1)
        except Exception as exc:
            if "HTTP Error" in str(exc):
                continue
            ok = False
            break
    if ok:
        print("MCP services ready")
        raise SystemExit(0)
    time.sleep(0.5)

raise SystemExit("MCP services not ready within 30s")
PY
}

cleanup() {
  set +e
  if [[ -d "${B00_TMP}" ]]; then
    (cd "${B00_TMP}" && docker-compose down >"${LOG_DIR}/b00-down.log" 2>&1) || true
  fi
  if [[ -d "${B29_TMP}" ]]; then
    (cd "${B29_TMP}" && docker-compose down >"${LOG_DIR}/b29-down.log" 2>&1) || true
  fi
  if [[ -n "${SEEDAGENT_PID}" ]] && kill -0 "${SEEDAGENT_PID}" 2>/dev/null; then
    kill "${SEEDAGENT_PID}" 2>/dev/null || true
  fi
  if [[ -n "${SEEDOPS_PID}" ]] && kill -0 "${SEEDOPS_PID}" 2>/dev/null; then
    kill "${SEEDOPS_PID}" 2>/dev/null || true
  fi
  if [[ "${KEEP_WORK_DIR}" -eq 0 ]]; then
    rm -rf "${B00_TMP}" "${B29_TMP}"
  fi
}
trap cleanup EXIT

(cd "${REPO_ROOT}/mcp-server" && \
  FASTMCP_HOST="127.0.0.1" FASTMCP_PORT="8000" FASTMCP_STREAMABLE_HTTP_PATH="/mcp" \
  SEED_MCP_TOKEN="${SEED_MCP_TOKEN}" SEED_MCP_PUBLIC_URL="http://127.0.0.1:8000" \
  python serve_http.py >"${LOG_DIR}/seedops.log" 2>&1) &
SEEDOPS_PID=$!

(cd "${SEED_AGENT_DIR}" && \
  SEED_AGENT_MCP_TOKEN="${SEED_AGENT_MCP_TOKEN}" \
  SEED_AGENT_MCP_HOST="127.0.0.1" SEED_AGENT_MCP_PORT="8100" SEED_AGENT_MCP_PATH="/mcp" \
  SEED_AGENT_MCP_PUBLIC_URL="http://127.0.0.1:8100" \
  SEED_MCP_CLIENT_MODE="http" SEED_MCP_URL="${SEED_MCP_URL}" SEED_MCP_TOKEN="${SEED_MCP_TOKEN}" \
  OPENAI_API_KEY="${OPENAI_API_KEY:-}" \
  OPENAI_API_BASE="${OPENAI_API_BASE:-}" \
  GOOGLE_API_KEY="${GOOGLE_API_KEY:-}" \
  GEMINI_API_KEY="${GEMINI_API_KEY:-}" \
  MIMO_API_KEY="${MIMO_API_KEY:-}" \
  LLM_API_KEY="${LLM_API_KEY:-}" \
  LLM_BASE_URL="${LLM_BASE_URL:-}" \
  LLM_MODEL="${LLM_MODEL}" \
  python serve_seedagent_http.py >"${LOG_DIR}/seedagent.log" 2>&1) &
SEEDAGENT_PID=$!

wait_mcp_ready

run_cmd_with_timeout() {
  local timeout_sec="$1"
  shift
  if command -v timeout >/dev/null 2>&1; then
    timeout "${timeout_sec}" "$@"
  else
    "$@"
  fi
}

# ---------------------------------------------------------------------------
# B00 run: S02 + S03
# ---------------------------------------------------------------------------
(cd "${B00_TMP}" && docker-compose up -d >"${LOG_DIR}/b00-up.log" 2>&1)
sleep 10
RUNNING_B00="$(cd "${B00_TMP}" && docker-compose ps --services --filter status=running | wc -l | tr -d ' ')"
echo "B00 running services: ${RUNNING_B00}"

set +e
run_cmd_with_timeout 1500 \
  "${REPO_ROOT}/examples/agent-base/S02_b00_path_maintenance/run.sh" \
  --mode both --output-dir "${B00_TMP}" >"${LOG_DIR}/s02.log" 2>&1
RC_S02=$?

run_cmd_with_timeout 1800 \
  "${REPO_ROOT}/examples/agent-base/S03_b00_latency_experiment/run.sh" \
  --mode both --output-dir "${B00_TMP}" --risk on --confirm-token YES_RUN_DYNAMIC_FAULTS >"${LOG_DIR}/s03.log" 2>&1
RC_S03=$?
set -e

(cd "${B00_TMP}" && docker-compose down >"${LOG_DIR}/b00-down-mid.log" 2>&1) || true

# ---------------------------------------------------------------------------
# B29 run: quick canonical + S01 + S04
# ---------------------------------------------------------------------------
(cd "${B29_TMP}" && docker-compose up -d >"${LOG_DIR}/b29-up.log" 2>&1)
sleep 10
RUNNING_B29="$(cd "${B29_TMP}" && docker-compose ps --services --filter status=running | wc -l | tr -d ' ')"
echo "B29 running services: ${RUNNING_B29}"

if [[ "${RUN_B29_CANONICAL_QUICK}" -eq 1 ]]; then
  python "${REPO_ROOT}/examples/agent-base/_common/invoke_seed_agent.py" run \
    --url "${SEED_AGENT_MCP_URL}" \
    --token "${SEED_AGENT_MCP_TOKEN}" \
    --request "Attach to B29 and summarize bgp briefly." \
    --workspace-name lab1 \
    --attach-output-dir "${B29_TMP}" \
    --policy-profile read_only \
    --no-follow-job \
    --no-download-artifacts >"${LOG_DIR}/s01_canonical_quick.json" 2>&1 || true
fi

set +e
run_cmd_with_timeout 1800 \
  env SEED_AGENT_FOLLOW_JOB=0 \
  "${REPO_ROOT}/examples/agent-base/S01_b29_health_maintenance/run.sh" \
  --mode "${S01_MODE}" --output-dir "${B29_TMP}" >"${LOG_DIR}/s01.log" 2>&1
RC_S01=$?

run_cmd_with_timeout 2100 \
  env SEED_AGENT_FOLLOW_JOB=0 \
  "${REPO_ROOT}/examples/agent-base/S04_b29_packetloss_experiment/run.sh" \
  --mode "${S04_MODE}" --output-dir "${B29_TMP}" --risk on --confirm-token YES_RUN_DYNAMIC_FAULTS >"${LOG_DIR}/s04.log" 2>&1
RC_S04=$?
set -e

python - "${SUMMARY_JSON}" "${RUNNING_B00}" "${RUNNING_B29}" "${RC_S01}" "${RC_S02}" "${RC_S03}" "${RC_S04}" "${S01_MODE}" "${S04_MODE}" "${REPO_ROOT}" <<'PY'
import json
import sys
from pathlib import Path

summary_path = Path(sys.argv[1])
running_b00 = int(sys.argv[2])
running_b29 = int(sys.argv[3])
rc_s01 = int(sys.argv[4])
rc_s02 = int(sys.argv[5])
rc_s03 = int(sys.argv[6])
rc_s04 = int(sys.argv[7])
s01_mode = sys.argv[8]
s04_mode = sys.argv[9]
repo_root = Path(sys.argv[10])

root = repo_root / "examples" / "agent-base"
scenario_paths = {
    "S01": root / "S01_b29_health_maintenance" / "artifacts" / "S01_b29_health_maintenance" / "latest",
    "S02": root / "S02_b00_path_maintenance" / "artifacts" / "S02_b00_path_maintenance" / "latest",
    "S03": root / "S03_b00_latency_experiment" / "artifacts" / "S03_b00_latency_experiment" / "latest",
    "S04": root / "S04_b29_packetloss_experiment" / "artifacts" / "S04_b29_packetloss_experiment" / "latest",
}

def load_status(path: Path):
    if not path.exists():
        return {"status": "missing", "errors": ["missing file"]}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return {
            "status": data.get("status", "unknown"),
            "errors": data.get("errors") or [],
            "summary": data.get("summary") or {},
        }
    except Exception as exc:
        return {"status": "parse_error", "errors": [str(exc)]}

data = {
    "runtime": {
        "running_services_b00": running_b00,
        "running_services_b29": running_b29,
    },
    "modes": {
        "s01_mode": s01_mode,
        "s04_mode": s04_mode,
    },
    "exit_codes": {
        "S01": rc_s01,
        "S02": rc_s02,
        "S03": rc_s03,
        "S04": rc_s04,
    },
    "artifacts": {
        "S01_latest": "",
        "S02_latest": "",
        "S03_latest": "",
        "S04_latest": "",
    },
    "statuses": {
        "S01_primary": load_status((scenario_paths["S01"].resolve() / "response.canonical.json") if scenario_paths["S01"].exists() else Path("/missing")),
        "S02_primary": load_status((scenario_paths["S02"].resolve() / "run.json") if scenario_paths["S02"].exists() else Path("/missing")),
        "S03_baseline": load_status((scenario_paths["S03"].resolve() / "baseline.json") if scenario_paths["S03"].exists() else Path("/missing")),
        "S03_experiment": load_status((scenario_paths["S03"].resolve() / "experiment.json") if scenario_paths["S03"].exists() else Path("/missing")),
        "S03_rollback": load_status((scenario_paths["S03"].resolve() / "rollback.json") if scenario_paths["S03"].exists() else Path("/missing")),
        "S04_baseline": load_status((scenario_paths["S04"].resolve() / "baseline.json") if scenario_paths["S04"].exists() else Path("/missing")),
        "S04_experiment": load_status((scenario_paths["S04"].resolve() / "experiment.json") if scenario_paths["S04"].exists() else Path("/missing")),
        "S04_rollback": load_status((scenario_paths["S04"].resolve() / "rollback.json") if scenario_paths["S04"].exists() else Path("/missing")),
    },
}

def display_path(path: Path) -> str:
    if not path.exists():
        return ""
    resolved = path.resolve()
    try:
        return str(resolved.relative_to(repo_root.resolve()))
    except ValueError:
        return str(resolved)

data["artifacts"]["S01_latest"] = display_path(scenario_paths["S01"])
data["artifacts"]["S02_latest"] = display_path(scenario_paths["S02"])
data["artifacts"]["S03_latest"] = display_path(scenario_paths["S03"])
data["artifacts"]["S04_latest"] = display_path(scenario_paths["S04"])

summary_path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
print(json.dumps(data, indent=2, ensure_ascii=False))
PY

echo
echo "Summary JSON: ${SUMMARY_JSON}"
echo "Logs dir:      ${LOG_DIR}"
echo "RC_S01=${RC_S01} RC_S02=${RC_S02} RC_S03=${RC_S03} RC_S04=${RC_S04}"

final_rc=0
for rc in "${RC_S01}" "${RC_S02}" "${RC_S03}" "${RC_S04}"; do
  if [[ "${rc}" -ne 0 ]]; then
    final_rc=1
    break
  fi
done
exit "${final_rc}"
