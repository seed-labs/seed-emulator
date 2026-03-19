#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${SCRIPT_DIR}/env_seedemu.sh"

PROFILE_ID="${1:-real_topology_rr}"
RUN_ID="${2:-latest}"
PORT="${SEED_SHOWCASE_PORT:-8088}"

exec python3 "${SCRIPT_DIR}/seed_k8s_showcase.py" \
  --profile "${PROFILE_ID}" \
  --run-id "${RUN_ID}" \
  --port "${PORT}"
