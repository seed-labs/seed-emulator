#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${SCRIPT_DIR}/env_seedemu.sh"

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
export ENTRY_SEED_REGISTRY_HOST="${SEED_REGISTRY_HOST:-192.168.122.110}"
export ENTRY_SEED_REGISTRY_PORT="${SEED_REGISTRY_PORT:-5000}"
export ENTRY_SEED_PROFILE_KIND="${SEED_PROFILE_KIND:-}"
export ENTRY_SEED_IMAGE_DISTRIBUTION_MODE="${SEED_IMAGE_DISTRIBUTION_MODE:-}"

python3 - <<'PY'
import json
import os
import re
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
                    "verify_mode": cfg.get("verify_mode", ""),
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

latest_runs = {}
if profile_root.exists():
    for pdir in sorted(profile_root.iterdir()):
        if not pdir.is_dir() or pdir.name == "latest":
            continue
        latest_link = pdir / "latest"
        target = ""
        summary_file = ""
        status = ""
        if latest_link.exists():
            try:
                target = str(latest_link.resolve())
            except Exception:
                target = str(latest_link)
            runner_summary = Path(target) / "runner_summary.json"
            if runner_summary.exists():
                summary_file = str(runner_summary)
                try:
                    data = json.loads(runner_summary.read_text(encoding="utf-8"))
                    status = data.get("status", "")
                except Exception:
                    status = ""
        latest_runs[pdir.name] = {
            "latest_dir": target,
            "runner_summary": summary_file,
            "status": status,
        }
summary["latest_profile_runs"] = latest_runs

summary["macro_tasks"] = [
    {
        "name": "Environment doctor",
        "command": f"scripts/seed_k8s_profile_runner.sh {summary['seed_profile']} doctor",
        "goal": "Check if current KVM+k3s prerequisites are healthy",
    },
    {
        "name": "Deploy from profile",
        "command": f"scripts/seed_k8s_profile_runner.sh {summary['seed_profile']} start",
        "goal": "Compile/build/deploy the selected profile",
    },
    {
        "name": "Acceptance verify",
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
markdown.append("## OS Matrix")
for item in summary["k3s_node_os_matrix"]:
    markdown.append(f"- `{item['name']}` -> `{item['os_image']}` / `{item['container_runtime']}`")
markdown.append("")
markdown.append("## Image Flow")
for step in summary["image_flow"]:
    markdown.append(f"- `{step}`")
markdown.append("")
markdown.append("## Next Commands")
for item in summary["macro_tasks"]:
    markdown.append(f"- `{item['command']}` : {item['goal']}")
markdown.append("")
markdown.append("## Core Env Vars")
markdown.append("- `KUBECONFIG`")
markdown.append("- `SEED_EXPERIMENT_PROFILE`")
markdown.append("- `SEED_NAMESPACE`")
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
