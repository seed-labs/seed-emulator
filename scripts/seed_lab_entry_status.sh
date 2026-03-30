#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${SCRIPT_DIR}/env_seedemu.sh"
source "${SCRIPT_DIR}/seed_k8s_cluster_inventory.sh"
seed_load_cluster_inventory

SEED_K3S_CLUSTER_NAME="${SEED_K3S_CLUSTER_NAME:-seedemu-k3s}"
SEED_K3S_MASTER_NAME="${SEED_K3S_MASTER_NAME:-seed-k3s-master}"
SEED_K3S_WORKER1_NAME="${SEED_K3S_WORKER1_NAME:-seed-k3s-worker1}"
SEED_K3S_WORKER2_NAME="${SEED_K3S_WORKER2_NAME:-seed-k3s-worker2}"
# Prefer profile-aware defaults over generic env defaults when possible.
SEED_EXPERIMENT_PROFILE="${SEED_EXPERIMENT_PROFILE:-mini_internet}"
PROFILE_FILE="${REPO_ROOT}/configs/seed_k8s_profiles.yaml"

profile_default() {
  local field="$1"
  python3 - <<PY
from pathlib import Path
try:
    import yaml  # type: ignore
except Exception:
    print("")
    raise SystemExit(0)
p = Path(${PROFILE_FILE@Q})
if not p.exists():
    print("")
    raise SystemExit(0)
data = yaml.safe_load(p.read_text(encoding="utf-8")) or {}
profiles = data.get("profiles", {}) if isinstance(data, dict) else {}
profile = profiles.get(${SEED_EXPERIMENT_PROFILE@Q}, {})
if isinstance(profile, dict):
    print(str(profile.get(${field@Q}, "")))
else:
    print("")
PY
}

PROFILE_DEFAULT_NAMESPACE="$(profile_default default_namespace)"
PROFILE_DEFAULT_CNI="$(profile_default default_cni_type)"

# env_seedemu.sh defaults to kind-style values. If caller did not provide
# stronger values, align entry status with selected profile defaults.
if [ -z "${SEED_NAMESPACE:-}" ] || [ "${SEED_NAMESPACE}" = "seedemu-kvtest" ]; then
  SEED_NAMESPACE="${PROFILE_DEFAULT_NAMESPACE:-seedemu-k3s-mini-mn}"
fi
if [ -z "${SEED_CNI_TYPE:-}" ] || [ "${SEED_CNI_TYPE}" = "bridge" ]; then
  SEED_CNI_TYPE="${PROFILE_DEFAULT_CNI:-macvlan}"
fi

SEED_AGENT_PROACTIVE_MODE="${SEED_AGENT_PROACTIVE_MODE:-guided}"
SEED_PLACEMENT_MODE="${SEED_PLACEMENT_MODE:-auto}"
SEED_ARTIFACT_DIR="${SEED_ARTIFACT_DIR:-${REPO_ROOT}/output/multinode_mini_validation/latest}"
SEED_OUTPUT_DIR="${SEED_OUTPUT_DIR:-${REPO_ROOT}/output/profile_runs/${SEED_EXPERIMENT_PROFILE}/latest/compiled}"
KUBECONFIG="${KUBECONFIG:-${REPO_ROOT}/output/kubeconfigs/${SEED_K3S_CLUSTER_NAME}.yaml}"

OUT_BASE="${REPO_ROOT}/output/assistant_entry"
TS="$(date +%Y%m%d_%H%M%S)"
OUT_DIR="${1:-${OUT_BASE}/${TS}}"
LATEST_LINK="${OUT_BASE}/latest"

mkdir -p "${OUT_DIR}" "${OUT_BASE}"
rm -f "${LATEST_LINK}" 2>/dev/null || true
ln -s "${OUT_DIR}" "${LATEST_LINK}" 2>/dev/null || true

log() {
  echo "[entry] $*"
}

has_cmd() {
  command -v "$1" >/dev/null 2>&1
}

capture_or_note() {
  local cmd="$1"
  local out_file="$2"
  local err_file="$3"
  if eval "${cmd}" >"${out_file}" 2>"${err_file}"; then
    return 0
  fi
  return 1
}

# virsh / KVM snapshot
if has_cmd virsh; then
  virsh list --all > "${OUT_DIR}/virsh_list_all.txt" 2>"${OUT_DIR}/virsh_list_all.err" || true
