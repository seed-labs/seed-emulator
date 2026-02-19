#!/usr/bin/env bash

MISSION_COMMON_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
MISSION_ROOT_DIR="$(cd "${MISSION_COMMON_DIR}/.." && pwd)"
SEED_EMAIL_ROOT="$(cd "${MISSION_ROOT_DIR}/../.." && pwd)"

SEED_AGENT_DIR="${SEED_AGENT_DIR:-${SEED_EMAIL_ROOT}/subrepos/seed-agent}"

SEED_AGENT_MCP_URL="${SEED_AGENT_MCP_URL:-http://127.0.0.1:8100/mcp}"
SEED_AGENT_MCP_TOKEN="${SEED_AGENT_MCP_TOKEN:-${SEED_MCP_TOKEN:-}}"

B00_OUTPUT_DIR="${B00_OUTPUT_DIR:-examples/internet/B00_mini_internet/output}"
B29_OUTPUT_DIR="${B29_OUTPUT_DIR:-examples/internet/B29_email_dns/output}"

mission_require_cmd() {
  local cmd="$1"
  if ! command -v "$cmd" >/dev/null 2>&1; then
    echo "Missing required command: ${cmd}" >&2
    return 1
  fi
}

mission_require_env() {
  local name="$1"
  if [[ -z "${!name:-}" ]]; then
    echo "Missing required env: ${name}" >&2
    return 1
  fi
}

mission_abs_path() {
  local raw="$1"
  local base="${2:-$PWD}"
  python - "$raw" "$base" <<'PY'
import os
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

mission_resolve_output_dir() {
  local task_id="$1"
  case "$task_id" in
    *_B29_*|SEC_B29_*|TS_B29_*|RS_B29_*)
      mission_abs_path "${B29_OUTPUT_DIR}" "${SEED_EMAIL_ROOT}"
      ;;
    *)
      mission_abs_path "${B00_OUTPUT_DIR}" "${SEED_EMAIL_ROOT}"
      ;;
  esac
}
