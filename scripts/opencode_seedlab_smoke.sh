#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TS="$(date +%Y%m%d_%H%M%S)"
ARTIFACT_BASE="${REPO_ROOT}/output/opencode_seedlab_smoke"
ARTIFACT_DIR="${ARTIFACT_BASE}/${TS}"
LATEST_LINK="${ARTIFACT_BASE}/latest"

mkdir -p "${ARTIFACT_DIR}"
rm -f "${LATEST_LINK}" 2>/dev/null || true
ln -s "${ARTIFACT_DIR}" "${LATEST_LINK}"

log() {
    printf '[smoke] %s\n' "$*"
}

pass() {
    if [[ "${SMOKE_VERBOSE}" == "true" ]]; then
        log "PASS: $1"
    fi
}

fail() {
    log "FAIL: $1"
    export SMOKE_FAIL=1
}

warn() {
    log "WARN: $1"
    export SMOKE_WARN=1
}

SMOKE_FAIL=0
SMOKE_WARN=0
SMOKE_VERBOSE="${SEED_SMOKE_VERBOSE:-false}"

if [[ -f "${REPO_ROOT}/scripts/env_seedemu.sh" ]]; then
    # shellcheck source=/dev/null
    source "${REPO_ROOT}/scripts/env_seedemu.sh"
    if [[ "${SMOKE_VERBOSE}" == "true" ]]; then
        pass "env_seedemu.sh sourced"
    fi
else
    fail "missing scripts/env_seedemu.sh"
fi

required_files=(
    "${REPO_ROOT}/configs/seed_k8s_profiles.yaml"
    "${REPO_ROOT}/configs/seed_failure_action_map.yaml"
    "${REPO_ROOT}/scripts/k3s_fetch_kubeconfig.sh"
    "${REPO_ROOT}/scripts/validate_k3s_mini_internet_multinode.sh"
    "${REPO_ROOT}/scripts/validate_k3s_real_topology_multinode.sh"
    "${REPO_ROOT}/scripts/inspect_k3s_mini_internet.sh"
    "${REPO_ROOT}/scripts/seed_lab_entry_status.sh"
    "${REPO_ROOT}/scripts/bootstrap_seed_lab_env.sh"
    "${REPO_ROOT}/scripts/check_doc_hygiene.sh"
    "${REPO_ROOT}/scripts/seedlab_report_from_artifacts.sh"
    "${REPO_ROOT}/scripts/seed_k8s_profile_runner.sh"
    "${REPO_ROOT}/.opencode/agents/seed-lab.md"
    "${REPO_ROOT}/.opencode/skills/seed-lab-core/SKILL.md"
    "${REPO_ROOT}/.opencode/skills/seed-lab-preflight/SKILL.md"
    "${REPO_ROOT}/.opencode/skills/seed-lab-execution/SKILL.md"
    "${REPO_ROOT}/.opencode/skills/seed-lab-verification/SKILL.md"
    "${REPO_ROOT}/.opencode/skills/seed-lab-triage/SKILL.md"
    "${REPO_ROOT}/.opencode/skills/seed-lab-reporting/SKILL.md"
    "${REPO_ROOT}/.opencode/skills/seed-lab-optimizer/SKILL.md"
    "${REPO_ROOT}/.opencode/skills/seed-lab-experiment-assistant/SKILL.md"
    "${REPO_ROOT}/.opencode/commands/seed-lab-start.md"
    "${REPO_ROOT}/.opencode/commands/seed-lab-verify.md"
    "${REPO_ROOT}/.opencode/commands/seed-lab-observe.md"
    "${REPO_ROOT}/.opencode/commands/seed-lab-all.md"
    "${REPO_ROOT}/.opencode/commands/seed-lab-triage.md"
    "${REPO_ROOT}/.opencode/commands/seed-lab-report.md"
    "${REPO_ROOT}/.opencode/commands/seed-lab-doctor.md"
    "${REPO_ROOT}/.opencode/commands/seed-lab-next.md"
    "${REPO_ROOT}/.opencode/commands/seed-lab-home.md"
    "${REPO_ROOT}/.opencode/commands/seed-lab-kubectl.md"
    "${REPO_ROOT}/opencode.jsonc"
)

for file in "${required_files[@]}"; do
    if [[ -f "${file}" ]]; then
        pass "found ${file}"
    else
        fail "missing ${file}"
    fi
done