else
  echo "virsh not available" > "${OUT_DIR}/virsh_list_all.err"
fi

# kubectl snapshot
if has_cmd kubectl; then
  kubectl version --client=true > "${OUT_DIR}/kubectl_client.txt" 2>"${OUT_DIR}/kubectl_client.err" || true
  if [ -f "${KUBECONFIG}" ]; then
    capture_or_note \
      "kubectl --kubeconfig '${KUBECONFIG}' config get-contexts" \
      "${OUT_DIR}/kube_contexts.txt" \
      "${OUT_DIR}/kube_contexts.err" || true
    capture_or_note \
      "kubectl --kubeconfig '${KUBECONFIG}' config current-context" \
      "${OUT_DIR}/kube_current_context.txt" \
      "${OUT_DIR}/kube_current_context.err" || true
    capture_or_note \
      "kubectl --kubeconfig '${KUBECONFIG}' get nodes -o wide" \
      "${OUT_DIR}/kube_nodes.txt" \
      "${OUT_DIR}/kube_nodes.err" || true
    capture_or_note \
      "kubectl --kubeconfig '${KUBECONFIG}' get nodes -o json" \
      "${OUT_DIR}/kube_nodes.json" \
      "${OUT_DIR}/kube_nodes_json.err" || true
    capture_or_note \
      "kubectl --kubeconfig '${KUBECONFIG}' get ns" \
      "${OUT_DIR}/kube_namespaces.txt" \
      "${OUT_DIR}/kube_namespaces.err" || true

    if kubectl --kubeconfig "${KUBECONFIG}" get ns "${SEED_NAMESPACE}" >/dev/null 2>&1; then
      capture_or_note \
        "kubectl --kubeconfig '${KUBECONFIG}' -n '${SEED_NAMESPACE}' get pods -o wide" \
        "${OUT_DIR}/pods_wide.txt" \
        "${OUT_DIR}/pods_wide.err" || true
      capture_or_note \
        "kubectl --kubeconfig '${KUBECONFIG}' -n '${SEED_NAMESPACE}' get deploy -o wide" \
        "${OUT_DIR}/deploy_wide.txt" \
        "${OUT_DIR}/deploy_wide.err" || true
      capture_or_note \
        "kubectl --kubeconfig '${KUBECONFIG}' -n '${SEED_NAMESPACE}' get vm,vmi -o wide" \
        "${OUT_DIR}/vm_vmi.txt" \
        "${OUT_DIR}/vm_vmi.err" || true
    fi
  else
    echo "kubeconfig not found: ${KUBECONFIG}" > "${OUT_DIR}/kube_nodes.err"
  fi
else
  echo "kubectl not available" > "${OUT_DIR}/kubectl_client.err"
fi

export ENTRY_REPO_ROOT="${REPO_ROOT}"
export ENTRY_OUT_DIR="${OUT_DIR}"
export ENTRY_KUBECONFIG="${KUBECONFIG}"
export ENTRY_SEED_PROFILE="${SEED_EXPERIMENT_PROFILE}"
export ENTRY_SEED_NAMESPACE="${SEED_NAMESPACE}"
export ENTRY_SEED_CNI_TYPE="${SEED_CNI_TYPE}"
export ENTRY_SEED_AGENT_PROACTIVE_MODE="${SEED_AGENT_PROACTIVE_MODE}"
export ENTRY_SEED_PLACEMENT_MODE="${SEED_PLACEMENT_MODE}"
export ENTRY_SEED_ARTIFACT_DIR="${SEED_ARTIFACT_DIR}"
export ENTRY_SEED_OUTPUT_DIR="${SEED_OUTPUT_DIR}"
export ENTRY_MASTER_NAME="${SEED_K3S_MASTER_NAME}"
export ENTRY_WORKER1_NAME="${SEED_K3S_WORKER1_NAME}"
export ENTRY_WORKER2_NAME="${SEED_K3S_WORKER2_NAME}"
export ENTRY_MASTER_IP="${SEED_K3S_MASTER_IP:-}"
export ENTRY_WORKER1_IP="${SEED_K3S_WORKER1_IP:-}"
export ENTRY_WORKER2_IP="${SEED_K3S_WORKER2_IP:-}"
export ENTRY_SEED_K3S_USER="${SEED_K3S_USER:-ubuntu}"
export ENTRY_SEED_K3S_SSH_KEY="${SEED_K3S_SSH_KEY:-$HOME/.ssh/id_ed25519}"
export ENTRY_SEED_REGISTRY_HOST="${SEED_REGISTRY_HOST:-192.168.122.110}"
export ENTRY_SEED_REGISTRY_PORT="${SEED_REGISTRY_PORT:-5000}"
export ENTRY_SEED_PROFILE_KIND="${SEED_PROFILE_KIND:-}"
export ENTRY_SEED_IMAGE_DISTRIBUTION_MODE="${SEED_IMAGE_DISTRIBUTION_MODE:-}"
export ENTRY_CLUSTER_INVENTORY_NAME="${SEED_CLUSTER_INVENTORY_NAME:-}"
export ENTRY_CLUSTER_INVENTORY_PATH="${SEED_CLUSTER_INVENTORY_PATH:-}"
export ENTRY_CLUSTER_INVENTORY_LOADED="${SEED_CLUSTER_INVENTORY_LOADED:-false}"
export ENTRY_CLUSTER_MAX_VALIDATED_TOPOLOGY_SIZE="${SEED_CLUSTER_MAX_VALIDATED_TOPOLOGY_SIZE:-0}"

