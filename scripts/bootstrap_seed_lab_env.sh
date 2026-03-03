#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${SCRIPT_DIR}/env_seedemu.sh"

ACTION="${1:-base}"
SEED_CONDA_ENV="${SEED_CONDA_ENV:-seedemu-k8s-py310}"
SEED_BOOTSTRAP_KVM_UP="${SEED_BOOTSTRAP_KVM_UP:-true}"

CONDA_BIN="${CONDA_BIN:-}"
CONDA_BASE_DIR="${CONDA_BASE_DIR:-}"

log() {
  echo "[bootstrap] $*"
}

warn() {
  echo "[bootstrap][WARN] $*" >&2
}

die() {
  echo "[bootstrap][ERROR] $*" >&2
  exit 1
}

usage() {
  cat <<'USAGE'
Usage: scripts/bootstrap_seed_lab_env.sh [base|kvm|all|check]

Actions:
  base   Install/prepare local tooling for SEED + opencode (no VM creation)
  kvm    Build local KVM+k3s lab (3 nodes) using scripts/kvm_quickstart.sh
  all    base + kvm + final doctor check
  check  Non-destructive status check and smoke check

Environment variables:
  SEED_CONDA_ENV          Conda env name (default: seedemu-k8s-py310)
  SEED_BOOTSTRAP_KVM_UP   true|false (default: true, for action kvm/all)

Examples:
  scripts/bootstrap_seed_lab_env.sh base
  scripts/bootstrap_seed_lab_env.sh all
  SEED_BOOTSTRAP_KVM_UP=false scripts/bootstrap_seed_lab_env.sh kvm
USAGE
}

require_cmd() {
  if ! command -v "$1" >/dev/null 2>&1; then
    die "Missing required command: $1"
  fi
}

ensure_user_bin_path() {
  mkdir -p "${HOME}/.local/bin"
  case ":${PATH}:" in
    *":${HOME}/.local/bin:"*) ;;
    *) export PATH="${HOME}/.local/bin:${PATH}" ;;
  esac
}

detect_os_arch() {
  local os arch
  os="$(uname -s | tr '[:upper:]' '[:lower:]')"
  arch="$(uname -m)"

  case "${os}" in
    linux*) os="linux" ;;
    darwin*) os="darwin" ;;
    *) os="unknown" ;;
  esac

  case "${arch}" in
    x86_64|amd64) arch="x86_64" ;;
    aarch64|arm64) arch="arm64" ;;
    *) arch="unknown" ;;
  esac

  echo "${os}:${arch}"
}

install_opencode_if_missing() {
  if command -v opencode >/dev/null 2>&1; then
    log "opencode already installed: $(command -v opencode)"
    return
  fi

  require_cmd curl
  ensure_user_bin_path
  log "Installing opencode to ${HOME}/.local/bin via official installer..."
  XDG_BIN_DIR="${HOME}/.local/bin" curl -fsSL https://opencode.ai/install | bash

  if ! command -v opencode >/dev/null 2>&1; then
    if [ -x "${HOME}/.local/bin/opencode" ]; then
      export PATH="${HOME}/.local/bin:${PATH}"
    fi
  fi

  command -v opencode >/dev/null 2>&1 || die "opencode install failed"
  log "opencode installed: $(command -v opencode)"
}

install_conda_if_missing() {
  if command -v conda >/dev/null 2>&1; then
    CONDA_BIN="$(command -v conda)"
    CONDA_BASE_DIR="$("${CONDA_BIN}" info --base)"
    log "conda already installed: ${CONDA_BIN}"
    return
  fi

  require_cmd curl
  local combo os arch installer tmp
  combo="$(detect_os_arch)"
  os="${combo%%:*}"
  arch="${combo##*:}"

  case "${os}:${arch}" in
    linux:x86_64) installer="Miniconda3-latest-Linux-x86_64.sh" ;;
    linux:arm64) installer="Miniconda3-latest-Linux-aarch64.sh" ;;
    darwin:x86_64) installer="Miniconda3-latest-MacOSX-x86_64.sh" ;;
    darwin:arm64) installer="Miniconda3-latest-MacOSX-arm64.sh" ;;
    *)
      die "Unsupported OS/arch for automatic conda install: ${os}/${arch}"
      ;;
  esac

  CONDA_BASE_DIR="${HOME}/miniconda3"
  tmp="$(mktemp -d)"
  trap 'rm -rf "${tmp}"' RETURN
  log "Installing Miniconda (${installer}) to ${CONDA_BASE_DIR}..."
  curl -fsSL -o "${tmp}/miniconda.sh" "https://repo.anaconda.com/miniconda/${installer}"
  bash "${tmp}/miniconda.sh" -b -p "${CONDA_BASE_DIR}"
  trap - RETURN
  rm -rf "${tmp}"

  CONDA_BIN="${CONDA_BASE_DIR}/bin/conda"
  [ -x "${CONDA_BIN}" ] || die "conda install did not produce ${CONDA_BIN}"
}

ensure_conda_env_and_python_deps() {
  local conda_sh
  conda_sh="${CONDA_BASE_DIR}/etc/profile.d/conda.sh"
  [ -f "${conda_sh}" ] || die "Missing conda init script: ${conda_sh}"
  # shellcheck source=/dev/null
  source "${conda_sh}"

  if ! conda env list | awk '{print $1}' | grep -qx "${SEED_CONDA_ENV}"; then
    log "Creating conda env ${SEED_CONDA_ENV} (Python 3.10)..."
    conda create -y -n "${SEED_CONDA_ENV}" python=3.10
  else
    log "Conda env already exists: ${SEED_CONDA_ENV}"
  fi

  log "Installing Python dependencies into ${SEED_CONDA_ENV}..."
  conda run -n "${SEED_CONDA_ENV}" python -m pip install --upgrade pip setuptools wheel
  conda run -n "${SEED_CONDA_ENV}" pip install -r "${REPO_ROOT}/requirements.txt" -r "${REPO_ROOT}/dev-requirements.txt"
  conda run -n "${SEED_CONDA_ENV}" pip install -e "${REPO_ROOT}"
}

