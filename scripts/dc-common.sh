#!/usr/bin/env bash
set -euo pipefail

resolve_compose_target() {
  local input="${1:-.}"
  if [[ -f "${input}" ]]; then
    readlink -f "${input}"
    return 0
  fi
  if [[ -d "${input}" ]]; then
    if [[ -f "${input}/docker-compose.yml" ]]; then
      readlink -f "${input}/docker-compose.yml"
      return 0
    fi
    if [[ -f "${input}/compose.yml" ]]; then
      readlink -f "${input}/compose.yml"
      return 0
    fi
  fi
  echo "[dc] ERROR: no docker-compose.yml/compose.yml found for: ${input}" >&2
  return 1
}

compose_cmd() {
  if command -v docker >/dev/null 2>&1; then
    printf 'docker compose\n'
    return 0
  fi
  if command -v docker-compose >/dev/null 2>&1; then
    printf 'docker-compose\n'
    return 0
  fi
  echo "[dc] ERROR: neither docker compose nor docker-compose is available" >&2
  return 1
}

default_map_port() {
  printf '%s\n' "${SEED_DEMO_MAP_PORT:-18080}"
}

dc_repo_root() {
  readlink -f "${SCRIPT_DIR}/.."
}

list_running_seedemu_containers() {
  docker ps --format '{{.Names}}' | grep -E '^(seedemu_internet_map|roundcube-|mail-|as[0-9]|output-)' || true
}

detect_active_baseline_compose() {
  local repo_root
  repo_root="$(dc_repo_root)"
  local running
  running="$(list_running_seedemu_containers)"
  if [[ -z "${running}" ]]; then
    return 1
  fi

  local best_compose=""
  local best_count=0
  local compose_file=""
  local container_name=""
  local count=0

  while IFS= read -r compose_file; do
    [[ -n "${compose_file}" ]] || continue
    count=0
    while IFS= read -r container_name; do
      [[ -n "${container_name}" ]] || continue
      if grep -Fqx "${container_name}" <<< "${running}"; then
        count=$((count + 1))
      fi
    done < <(sed -n 's/^[[:space:]]*container_name:[[:space:]]*//p' "${compose_file}")

    if (( count > best_count )); then
      best_count="${count}"
      best_compose="${compose_file}"
    fi
  done < <(find "${repo_root}/examples" -path '*/output/docker-compose.yml' -print 2>/dev/null | sort)

  if (( best_count > 0 )) && [[ -n "${best_compose}" ]]; then
    printf '%s\n' "${best_compose}"
    return 0
  fi
  return 1
}

guard_single_active_baseline() {
  local target_compose="$1"
  if [[ "${SEED_DC_FORCE:-0}" == "1" ]]; then
    return 0
  fi

  local active_compose
  active_compose="$(detect_active_baseline_compose || true)"
  if [[ -z "${active_compose}" ]]; then
    return 0
  fi

  if [[ "${active_compose}" == "${target_compose}" ]]; then
    return 0
  fi

  echo "[dc] ERROR: another baseline appears to be running." >&2
  echo "[dc] ERROR: active compose: ${active_compose}" >&2
  echo "[dc] ERROR: requested compose: ${target_compose}" >&2
  echo "[dc] ERROR: keep exactly one baseline online; run dcdown in the active baseline first." >&2
  echo "[dc] ERROR: if you intentionally want to bypass this guard, set SEED_DC_FORCE=1." >&2
  return 1
}

maybe_disable_bridge_netfilter() {
  if ! command -v sysctl >/dev/null 2>&1; then
    return 0
  fi

  local keys=(
    "net.bridge.bridge-nf-call-iptables"
    "net.bridge.bridge-nf-call-ip6tables"
    "net.bridge.bridge-nf-call-arptables"
  )
  local needs_fix="0"
  local key
  local value

  for key in "${keys[@]}"; do
    value="$(sysctl -n "${key}" 2>/dev/null || true)"
    if [[ "${value}" == "1" ]]; then
      needs_fix="1"
      break
    fi
  done

  if [[ "${needs_fix}" != "1" ]]; then
    return 0
  fi

  echo "[dc] host bridge netfilter is enabled; routed container traffic may be dropped"
  if [[ "${SEED_BRIDGE_NETFILTER_AUTO_DISABLE:-1}" != "1" ]]; then
    echo "[dc] auto-disable skipped because SEED_BRIDGE_NETFILTER_AUTO_DISABLE=${SEED_BRIDGE_NETFILTER_AUTO_DISABLE}"
    return 0
  fi

  local sysctl_args=(
    "net.bridge.bridge-nf-call-iptables=0"
    "net.bridge.bridge-nf-call-ip6tables=0"
    "net.bridge.bridge-nf-call-arptables=0"
  )

  if [[ "$(id -u)" == "0" ]]; then
    sysctl -w "${sysctl_args[@]}" >/dev/null
    echo "[dc] disabled host bridge netfilter for Docker-routed emulator traffic"
    return 0
  fi

  if command -v sudo >/dev/null 2>&1 && sudo -n true 2>/dev/null; then
    sudo -n sysctl -w "${sysctl_args[@]}" >/dev/null
    echo "[dc] disabled host bridge netfilter for Docker-routed emulator traffic"
    return 0
  fi

  echo "[dc] WARNING: unable to disable host bridge netfilter automatically" >&2
  echo "[dc] WARNING: run: sudo sysctl -w net.bridge.bridge-nf-call-iptables=0 net.bridge.bridge-nf-call-ip6tables=0 net.bridge.bridge-nf-call-arptables=0" >&2
}

usage_dcup() {
  cat <<'EOF'
Usage: dcup [--build] [output_dir_or_compose_file]

Defaults:
  - target: current directory
  - action: up -d --no-build --remove-orphans
  - map port: SEED_DEMO_MAP_PORT or 18080
  - use --build for fresh-image validation from current output
EOF
}

usage_dcdown() {
  cat <<'EOF'
Usage: dcdown [output_dir_or_compose_file]

Defaults:
  - target: current directory
  - action: down --remove-orphans
  - map port: SEED_DEMO_MAP_PORT or 18080
EOF
}
