#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${SCRIPT_DIR}/env_seedemu.sh"

VALIDATION_DIR_INPUT="${1:-}"
OBSERVE_DIR_INPUT="${2:-}"
REPORT_DIR_INPUT="${3:-}"

find_latest_dir() {
  local base_dir="$1"
  if [ ! -d "${base_dir}" ]; then
    return 1
  fi

  local latest
  latest="$(find "${base_dir}" -mindepth 1 -maxdepth 1 -type d -printf '%T@ %p\n' 2>/dev/null | sort -nr | awk 'NR==1{print $2}')"
  if [ -z "${latest}" ]; then
    return 1
  fi

  printf '%s\n' "${latest}"
}

resolve_validation_dir() {
  if [ -n "${VALIDATION_DIR_INPUT}" ]; then
    printf '%s\n' "${VALIDATION_DIR_INPUT}"
    return
  fi

  if [ -n "${SEED_ARTIFACT_DIR:-}" ]; then
    printf '%s\n' "${SEED_ARTIFACT_DIR}"
    return
  fi

  if latest="$(find_latest_dir "${REPO_ROOT}/output/multinode_mini_validation" 2>/dev/null)"; then
    printf '%s\n' "${latest}"
    return
  fi

  if latest="$(find_latest_dir "${REPO_ROOT}/output/opencode_seedlab_fullrun" 2>/dev/null)"; then
    printf '%s\n' "${latest}"
    return
  fi

  return 1
}

resolve_observe_dir() {
  if [ -n "${OBSERVE_DIR_INPUT}" ]; then
    printf '%s\n' "${OBSERVE_DIR_INPUT}"
    return
  fi

  if [ -n "${SEED_OBSERVE_DIR:-}" ]; then
    printf '%s\n' "${SEED_OBSERVE_DIR}"
    return
  fi

  if [ -L "${REPO_ROOT}/output/mini_observe/latest" ] || [ -d "${REPO_ROOT}/output/mini_observe/latest" ]; then
    printf '%s\n' "${REPO_ROOT}/output/mini_observe/latest"
    return
  fi

  printf '%s\n' ""
}

VALIDATION_DIR="$(resolve_validation_dir || true)"
OBSERVE_DIR="$(resolve_observe_dir)"

if [ -z "${VALIDATION_DIR}" ]; then
  echo "Cannot determine validation artifact directory." >&2
  echo "Provide argument or set SEED_ARTIFACT_DIR." >&2
  exit 1
fi

if [ ! -d "${VALIDATION_DIR}" ]; then
  echo "Validation artifact directory not found: ${VALIDATION_DIR}" >&2
  exit 1
fi

if [ ! -f "${VALIDATION_DIR}/summary.json" ]; then
  echo "Missing required file: ${VALIDATION_DIR}/summary.json" >&2
  exit 1
fi

if [ -z "${REPORT_DIR_INPUT}" ]; then
  REPORT_DIR="${VALIDATION_DIR}/report"
else
  REPORT_DIR="${REPORT_DIR_INPUT}"
fi

mkdir -p "${REPORT_DIR}"

python3 - <<PY
import json
from datetime import datetime, timezone
from pathlib import Path

validation_dir = Path(${VALIDATION_DIR@Q}).resolve()
observe_dir_raw = ${OBSERVE_DIR@Q}
observe_dir = Path(observe_dir_raw).resolve() if observe_dir_raw else None
report_dir = Path(${REPORT_DIR@Q}).resolve()
report_dir.mkdir(parents=True, exist_ok=True)

summary = json.loads((validation_dir / "summary.json").read_text(encoding="utf-8"))


def load_json_if_exists(path: Path):
    if path.exists():
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return {"parse_error": str(path)}
    return None

placement = load_json_if_exists(validation_dir / "placement_check.json")
recovery = load_json_if_exists(validation_dir / "recovery_check.json")
diagnostics = load_json_if_exists(validation_dir / "diagnostics.json")
next_actions = load_json_if_exists(validation_dir / "next_actions.json")
observe_summary = load_json_if_exists(observe_dir / "summary.json") if observe_dir else None
observe_namespace_match = None
if observe_summary is not None:
    expected_ns = str(summary.get("namespace", ""))
    observe_ns = str(observe_summary.get("namespace", ""))
    observe_namespace_match = (observe_ns == expected_ns)

