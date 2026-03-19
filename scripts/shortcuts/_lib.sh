#!/usr/bin/env bash
set -euo pipefail

SHORTCUT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

seed_shortcuts_repo_root() {
  if [ -n "${REPO_ROOT:-}" ] && [ -d "${REPO_ROOT}" ]; then
    echo "${REPO_ROOT}"
    return 0
  fi

  if command -v git >/dev/null 2>&1; then
    local git_root
    git_root="$(git -C "${SHORTCUT_DIR}" rev-parse --show-toplevel 2>/dev/null || true)"
    if [ -n "${git_root}" ] && [ -d "${git_root}" ]; then
      echo "${git_root}"
      return 0
    fi
  fi

  echo "$(cd "${SHORTCUT_DIR}/../.." && pwd)"
}

seed_shortcuts_source_env() {
  local repo_root
  repo_root="$(seed_shortcuts_repo_root)"
  # shellcheck disable=SC1090
  source "${repo_root}/scripts/env_seedemu.sh"
}

seed_shortcuts_profile() {
  local profile="${1:-}"
  if [ -n "${profile}" ]; then
    echo "${profile}"
    return 0
  fi
  if [ -n "${SEED_EXPERIMENT_PROFILE:-}" ]; then
    echo "${SEED_EXPERIMENT_PROFILE}"
    return 0
  fi
  echo "mini_internet"
}

seed_shortcuts_is_profile_id() {
  local candidate="${1:-}"
  local repo_root profiles_path

  if [ -z "${candidate}" ]; then
    return 1
  fi

  repo_root="$(seed_shortcuts_repo_root)"
  profiles_path="${repo_root}/configs/seed_k8s_profiles.yaml"
  if [ ! -f "${profiles_path}" ]; then
    return 1
  fi

  python3 - <<PY >/dev/null 2>&1
from pathlib import Path
try:
    import yaml  # type: ignore
except Exception:
    raise SystemExit(1)
p = Path(${profiles_path@Q})
loaded = yaml.safe_load(p.read_text(encoding="utf-8")) or {}
profiles = loaded.get("profiles", {}) if isinstance(loaded, dict) else {}
raise SystemExit(0 if ${candidate@Q} in profiles else 1)
PY
}

seed_shortcuts_ensure_kubeconfig() {
  local repo_root candidate
  repo_root="$(seed_shortcuts_repo_root)"

  if [ -n "${KUBECONFIG:-}" ] && [ -f "${KUBECONFIG}" ]; then
    return 0
  fi

  candidate="${repo_root}/output/kubeconfigs/seedemu-k3s.yaml"
  if [ -f "${candidate}" ]; then
    export KUBECONFIG="${candidate}"
  fi
}

seed_shortcuts_resolve_namespace() {
  local profile="$1"
  local repo_root summary_path profiles_path
  repo_root="$(seed_shortcuts_repo_root)"

  if [ -n "${SEED_NAMESPACE:-}" ]; then
    echo "${SEED_NAMESPACE}"
    return 0
  fi

  summary_path="${repo_root}/output/profile_runs/${profile}/latest/validation/summary.json"
  if [ -f "${summary_path}" ]; then
    python3 - <<PY
import json
from pathlib import Path

p = Path(${summary_path@Q})
try:
    data = json.loads(p.read_text(encoding="utf-8"))
except Exception:
    data = {}
ns = data.get("namespace", "") if isinstance(data, dict) else ""
print(str(ns))
PY
    return 0
  fi

  profiles_path="${repo_root}/configs/seed_k8s_profiles.yaml"
  if [ -f "${profiles_path}" ]; then
    python3 - <<PY
from pathlib import Path
try:
    import yaml  # type: ignore
except Exception:
    print("")
    raise SystemExit(0)

p = Path(${profiles_path@Q})
loaded = yaml.safe_load(p.read_text(encoding="utf-8")) or {}
profiles = loaded.get("profiles", {}) if isinstance(loaded, dict) else {}
profile = profiles.get(${profile@Q}, {})
if isinstance(profile, dict):
    print(str(profile.get("default_namespace", "")))
else:
    print("")
PY
    return 0
  fi

  echo ""
}

seed_shortcuts_is_selector() {
  local value="${1:-}"
  [[ "${value}" == *"="* ]] || [[ "${value}" == *","* ]]
}

seed_shortcuts_pick_pod() {
  local namespace="$1"
  local target="$2"

  if [ -z "${target}" ]; then
    echo ""
    return 0
  fi

  if seed_shortcuts_is_selector "${target}"; then
    kubectl -n "${namespace}" get pods -l "${target}" \
      -o jsonpath='{.items[0].metadata.name}' 2>/dev/null || true
    return 0
  fi

  echo "${target}"
}

seed_shortcuts_print_map() {
  local shortcut="$1"
  shift
  echo "[${shortcut}] maps to: $*"
}

seed_shortcuts_die() {
  echo "ERROR: $*" >&2
  exit 1
}