python3 - <<'PY'
import json
import os
import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path

try:
    import yaml  # type: ignore
except Exception:
    yaml = None

repo_root = Path(os.environ["ENTRY_REPO_ROOT"])
out_dir = Path(os.environ["ENTRY_OUT_DIR"])
profile_file = repo_root / "configs/seed_k8s_profiles.yaml"
profile_root = repo_root / "output/profile_runs"
kubeconfig_path = Path(os.environ["ENTRY_KUBECONFIG"])

summary = {
    "generated_at": datetime.now(timezone.utc).isoformat(),
    "repo_root": str(repo_root),
    "kubeconfig": os.environ["ENTRY_KUBECONFIG"],
    "seed_profile": os.environ["ENTRY_SEED_PROFILE"],
    "seed_namespace": os.environ["ENTRY_SEED_NAMESPACE"],
    "seed_cni_type": os.environ["ENTRY_SEED_CNI_TYPE"],
    "seed_agent_proactive_mode": os.environ["ENTRY_SEED_AGENT_PROACTIVE_MODE"],
    "seed_placement_mode": os.environ["ENTRY_SEED_PLACEMENT_MODE"],
    "seed_artifact_dir": os.environ["ENTRY_SEED_ARTIFACT_DIR"],
    "seed_output_dir": os.environ["ENTRY_SEED_OUTPUT_DIR"],
    "registry_host": os.environ["ENTRY_SEED_REGISTRY_HOST"],
    "registry_port": os.environ["ENTRY_SEED_REGISTRY_PORT"],
    "cluster_inventory_name": os.environ.get("ENTRY_CLUSTER_INVENTORY_NAME", ""),
    "cluster_inventory_path": os.environ.get("ENTRY_CLUSTER_INVENTORY_PATH", ""),
    "cluster_inventory_loaded": os.environ.get("ENTRY_CLUSTER_INVENTORY_LOADED", "false") == "true",
    "cluster_max_validated_topology_size": int(os.environ.get("ENTRY_CLUSTER_MAX_VALIDATED_TOPOLOGY_SIZE", "0") or 0),
}

profile_kind = os.environ.get("ENTRY_SEED_PROFILE_KIND", "").strip() or (
    "scale" if summary["seed_profile"] == "real_topology_rr_scale" else "baseline"
)
summary["profile_kind"] = profile_kind

image_distribution_mode = os.environ.get("ENTRY_SEED_IMAGE_DISTRIBUTION_MODE", "").strip()
if not image_distribution_mode:
    if summary["seed_profile"] in {"real_topology_rr", "real_topology_rr_scale"}:
        image_distribution_mode = "preload"
    else:
        image_distribution_mode = "registry"
summary["image_distribution_mode"] = image_distribution_mode

host_os = "unknown"
os_release = Path("/etc/os-release")
if os_release.exists():
    data = {}
    for raw in os_release.read_text(encoding="utf-8", errors="ignore").splitlines():
        if "=" not in raw:
            continue
        key, value = raw.split("=", 1)
        data[key.strip()] = value.strip().strip('"')
    host_os = data.get("PRETTY_NAME") or data.get("NAME") or "unknown"
summary["host_os"] = host_os

