#!/usr/bin/env bash

SEED_AGENT_BASE_COMMON_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SEED_AGENT_BASE_DIR="$(cd "${SEED_AGENT_BASE_COMMON_DIR}/.." && pwd)"
SEED_EMAIL_REPO_ROOT="$(cd "${SEED_AGENT_BASE_DIR}/../.." && pwd)"

SEED_AGENT_DIR="${SEED_AGENT_DIR:-${SEED_EMAIL_REPO_ROOT}/../seed-agent}"

B29_OUTPUT_DIR="${B29_OUTPUT_DIR:-examples/internet/B29_email_dns/output}"
B00_OUTPUT_DIR="${B00_OUTPUT_DIR:-examples/internet/B00_mini_internet/output}"

SEED_AGENT_MCP_URL="${SEED_AGENT_MCP_URL:-http://127.0.0.1:8100/mcp}"
SEEDOPS_MCP_URL="${SEEDOPS_MCP_URL:-${SEED_MCP_URL:-http://127.0.0.1:8000/mcp}}"

seed_python_bin() {
  if command -v python3 >/dev/null 2>&1; then
    echo "python3"
    return 0
  fi
  if command -v python >/dev/null 2>&1; then
    echo "python"
    return 0
  fi
  echo "python3"
}

seed_resolve_path() {
  local path_input="$1"
  local base_dir="${2:-$PWD}"
  local pybin
  pybin="$(seed_python_bin)"
  "$pybin" - "$path_input" "$base_dir" <<'PY'
import sys
from pathlib import Path

raw = Path(sys.argv[1]).expanduser()
base = Path(sys.argv[2]).expanduser()
if raw.is_absolute():
    print(raw.resolve())
else:
    print((base / raw).resolve())
PY
}

seed_default_output_dir() {
  local baseline="$1"
  case "$baseline" in
    B29) echo "${B29_OUTPUT_DIR}" ;;
    B00) echo "${B00_OUTPUT_DIR}" ;;
    *)
      echo "Unsupported baseline: ${baseline}" >&2
      return 1
      ;;
  esac
}

seed_resolve_output_dir() {
  local baseline="$1"
  local override="${2:-}"
  local value
  if [[ -n "${override}" ]]; then
    value="${override}"
  else
    value="$(seed_default_output_dir "${baseline}")"
  fi
  seed_resolve_path "${value}" "${SEED_EMAIL_REPO_ROOT}"
}

seed_require_env() {
  local var_name="$1"
  if [[ -z "${!var_name:-}" ]]; then
    echo "Missing required env var: ${var_name}" >&2
    return 1
  fi
}

seed_require_file() {
  local file_path="$1"
  if [[ ! -f "${file_path}" ]]; then
    echo "Required file does not exist: ${file_path}" >&2
    return 1
  fi
}

seed_require_dir() {
  local dir_path="$1"
  if [[ ! -d "${dir_path}" ]]; then
    echo "Required directory does not exist: ${dir_path}" >&2
    return 1
  fi
}

seed_validate_mode() {
  local mode="$1"
  case "${mode}" in
    canonical|fallback|both) return 0 ;;
    *)
      echo "Invalid mode: ${mode} (expected canonical|fallback|both)" >&2
      return 1
      ;;
  esac
}

seed_now_utc_compact() {
  date -u +"%Y%m%dT%H%M%SZ"
}
