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
import os
from datetime import datetime, timezone
from pathlib import Path

validation_dir = Path(${VALIDATION_DIR@Q}).resolve()
observe_dir_raw = ${OBSERVE_DIR@Q}
observe_dir = Path(observe_dir_raw).resolve() if observe_dir_raw else None
report_dir = Path(${REPORT_DIR@Q}).resolve()
report_dir.mkdir(parents=True, exist_ok=True)

summary = json.loads((validation_dir / "summary.json").read_text(encoding="utf-8"))
profile_id = str(summary.get("profile", "") or summary.get("profile_id", "") or "")

def detect_host_os() -> str:
    os_release = Path("/etc/os-release")
    if not os_release.exists():
        return "unknown"
    data = {}
    for raw in os_release.read_text(encoding="utf-8", errors="ignore").splitlines():
        if "=" not in raw:
            continue
        key, value = raw.split("=", 1)
        data[key.strip()] = value.strip().strip('"')
    return data.get("PRETTY_NAME") or data.get("NAME") or "unknown"

def load_nodes_matrix() -> list[dict]:
    candidates = [validation_dir / "nodes.json", validation_dir / "kube_nodes.json"]
    for path in candidates:
        loaded = load_json_if_exists(path)
        if not isinstance(loaded, dict):
            continue
        items = loaded.get("items", [])
        matrix = []
        for item in items:
            if not isinstance(item, dict):
                continue
            metadata = item.get("metadata", {}) or {}
            status = item.get("status", {}) or {}
            node_info = status.get("nodeInfo", {}) or {}
            matrix.append(
                {
                    "name": metadata.get("name", ""),
                    "os_image": node_info.get("osImage", ""),
                    "kernel_version": node_info.get("kernelVersion", ""),
                    "container_runtime": node_info.get("containerRuntimeVersion", ""),
                }
            )
        if matrix:
            return matrix
    return []

def detect_container_base_series() -> str:
    dockerfile = Path(${REPO_ROOT@Q}) / "docker_images/seedemu-base/Dockerfile"
    if not dockerfile.exists():
        return "unknown"
    for raw in dockerfile.read_text(encoding="utf-8", errors="ignore").splitlines():
        line = raw.strip()
        if line.upper().startswith("FROM "):
            return line.split(None, 1)[1]
    return "unknown"


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
minimal_retry_command = ""
fallback_command = ""
first_evidence_file = ""
if diagnostics and isinstance(diagnostics, dict):
    failure_code = str(diagnostics.get("failure_code", failure_code) or failure_code)
    minimal_retry_command = str(diagnostics.get("minimal_retry_command", "") or "")
    fallback_command = str(diagnostics.get("fallback_command", "") or "")
    first_evidence_file = str(diagnostics.get("first_evidence_file", "") or "")

if (observe_namespace_match is False) and not failure_code:
    failure_code = "OBSERVE_NAMESPACE_MISMATCH"

if profile_id in {"real_topology_rr", "real_topology_rr_scale"}:
    retry_by_failure = {
        "kubeconfig_fetch_failed": "scripts/k3s_fetch_kubeconfig.sh && scripts/validate_k3s_real_topology_multinode.sh preflight",
        "kubeconfig_not_found_after_fetch": "scripts/k3s_fetch_kubeconfig.sh && scripts/validate_k3s_real_topology_multinode.sh preflight",
        "ssh_key_not_found": "export SEED_K3S_SSH_KEY=/path/to/key && scripts/validate_k3s_real_topology_multinode.sh preflight",
        "compile_missing_k8s_yaml": "scripts/validate_k3s_real_topology_multinode.sh compile",
        "compile_missing_build_script": "scripts/validate_k3s_real_topology_multinode.sh compile",
        "registry_timeout": f"scripts/seed_k8s_profile_runner.sh {profile_id} start",
        "build_failed": "scripts/validate_k3s_real_topology_multinode.sh build",
        "deploy_wait_timeout_or_failure": "scripts/validate_k3s_real_topology_multinode.sh deploy",
        "placement_check_failed": "scripts/validate_k3s_real_topology_multinode.sh verify",
        "bgp_not_established": "scripts/validate_k3s_real_topology_multinode.sh verify",
        "strict3_not_supported": "export SEED_PLACEMENT_MODE=auto && scripts/validate_k3s_real_topology_multinode.sh verify",
    }
else:
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
    next_namespace = str(summary.get("namespace", "") or "")
    if profile_id == "mini_internet":
        recommended_next = f"scripts/inspect_k3s_mini_internet.sh {next_namespace or 'seedemu-k3s-mini-mn'}"
    else:
        recommended_next = f"kubectl -n {next_namespace or 'default'} get pods -o wide"