ssh_key_path = str(Path(os.environ.get("ENTRY_SEED_K3S_SSH_KEY", "")).expanduser())
ssh_user = os.environ.get("ENTRY_SEED_K3S_USER", "ubuntu")
summary["ssh_user"] = ssh_user
summary["ssh_key_path"] = ssh_key_path
summary["ssh_key_exists"] = Path(ssh_key_path).is_file()

ssh_targets = [
    (os.environ.get("ENTRY_MASTER_NAME", ""), os.environ.get("ENTRY_MASTER_IP", "")),
    (os.environ.get("ENTRY_WORKER1_NAME", ""), os.environ.get("ENTRY_WORKER1_IP", "")),
    (os.environ.get("ENTRY_WORKER2_NAME", ""), os.environ.get("ENTRY_WORKER2_IP", "")),
]
ssh_access = []
if summary["ssh_key_exists"]:
    for name, ip in ssh_targets:
        if not name or not ip:
            continue
        command = [
            "ssh",
            "-o",
            "StrictHostKeyChecking=no",
            "-o",
            "UserKnownHostsFile=/dev/null",
            "-o",
            "LogLevel=ERROR",
            "-o",
            "BatchMode=yes",
            "-o",
            "IdentitiesOnly=yes",
            "-o",
            "IdentityAgent=none",
            "-o",
            "ConnectTimeout=8",
            "-n",
            "-i",
            ssh_key_path,
            f"{ssh_user}@{ip}",
            "hostname",
        ]
        result = subprocess.run(command, text=True, capture_output=True, check=False, timeout=15)
        ssh_access.append(
            {
                "name": name,
                "management_ip": ip,
                "reachable": result.returncode == 0,
                "hostname": result.stdout.strip(),
                "error": "" if result.returncode == 0 else " ".join((result.stderr or result.stdout).strip().split()),
            }
        )
else:
    for name, ip in ssh_targets:
        if not name or not ip:
            continue
        ssh_access.append(
            {
                "name": name,
                "management_ip": ip,
                "reachable": False,
                "hostname": "",
                "error": f"key not found: {ssh_key_path}",
            }
        )

summary["ssh_access"] = ssh_access
summary["ssh_access_ok"] = bool(ssh_access) and all(item.get("reachable") for item in ssh_access)
(out_dir / "ssh_access.json").write_text(json.dumps({
    "ssh_user": ssh_user,
    "ssh_key_path": ssh_key_path,
    "ssh_key_exists": summary["ssh_key_exists"],
    "ssh_access_ok": summary["ssh_access_ok"],
    "nodes": ssh_access,
}, indent=2), encoding="utf-8")

profiles = []
if profile_file.exists() and yaml is not None:
    loaded = yaml.safe_load(profile_file.read_text(encoding="utf-8")) or {}
    entries = loaded.get("profiles", {}) if isinstance(loaded, dict) else {}
    if isinstance(entries, dict):
        for profile_id, cfg in entries.items():
            if not isinstance(cfg, dict):
                continue
            profiles.append(
                {
                    "profile_id": profile_id,
                    "compile_script": cfg.get("compile_script", ""),
                    "default_namespace": cfg.get("default_namespace", ""),
                    "default_cni_type": cfg.get("default_cni_type", ""),
                    "default_topology_size": cfg.get("default_topology_size", 0),
                    "verify_mode": cfg.get("verify_mode", ""),
                    "support_tier": cfg.get("support_tier", ""),
                    "acceptance_level": cfg.get("acceptance_level", ""),
                    "capacity_gate": cfg.get("capacity_gate", ""),
                }
            )

summary["available_profiles"] = sorted(profiles, key=lambda item: item["profile_id"])

container_base_image = "unknown"
dockerfile = repo_root / "docker_images/seedemu-base/Dockerfile"
if dockerfile.exists():
    for raw in dockerfile.read_text(encoding="utf-8", errors="ignore").splitlines():
        line = raw.strip()
        if line.upper().startswith("FROM "):
            container_base_image = line.split(None, 1)[1]
            break
summary["container_base_image"] = container_base_image

virsh_file = out_dir / "virsh_list_all.txt"
expected_vms = [
    os.environ["ENTRY_MASTER_NAME"],
    os.environ["ENTRY_WORKER1_NAME"],
    os.environ["ENTRY_WORKER2_NAME"],
]
vm_status = {name: "unknown" for name in expected_vms}
if virsh_file.exists():
    for line in virsh_file.read_text(encoding="utf-8", errors="ignore").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("-") or stripped.lower().startswith("id"):
            continue
        parts = re.split(r"\s{2,}", stripped)
        if len(parts) < 3:
            continue
        name = parts[1].strip()
        state = parts[2].strip().lower()
        if name in vm_status:
            vm_status[name] = state