strict3 = bool(summary.get("strict3_passed", False))
placement_passed = bool(summary.get("placement_passed", strict3))
placement_mode = str(summary.get("placement_mode", "strict3"))
bgp = bool(summary.get("bgp_passed", False))
connectivity = bool(summary.get("connectivity_passed", False))
recovery_passed = bool(summary.get("recovery_passed", False))
overall_pass = placement_passed and bgp and connectivity and recovery_passed

failure_reason = str(summary.get("failure_reason", "") or "")
failure_code = str(summary.get("failure_code", "") or "")
if diagnostics and isinstance(diagnostics, dict):
    failure_code = str(diagnostics.get("failure_code", failure_code) or failure_code)

if (observe_namespace_match is False) and not failure_code:
    failure_code = "OBSERVE_NAMESPACE_MISMATCH"

retry_by_failure = {
    "kubeconfig_not_found_after_fetch": "scripts/k3s_fetch_kubeconfig.sh && scripts/validate_k3s_mini_internet_multinode.sh preflight",
    "ssh_key_not_found": "export SEED_K3S_SSH_KEY=/path/to/key && scripts/validate_k3s_mini_internet_multinode.sh preflight",
    "preflight_failed_after_repair": "scripts/validate_k3s_mini_internet_multinode.sh preflight",
    "compile_missing_k8s_yaml": "scripts/validate_k3s_mini_internet_multinode.sh compile",
    "deploy_wait_timeout_or_failure": "scripts/validate_k3s_mini_internet_multinode.sh deploy",
    "strict3_placement_failed": "scripts/validate_k3s_mini_internet_multinode.sh verify",
    "placement_check_failed": "scripts/validate_k3s_mini_internet_multinode.sh verify",
    "bgp_not_established": "scripts/validate_k3s_mini_internet_multinode.sh verify",
    "connectivity_check_failed": "scripts/validate_k3s_mini_internet_multinode.sh verify",
    "recovery_check_failed": "scripts/validate_k3s_mini_internet_multinode.sh verify",
}

if overall_pass:
    next_namespace = str(summary.get("namespace", "") or "seedemu-k3s-mini-mn")
    recommended_next = f"scripts/inspect_k3s_mini_internet.sh {next_namespace}"
else:
    recommended_next = retry_by_failure.get(failure_reason, "scripts/validate_k3s_mini_internet_multinode.sh verify")

minimal_retry_command = ""
fallback_command = ""
first_evidence_file = ""
if diagnostics and isinstance(diagnostics, dict):
    minimal_retry_command = str(diagnostics.get("minimal_retry_command", "") or "")
    fallback_command = str(diagnostics.get("fallback_command", "") or "")
    first_evidence_file = str(diagnostics.get("first_evidence_file", "") or "")
if not minimal_retry_command and next_actions and isinstance(next_actions, dict):
    minimal_retry_command = str(next_actions.get("minimal_retry_command", "") or "")
if not fallback_command and next_actions and isinstance(next_actions, dict):
    fallback_command = str(next_actions.get("fallback_command", "") or "")
if not minimal_retry_command:
    minimal_retry_command = recommended_next
if not fallback_command:
    fallback_command = minimal_retry_command
if not first_evidence_file:
    first_evidence_file = str((validation_dir / "summary.json").resolve())