else:
    recommended_next = retry_by_failure.get(failure_reason, minimal_retry_command or "scripts/validate_k3s_mini_internet_multinode.sh verify")

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

evidence_files = {}
def add_evidence(key: str, path: Path):
    if path.exists():
        evidence_files[key] = str(path.resolve())

add_evidence("summary", validation_dir / "summary.json")
add_evidence("diagnostics", validation_dir / "diagnostics.json")
add_evidence("next_actions", validation_dir / "next_actions.json")

if profile_id in {"real_topology_rr", "real_topology_rr_scale"}:
    add_evidence("counts", validation_dir / "counts.json")
    add_evidence("placement", validation_dir / "placement.tsv")
    add_evidence("nodes", validation_dir / "nodes_wide.txt")
    add_evidence("nodes_json", validation_dir / "nodes.json")
    add_evidence("pods_wide", validation_dir / "pods_wide.txt")
    add_evidence("deployments_wide", validation_dir / "deployments_wide.txt")
    add_evidence("bird_sample", validation_dir / "bird_sample.txt")
else:
    add_evidence("placement", validation_dir / "placement.tsv")
    add_evidence("placement_check", validation_dir / "placement_check.json")
    add_evidence("bird_router151", validation_dir / "bird_router151.txt")
    add_evidence("bird_ix100", validation_dir / "bird_ix100.txt")
    add_evidence("ping_150_to_151", validation_dir / "ping_150_to_151.txt")
    add_evidence("recovery_check", validation_dir / "recovery_check.json")

if observe_dir:
    add_evidence("observe_summary", observe_dir / "summary.json")

host_os = detect_host_os()
node_os_matrix = load_nodes_matrix()
container_base_image = detect_container_base_series()
registry = str(summary.get("registry", "") or "")
registry_host = str(summary.get("registry_host", "") or "")
registry_port = str(summary.get("registry_port", "") or "")
profile_kind = str(summary.get("profile_kind", "baseline") or "baseline")
image_distribution_mode = str(summary.get("image_distribution_mode", "") or "")
if not image_distribution_mode:
    image_distribution_mode = "preload" if profile_id in {"real_topology_rr", "real_topology_rr_scale"} else "registry"

if image_distribution_mode == "preload":
    image_flow = [
        "local compile",
        "scp compiled artifacts to seed-k3s-master",
        f"run build_images.sh on {registry_host or '192.168.122.110'}",
        "preload images into master/worker containerd",
        "kubectl apply uses preloaded images",
    ]
else:
    image_flow = [
        "local compile",
        "scp compiled artifacts to seed-k3s-master",
        f"run build_images.sh on {registry_host or '192.168.122.110'}",
        f"push images to {registry or '192.168.122.110:5000'}",
        "workers pull images from master registry",
    ]

report = {
    "generated_at": datetime.now(timezone.utc).isoformat(),
    "profile_id": profile_id,
    "validation_dir": str(validation_dir),
    "observe_dir": str(observe_dir) if observe_dir else "",
    "report_dir": str(report_dir),
    "cluster": summary.get("cluster", ""),
    "namespace": summary.get("namespace", ""),
    "profile_kind": profile_kind,
    "cni_type": summary.get("cni_type", ""),
    "cni_master_interface": summary.get("cni_master_interface", ""),
    "registry": registry,
    "registry_host": registry_host,
    "registry_port": registry_port,
    "image_distribution_mode": image_distribution_mode,
    "host_os": host_os,
    "node_os_matrix": node_os_matrix,
    "container_base_image": container_base_image,
    "image_flow": image_flow,
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
    "evidence_files": evidence_files,
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
    f"- Profile kind: '{report['profile_kind']}'",
    f"- CNI: '{report['cni_type']}' (iface: '{report['cni_master_interface']}')",
    f"- Registry: '{report['registry']}'",
    f"- Image distribution: '{report['image_distribution_mode']}'",
    f"- Host OS: '{report['host_os']}'",
    f"- Container base image: '{report['container_base_image']}'",
    f"- Placement mode: '{report['placement_mode']}'",
    f"- Nodes used: '{report['nodes_used']}'",
    "",
    "## Environment",
    "",
    *(f"- node_os: '{item['name']} | {item['os_image']} | {item['container_runtime']}'" for item in report["node_os_matrix"]),
    *(f"- image_flow: '{step}'" for step in report["image_flow"]),
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
    *(f"- {k}: '{v}'" for k, v in report["evidence_files"].items()),
    f"- first_evidence_file: '{report['first_evidence_file']}'",
]

if "observe_summary" in report["evidence_files"]:
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