summary["kvm"] = {
    "virsh_available": virsh_file.exists(),
    "expected_vms": expected_vms,
    "expected_vm_state": vm_status,
    "expected_vm_running_count": sum(1 for v in vm_status.values() if "running" in v),
}

nodes_file = out_dir / "kube_nodes.txt"
kube_nodes = {"total": 0, "ready": 0}
if nodes_file.exists():
    lines = [ln for ln in nodes_file.read_text(encoding="utf-8", errors="ignore").splitlines() if ln.strip()]
    for idx, line in enumerate(lines):
        if idx == 0 and "STATUS" in line:
            continue
        cols = line.split()
        if len(cols) < 2:
            continue
        kube_nodes["total"] += 1
        if cols[1].startswith("Ready"):
            kube_nodes["ready"] += 1

summary["kubernetes"] = {
    "kubectl_available": (out_dir / "kubectl_client.txt").exists(),
    "kubeconfig_exists": kubeconfig_path.exists(),
    "nodes": kube_nodes,
    "current_context": (out_dir / "kube_current_context.txt").read_text(encoding="utf-8").strip()
    if (out_dir / "kube_current_context.txt").exists()
    else "",
}

active_seed_namespaces = []
namespaces_file = out_dir / "kube_namespaces.txt"
if namespaces_file.exists():
    lines = [ln for ln in namespaces_file.read_text(encoding="utf-8", errors="ignore").splitlines() if ln.strip()]
    for idx, line in enumerate(lines):
        if idx == 0 and "STATUS" in line:
            continue
        cols = line.split()
        if len(cols) < 2:
            continue
        name, status = cols[0], cols[1]
        if name.startswith("seedemu-"):
            active_seed_namespaces.append({"name": name, "status": status})
summary["active_seed_namespaces"] = active_seed_namespaces

node_matrix = []
nodes_json = out_dir / "kube_nodes.json"
if nodes_json.exists():
    try:
        loaded = json.loads(nodes_json.read_text(encoding="utf-8"))
    except Exception:
        loaded = {}
    for item in loaded.get("items", []) if isinstance(loaded, dict) else []:
        metadata = item.get("metadata", {}) or {}
        node_info = (item.get("status", {}) or {}).get("nodeInfo", {}) or {}
        node_matrix.append(
            {
                "name": metadata.get("name", ""),
                "os_image": node_info.get("osImage", ""),
                "kernel_version": node_info.get("kernelVersion", ""),
                "container_runtime": node_info.get("containerRuntimeVersion", ""),
            }
        )
summary["k3s_node_os_matrix"] = node_matrix
summary["node_os_matrix"] = node_matrix

if image_distribution_mode == "preload":
    summary["image_flow"] = [
        "local compile",
        "scp compiled artifacts to seed-k3s-master",
        f"run build_images.sh on {summary['registry_host']}",
        "preload images into master/worker containerd",
        "kubectl apply uses preloaded images",
    ]
else:
    summary["image_flow"] = [
        "local compile",
        "scp compiled artifacts to seed-k3s-master",
        f"run build_images.sh on {summary['registry_host']}",
        f"push images to {summary['registry_host']}:{summary['registry_port']}",
        "workers pull images from master registry",
    ]

def load_json(path: Path) -> dict:
    if not path.exists():
        return {}
    try:
        loaded = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}
    return loaded if isinstance(loaded, dict) else {}


def iso_to_epoch(value: str) -> float:
    text = str(value or "").strip()
    if not text:
        return 0.0
    try:
        return datetime.fromisoformat(text.replace("Z", "+00:00")).timestamp()
    except Exception:
        return 0.0