report = {
    "generated_at": datetime.now(timezone.utc).isoformat(),
    "validation_dir": str(validation_dir),
    "observe_dir": str(observe_dir) if observe_dir else "",
    "report_dir": str(report_dir),
    "cluster": summary.get("cluster", ""),
    "namespace": summary.get("namespace", ""),
    "cni_type": summary.get("cni_type", ""),
    "cni_master_interface": summary.get("cni_master_interface", ""),
    "placement_mode": placement_mode,
    "nodes_used": summary.get("nodes_used", 0),
    "placement_passed": placement_passed,
    "strict3_passed": strict3,
    "bgp_passed": bgp,
    "connectivity_passed": connectivity,
    "recovery_passed": recovery_passed,
    "overall_passed": overall_pass,
    "failure_reason": failure_reason,
    "failure_code": failure_code,
    "fallback_used": summary.get("fallback_used", ""),
    "duration_seconds": summary.get("duration_seconds", 0),
    "minimal_retry_command": minimal_retry_command,
    "fallback_command": fallback_command,
    "first_evidence_file": first_evidence_file,
    "placement_check": placement,
    "recovery_check": recovery,
    "diagnostics": diagnostics,
    "next_actions": next_actions,
    "observe_summary": observe_summary,
    "observe_namespace_match": observe_namespace_match,
    "evidence_files": {
        "summary": str((validation_dir / "summary.json").resolve()),
        "placement_check": str((validation_dir / "placement_check.json").resolve()),
        "bird_router151": str((validation_dir / "bird_router151.txt").resolve()),
        "bird_ix100": str((validation_dir / "bird_ix100.txt").resolve()),
        "ping_150_to_151": str((validation_dir / "ping_150_to_151.txt").resolve()),
        "recovery_check": str((validation_dir / "recovery_check.json").resolve()),
        "observe_summary": str((observe_dir / "summary.json").resolve()) if observe_dir else "",
    },
    "recommended_next_command": recommended_next,
}

(report_dir / "report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")

md_lines = [
    "# SEED Lab Run Report",
    "",
    f"- Generated at (UTC): {report['generated_at']}",
    f"- Validation dir: '{report['validation_dir']}'",
    f"- Observe dir: '{report['observe_dir']}'" if report["observe_dir"] else "- Observe dir: '(not provided)'",
    f"- Cluster: '{report['cluster']}'",
    f"- Namespace: '{report['namespace']}'",
    f"- CNI: '{report['cni_type']}' (iface: '{report['cni_master_interface']}')",
    f"- Placement mode: '{report['placement_mode']}'",
    f"- Nodes used: '{report['nodes_used']}'",
    "",
    "## Verdict",
    "",
    f"- placement_passed: '{report['placement_passed']}'",
    f"- strict3_passed: '{report['strict3_passed']}'",
    f"- bgp_passed: '{report['bgp_passed']}'",
    f"- connectivity_passed: '{report['connectivity_passed']}'",
    f"- recovery_passed: '{report['recovery_passed']}'",
    f"- overall_passed: '{report['overall_passed']}'",
    f"- failure_reason: '{report['failure_reason']}'",
    f"- failure_code: '{report['failure_code']}'",
    f"- minimal_retry_command: '{report['minimal_retry_command']}'",
    f"- fallback_command: '{report['fallback_command']}'",
    "",
    "## Evidence",
    "",
    f"- summary: '{report['evidence_files']['summary']}'",
    f"- placement_check: '{report['evidence_files']['placement_check']}'",
    f"- bird_router151: '{report['evidence_files']['bird_router151']}'",
    f"- bird_ix100: '{report['evidence_files']['bird_ix100']}'",
    f"- ping_150_to_151: '{report['evidence_files']['ping_150_to_151']}'",
    f"- recovery_check: '{report['evidence_files']['recovery_check']}'",
    f"- first_evidence_file: '{report['first_evidence_file']}'",
]

if report["evidence_files"]["observe_summary"]:
    md_lines.append(f"- observe_summary: '{report['evidence_files']['observe_summary']}'")
    md_lines.append(f"- observe_namespace_match: '{report['observe_namespace_match']}'")

md_lines.extend([
    "",
    "## Next",
    "",
    f"- Recommended command: '{report['recommended_next_command']}'",
])

(report_dir / "report.md").write_text("\n".join(md_lines) + "\n", encoding="utf-8")
PY

REPORT_INDEX_DIR="${REPO_ROOT}/output/seedlab_reports"
mkdir -p "${REPORT_INDEX_DIR}"
ln -sfn "${REPORT_DIR}" "${REPORT_INDEX_DIR}/latest"

echo "Report generated: ${REPORT_DIR}/report.json"
echo "Report generated: ${REPORT_DIR}/report.md"
