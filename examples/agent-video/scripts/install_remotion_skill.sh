#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VIDEO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
CODEX_HOME="${CODEX_HOME:-${VIDEO_ROOT}/.codex-seed-video}"
SKILLS_DIR="${CODEX_HOME}/skills"

mkdir -p "${SKILLS_DIR}"

INSTALLER="/home/parallels/.codex/skills/.system/skill-installer/scripts/install-skill-from-github.py"
if [[ ! -f "${INSTALLER}" ]]; then
  echo "skill-installer not found: ${INSTALLER}" >&2
  exit 2
fi

echo "[seed-video] Installing remotion skill into: ${SKILLS_DIR}"
if [[ -d "${SKILLS_DIR}/remotion" ]]; then
  echo "[seed-video] Skill already installed: ${SKILLS_DIR}/remotion"
  echo "[seed-video] Project-scoped CODEX_HOME=${CODEX_HOME}"
  exit 0
fi
python "${INSTALLER}" \
  --repo remotion-dev/skills \
  --path skills/remotion \
  --dest "${SKILLS_DIR}"

echo "[seed-video] Done. Restart Codex to pick up new skills."
echo "[seed-video] Project-scoped CODEX_HOME=${CODEX_HOME}"