def build_run_record(run_dir: Path) -> dict:
    runner_summary_path = run_dir / "runner_summary.json"
    validation_summary_path = run_dir / "validation" / "summary.json"
    timing_path = run_dir / "validation" / "timing.json"
    report_path = run_dir / "report" / "report.json"

    runner_data = load_json(runner_summary_path)
    validation_data = load_json(validation_summary_path)
    timing_data = load_json(timing_path)
    report_data = load_json(report_path)

    runner_action = str(validation_data.get("runner_action", "") or runner_data.get("action", "") or "")
    runner_status = str(validation_data.get("runner_status", "") or runner_data.get("status", "") or "")
    namespace = str(validation_data.get("namespace", "") or report_data.get("namespace", "") or "")
    nodes_used = int(validation_data.get("nodes_used", report_data.get("nodes_used", 0)) or 0)
    expected_nodes = int(validation_data.get("expected_nodes", 0) or 0)
    validation_duration_seconds = int(
        validation_data.get("validation_duration_seconds", validation_data.get("duration_seconds", 0)) or 0
    )
    build_duration = int(timing_data.get("build_duration_seconds", validation_data.get("build_duration_seconds", 0)) or 0)
    up_duration = int(timing_data.get("up_duration_seconds", validation_data.get("up_duration_seconds", 0)) or 0)
    phase_duration = int(
        timing_data.get("phase_start_duration_seconds", validation_data.get("phase_start_duration_seconds", 0)) or 0
    )
    start_bird_duration = int(
        timing_data.get("start_bird_duration_seconds", validation_data.get("start_bird_duration_seconds", 0)) or 0
    )
    start_kernel_duration = int(
        timing_data.get("start_kernel_duration_seconds", validation_data.get("start_kernel_duration_seconds", 0)) or 0
    )
    pipeline_duration_seconds = max(
        int(report_data.get("pipeline_duration_seconds", validation_data.get("pipeline_duration_seconds", 0)) or 0),
        build_duration + up_duration + phase_duration + start_bird_duration + start_kernel_duration + validation_duration_seconds,
        validation_duration_seconds,
    )

    acceptance_status = str(
        report_data.get("acceptance_status", "")
        or validation_data.get("acceptance_status", "")
        or ("PASS" if report_data.get("overall_passed") else "")
    )
    if not acceptance_status:
        if runner_status != "PASS":
            acceptance_status = "FAIL"
        elif runner_action in {"verify", "observe", "report", "all"}:
            acceptance_status = "FAIL"
        elif runner_action:
            acceptance_status = "PARTIAL"
        else:
            acceptance_status = "NOT_RUN"

    overall_passed = report_data.get("overall_passed")
    if overall_passed is None and acceptance_status:
        overall_passed = acceptance_status == "PASS"

    sort_epoch = max(
        iso_to_epoch(validation_data.get("runner_finished_at", "")),
        iso_to_epoch(validation_data.get("runner_started_at", "")),
        iso_to_epoch(validation_data.get("generated_at", "")),
        iso_to_epoch(report_data.get("generated_at", "")),
        iso_to_epoch(runner_data.get("finished_at", "")),
        iso_to_epoch(runner_data.get("started_at", "")),
        run_dir.stat().st_mtime,
    )

    return {
        "run_id": run_dir.name,
        "latest_dir": str(run_dir),
        "runner_summary": str(runner_summary_path) if runner_summary_path.exists() else "",
        "validation_summary": str(validation_summary_path) if validation_summary_path.exists() else "",
        "report": str(report_path) if report_path.exists() else "",
        "status": runner_status,
        "runner_action": runner_action,
        "acceptance_status": acceptance_status,
        "overall_passed": overall_passed,
        "namespace": namespace,
        "nodes_used": nodes_used,
        "expected_nodes": expected_nodes,
        "pipeline_duration_seconds": pipeline_duration_seconds,
        "validation_duration_seconds": validation_duration_seconds,
        "first_evidence_file": str(report_data.get("first_evidence_file", "") or ""),
        "_sort_epoch": sort_epoch,
    }


def clean_record(item: dict) -> dict:
    return {k: v for k, v in item.items() if not str(k).startswith("_")}


latest_runs = {}
all_run_records = []
if profile_root.exists():

    for pdir in sorted(profile_root.iterdir()):
        if not pdir.is_dir() or pdir.name == "latest":
            continue

        run_dirs = [child for child in pdir.iterdir() if child.is_dir() and child.name != "latest"]
        records = [build_run_record(run_dir) for run_dir in run_dirs]
        all_run_records.extend(records)
        records.sort(
            key=lambda item: (float(item.get("_sort_epoch", 0.0) or 0.0), item.get("run_id", "")),
            reverse=True,
        )
        latest_attempted = records[0] if records else {}
        latest_verified = next(
            (
                item
                for item in records
                if item.get("acceptance_status") in {"PASS", "FAIL", "CAPACITY_GATED"}
                or item.get("runner_action") in {"verify", "observe", "report", "all"}
            ),
            {},
        )
        latest_accepted = next(
            (
                item
                for item in records
                if item.get("report") and item.get("acceptance_status") == "PASS"
            ),
            {},
        )

        latest_runs[pdir.name] = {
            **clean_record(latest_attempted),
            "latest_attempted_run": clean_record(latest_attempted),
            "latest_verified_run": clean_record(latest_verified),
            "latest_accepted_run": clean_record(latest_accepted),
        }