install_kubectl_if_missing() {
  if command -v kubectl >/dev/null 2>&1; then
    log "kubectl already installed: $(command -v kubectl)"
    return
  fi

  require_cmd curl
  ensure_user_bin_path

  local combo os arch version url
  combo="$(detect_os_arch)"
  os="${combo%%:*}"
  arch="${combo##*:}"
  version="$(curl -fsSL https://dl.k8s.io/release/stable.txt)"

  case "${os}:${arch}" in
    linux:x86_64) url="https://dl.k8s.io/release/${version}/bin/linux/amd64/kubectl" ;;
    linux:arm64) url="https://dl.k8s.io/release/${version}/bin/linux/arm64/kubectl" ;;
    darwin:x86_64) url="https://dl.k8s.io/release/${version}/bin/darwin/amd64/kubectl" ;;
    darwin:arm64) url="https://dl.k8s.io/release/${version}/bin/darwin/arm64/kubectl" ;;
    *)
      die "Unsupported OS/arch for automatic kubectl install: ${os}/${arch}"
      ;;
  esac

  log "Installing kubectl ${version} to ${HOME}/.local/bin/kubectl..."
  curl -fsSL -o "${HOME}/.local/bin/kubectl" "${url}"
  chmod +x "${HOME}/.local/bin/kubectl"
  command -v kubectl >/dev/null 2>&1 || die "kubectl install failed"
}

install_kind_if_missing() {
  if command -v kind >/dev/null 2>&1; then
    log "kind already installed: $(command -v kind)"
    return
  fi

  require_cmd curl
  ensure_user_bin_path

  local combo os arch url
  combo="$(detect_os_arch)"
  os="${combo%%:*}"
  arch="${combo##*:}"

  case "${os}:${arch}" in
    linux:x86_64) url="https://kind.sigs.k8s.io/dl/latest/kind-linux-amd64" ;;
    linux:arm64) url="https://kind.sigs.k8s.io/dl/latest/kind-linux-arm64" ;;
    darwin:x86_64) url="https://kind.sigs.k8s.io/dl/latest/kind-darwin-amd64" ;;
    darwin:arm64) url="https://kind.sigs.k8s.io/dl/latest/kind-darwin-arm64" ;;
    *)
      warn "Unsupported OS/arch for automatic kind install: ${os}/${arch}"
      return
      ;;
  esac

  log "Installing kind to ${HOME}/.local/bin/kind..."
  curl -fsSL -o "${HOME}/.local/bin/kind" "${url}"
  chmod +x "${HOME}/.local/bin/kind"
  if ! command -v kind >/dev/null 2>&1; then
    warn "kind install failed; continue without kind"
  fi
}

action_base() {
  ensure_user_bin_path
  install_opencode_if_missing
  install_conda_if_missing
  ensure_conda_env_and_python_deps
  install_kubectl_if_missing
  install_kind_if_missing

  if command -v opencode >/dev/null 2>&1; then
    log "opencode models:"
    opencode models | sed 's/^/[bootstrap]   /'
  fi

  log "Base bootstrap done."
  log "Next: cd ${REPO_ROOT} && opencode"
}

action_kvm() {
  require_cmd bash
  if [ "${SEED_BOOTSTRAP_KVM_UP}" = "true" ]; then
    log "Running KVM quickstart up (this can take several minutes)..."
    "${REPO_ROOT}/scripts/kvm_quickstart.sh" up
  else
    log "Running KVM quickstart prereq only..."
    "${REPO_ROOT}/scripts/kvm_quickstart.sh" prereq
  fi

  if [ -x "${REPO_ROOT}/scripts/k3s_fetch_kubeconfig.sh" ]; then
    log "Fetching kubeconfig..."
    "${REPO_ROOT}/scripts/k3s_fetch_kubeconfig.sh" || warn "k3s_fetch_kubeconfig.sh failed"
  fi
}

action_check() {
  log "Running entry status snapshot..."
  "${REPO_ROOT}/scripts/seed_lab_entry_status.sh"
  log "Running smoke check..."
  "${REPO_ROOT}/scripts/opencode_seedlab_smoke.sh" || warn "smoke returned non-zero; inspect artifacts"
}

action_all() {
  action_base
  action_kvm
  action_check

  if [ -n "${CONDA_BASE_DIR}" ] && [ -f "${CONDA_BASE_DIR}/etc/profile.d/conda.sh" ]; then
    # shellcheck source=/dev/null
    source "${CONDA_BASE_DIR}/etc/profile.d/conda.sh"
    if conda env list | awk '{print $1}' | grep -qx "${SEED_CONDA_ENV}"; then
      log "Running final doctor check..."
      conda run -n "${SEED_CONDA_ENV}" \
        "${REPO_ROOT}/scripts/seed_k8s_profile_runner.sh" "${SEED_EXPERIMENT_PROFILE:-mini_internet}" doctor \
        || warn "doctor check failed; inspect output/profile_runs"
    fi
  fi
}

case "${ACTION}" in
  base)
    action_base
    ;;
  kvm)
    action_kvm
    ;;
  all)
    action_all
    ;;
  check)
    action_check
    ;;
  -h|--help|help)
    usage
    ;;
  *)
    echo "Unknown action: ${ACTION}" >&2
    usage
    exit 1
    ;;
esac

