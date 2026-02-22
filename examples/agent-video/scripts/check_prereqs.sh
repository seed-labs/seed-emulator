#!/usr/bin/env bash
set -euo pipefail

missing=0
check() {
  local cmd="$1"
  if command -v "$cmd" >/dev/null 2>&1; then
    echo "[ok] ${cmd} -> $("$cmd" --version 2>/dev/null | head -n1 || true)"
  else
    echo "[missing] ${cmd}"
    missing=1
  fi
}

check python

if command -v node >/dev/null 2>&1; then
  check node
  check npm
  check npx
else
  if [[ -x "$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)/.runtime/node/bin/node" ]]; then
    video_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
    node_home="${video_root}/.runtime/node"
    echo "[ok] node (local runtime) -> $("${node_home}/bin/node" --version)"
    PATH="${node_home}/bin:${PATH}" npm --version >/dev/null 2>&1 && echo "[ok] npm (local runtime)" || { echo "[missing] npm (local runtime)"; missing=1; }
    PATH="${node_home}/bin:${PATH}" npx --version >/dev/null 2>&1 && echo "[ok] npx (local runtime)" || { echo "[missing] npx (local runtime)"; missing=1; }
  else
    echo "[missing] node (system or local runtime)"
    missing=1
  fi
fi

if command -v ffmpeg >/dev/null 2>&1; then
  check ffmpeg
else
  if [[ -x "$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)/.runtime/ffmpeg/bin/ffmpeg" ]]; then
    echo "[ok] ffmpeg (local runtime)"
  else
    echo "[missing] ffmpeg (system or local runtime)"
    missing=1
  fi
fi

if [[ "$missing" -ne 0 ]]; then
  echo ""
  echo "No sudo is required for this project."
  echo "Bootstrap local runtime:"
  echo "  bash scripts/bootstrap_runtime.sh"
  echo "  bash scripts/bootstrap_ffmpeg.sh"
  exit 2
fi