summary["latest_profile_runs"] = latest_runs

all_run_records.sort(
    key=lambda item: (float(item.get("_sort_epoch", 0.0) or 0.0), item.get("run_id", "")),
    reverse=True,
)
summary["latest_run"] = next((clean_record(item) for item in all_run_records), None)
summary["latest_verified_run"] = next(
    (
        clean_record(item)
        for item in all_run_records
        if item.get("acceptance_status") in {"PASS", "FAIL", "CAPACITY_GATED"}
        or item.get("runner_action") in {"verify", "observe", "report", "all"}
    ),
    None,
)
summary["latest_accepted_run"] = next(
    (
        clean_record(item)
        for item in all_run_records
        if item.get("report") and item.get("acceptance_status") == "PASS"
    ),
    None,
)

summary["macro_tasks"] = [
    {
        "name": "Environment doctor",
        "command": f"scripts/seed_k8s_profile_runner.sh {summary['seed_profile']} doctor",
        "goal": "Check if current KVM+k3s prerequisites are healthy",
    },
    {
        "name": "Compile profile",
        "command": f"scripts/seed_k8s_profile_runner.sh {summary['seed_profile']} compile",
        "goal": "Compile the selected topology into Kubernetes output",
    },
    {
        "name": "Build images",
        "command": f"scripts/seed_k8s_profile_runner.sh {summary['seed_profile']} build",
        "goal": "Build and distribute images for the latest compiled run",
    },
    {
        "name": "Deploy workloads",
        "command": f"scripts/seed_k8s_profile_runner.sh {summary['seed_profile']} deploy",
        "goal": "Apply the compiled manifests without starting bird",
    },
    {
        "name": "Start bird",
        "command": f"scripts/seed_k8s_profile_runner.sh {summary['seed_profile']} start-bird",
        "goal": "Start bird routing processes",
    },
    {
        "name": "Switch kernel",
        "command": f"scripts/seed_k8s_profile_runner.sh {summary['seed_profile']} start-kernel",
        "goal": "Enable the kernel export stage",
    },
    {
        "name": "Verify acceptance",
        "command": f"scripts/seed_k8s_profile_runner.sh {summary['seed_profile']} verify",
        "goal": "Run strict verification on placement/BGP/connectivity/recovery",
    },
    {
        "name": "Observe runtime",
        "command": f"scripts/seed_k8s_profile_runner.sh {summary['seed_profile']} observe",
        "goal": "Capture pod/node/network evidence for review",
    },
    {
        "name": "Full pipeline",
        "command": f"scripts/seed_k8s_profile_runner.sh {summary['seed_profile']} all",
        "goal": "Run full lifecycle with report artifacts",
    },
]

summary["kubectl_quickstart"] = {
    "set_namespace": f"export NS={summary['seed_namespace']}",
    "nodes": f"kubectl --kubeconfig {summary['kubeconfig']} get nodes -o wide",
    "pods": f"kubectl --kubeconfig {summary['kubeconfig']} -n {summary['seed_namespace']} get pods -o wide",
    "deployments": f"kubectl --kubeconfig {summary['kubeconfig']} -n {summary['seed_namespace']} get deploy -o wide",
    "vmi": f"kubectl --kubeconfig {summary['kubeconfig']} -n {summary['seed_namespace']} get vm,vmi -o wide",
    "events": f"kubectl --kubeconfig {summary['kubeconfig']} -n {summary['seed_namespace']} get events --sort-by=.lastTimestamp | tail -n 40",
}

summary_path = out_dir / "summary.json"
summary_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")