if [[ -f "${REPO_ROOT}/scripts/check_doc_hygiene.sh" ]]; then
    if "${REPO_ROOT}/scripts/check_doc_hygiene.sh" >"${ARTIFACT_DIR}/doc_hygiene.txt" 2>&1; then
        pass "doc hygiene"
    else
        fail "doc hygiene failed (see ${ARTIFACT_DIR}/doc_hygiene.txt)"
    fi
fi

for cmd in kubectl rg; do
    if command -v "${cmd}" >/dev/null 2>&1; then
        pass "command available: ${cmd}"
    else
        fail "command not found: ${cmd}"
    fi
done

export SEED_K3S_CLUSTER_NAME="${SEED_K3S_CLUSTER_NAME:-seedemu-k3s}"
export SEED_NAMESPACE="${SEED_NAMESPACE:-seedemu-k3s-mini-mn}"
export SEED_CNI_TYPE="${SEED_CNI_TYPE:-macvlan}"
export KUBECONFIG="${KUBECONFIG:-${REPO_ROOT}/output/kubeconfigs/${SEED_K3S_CLUSTER_NAME}.yaml}"

if [[ ! -f "${KUBECONFIG}" ]]; then
    warn "kubeconfig not found at ${KUBECONFIG}; attempting fetch"
    if [[ -n "${SEED_K3S_MASTER_IP:-}" && -n "${SEED_K3S_USER:-}" && -n "${SEED_K3S_SSH_KEY:-}" ]]; then
        "${REPO_ROOT}/scripts/k3s_fetch_kubeconfig.sh" || fail "k3s_fetch_kubeconfig.sh failed"
    else
        fail "missing SEED_K3S_MASTER_IP/SEED_K3S_USER/SEED_K3S_SSH_KEY for kubeconfig fetch"
    fi
fi

if [[ -n "${SEED_K3S_SSH_KEY:-}" ]]; then
    if [[ -r "${SEED_K3S_SSH_KEY}" ]]; then
        pass "ssh key readable: ${SEED_K3S_SSH_KEY}"
    else
        fail "ssh key not readable: ${SEED_K3S_SSH_KEY}"
    fi
else
    warn "SEED_K3S_SSH_KEY not set"
fi

NODES_OK=0
NS_VISIBLE=0
if [[ -f "${KUBECONFIG}" ]]; then
    if kubectl --kubeconfig "${KUBECONFIG}" get nodes -o wide >"${ARTIFACT_DIR}/kube_nodes.txt" 2>"${ARTIFACT_DIR}/kube_nodes.err"; then
        NODES_OK=1
        pass "kubectl can access nodes"
    else
        fail "kubectl cannot access nodes"
    fi

    if kubectl --kubeconfig "${KUBECONFIG}" get ns "${SEED_NAMESPACE}" >"${ARTIFACT_DIR}/namespace.txt" 2>"${ARTIFACT_DIR}/namespace.err"; then
        NS_VISIBLE=1
        pass "namespace visible: ${SEED_NAMESPACE}"
    else
        warn "namespace not visible yet: ${SEED_NAMESPACE}"
    fi
else
    fail "kubeconfig still missing after fetch attempt: ${KUBECONFIG}"
fi

export REPO_ROOT TS ARTIFACT_DIR NODES_OK NS_VISIBLE
python - <<'PY'
import json
import os
from pathlib import Path

summary = {
    "timestamp": os.environ["TS"],
    "repo_root": os.environ["REPO_ROOT"],
    "kubeconfig": os.environ.get("KUBECONFIG", ""),
    "namespace": os.environ.get("SEED_NAMESPACE", ""),
    "cni_type": os.environ.get("SEED_CNI_TYPE", ""),
    "checks": {
        "nodes_accessible": os.environ.get("NODES_OK") == "1",
        "namespace_visible": os.environ.get("NS_VISIBLE") == "1",
    },
}
Path(os.environ["ARTIFACT_DIR"], "summary.json").write_text(
    json.dumps(summary, indent=2),
    encoding="utf-8",
)
PY

if [[ "${SMOKE_FAIL}" == "1" ]]; then
    log "smoke failed; check ${ARTIFACT_DIR}/summary.json"
    exit 1
fi

if [[ "${SMOKE_WARN}" == "1" ]]; then
    log "smoke passed with warnings; check ${ARTIFACT_DIR}/summary.json"
    exit 0
fi

log "smoke passed; summary at ${ARTIFACT_DIR}/summary.json"