markdown = []
markdown.append("# SEED Lab Entry Status")
markdown.append("")
markdown.append(f"- Summary JSON: `{summary_path}`")
markdown.append(f"- Namespace: `{summary['seed_namespace']}`")
markdown.append(f"- Profile: `{summary['seed_profile']}`")
markdown.append(f"- Profile kind: `{summary['profile_kind']}`")
markdown.append(f"- Cluster inventory: `{summary['cluster_inventory_name'] or 'not-set'}`")
markdown.append(f"- Placement mode: `{summary['seed_placement_mode']}`")
markdown.append(f"- Registry: `{summary['registry_host']}:{summary['registry_port']}`")
markdown.append(f"- Image distribution: `{summary['image_distribution_mode']}`")
markdown.append(f"- Host OS: `{summary['host_os']}`")
markdown.append(f"- Container base image: `{summary['container_base_image']}`")
markdown.append(
    f"- K8s Nodes Ready: `{summary['kubernetes']['nodes']['ready']}/{summary['kubernetes']['nodes']['total']}`"
)
markdown.append(
    f"- Expected KVM Running: `{summary['kvm']['expected_vm_running_count']}/{len(expected_vms)}`"
)
markdown.append("")
markdown.append("## Active SEED Namespaces")
if summary["active_seed_namespaces"]:
    for item in summary["active_seed_namespaces"]:
        markdown.append(f"- `{item['name']}` -> `{item['status']}`")
else:
    markdown.append("- none")
markdown.append("")
markdown.append("## OS Matrix")
for item in summary["node_os_matrix"]:
    markdown.append(f"- `{item['name']}` -> `{item['os_image']}` / `{item['container_runtime']}`")
markdown.append("")
markdown.append("## SSH Access")
markdown.append(f"- `user={summary['ssh_user']}` key=`{summary['ssh_key_path']}` exists=`{summary['ssh_key_exists']}` all_ok=`{summary['ssh_access_ok']}`")
for item in summary["ssh_access"]:
    markdown.append(
        f"- `{item['name']}` `{item['management_ip']}` reachable=`{item['reachable']}` hostname=`{item['hostname']}`"
    )
markdown.append("")
markdown.append("## Image Flow")
for step in summary["image_flow"]:
    markdown.append(f"- `{step}`")
markdown.append("")
markdown.append("## Latest Profile Runs")
for profile_id, item in sorted(summary["latest_profile_runs"].items()):
    markdown.append(
        f"- `{profile_id}` -> attempted=`{item.get('status', '') or 'unknown'}` "
        f"acceptance=`{item.get('acceptance_status', 'NOT_RUN')}` ns=`{item.get('namespace', '')}` "
        f"nodes=`{item.get('nodes_used', 0)}` expected=`{item.get('expected_nodes', 0)}` "
        f"total=`{item.get('pipeline_duration_seconds', 0)}s` run=`{item.get('latest_dir', '')}`"
    )
    verified = item.get("latest_verified_run") or {}
    accepted = item.get("latest_accepted_run") or {}
    if verified:
        markdown.append(
            f"- latest_verified=`{verified.get('run_id', '')}` status=`{verified.get('acceptance_status', '')}`"
        )
    if accepted:
        markdown.append(
            f"- latest_accepted=`{accepted.get('run_id', '')}` status=`{accepted.get('acceptance_status', '')}`"
        )
markdown.append("")
markdown.append("## Next Commands")
for item in summary["macro_tasks"]:
    markdown.append(f"- `{item['command']}` : {item['goal']}")
markdown.append("")
markdown.append("## Core Env Vars")
markdown.append("- `KUBECONFIG`")
markdown.append("- `SEED_EXPERIMENT_PROFILE`")
markdown.append("- `SEED_NAMESPACE`")
markdown.append("- `SEED_K3S_SSH_KEY`")
markdown.append("- `SEED_CNI_TYPE`")
markdown.append("- `SEED_PLACEMENT_MODE`")
markdown.append("- `SEED_AGENT_PROACTIVE_MODE`")
markdown.append("- `SEED_ARTIFACT_DIR`")
markdown.append("- `SEED_OUTPUT_DIR`")
(out_dir / "summary.md").write_text("\n".join(markdown) + "\n", encoding="utf-8")
PY

log "summary: ${OUT_DIR}/summary.json"
if [ -f "${OUT_DIR}/summary.md" ]; then
  log "summary_md: ${OUT_DIR}/summary.md"
fi
if [ -f "${OUT_DIR}/kube_nodes.txt" ]; then
  log "kube_nodes: ${OUT_DIR}/kube_nodes.txt"
fi
if [ -f "${OUT_DIR}/virsh_list_all.txt" ]; then
  log "virsh: ${OUT_DIR}/virsh_list_all.txt"
fi
