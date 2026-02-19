#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VIDEO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
RUNTIME_DIR="${VIDEO_ROOT}/.runtime"
FFMPEG_DIR="${RUNTIME_DIR}/ffmpeg"

arch="$(uname -m)"
case "${arch}" in
  aarch64|arm64) asset_name="ffmpeg-master-latest-linuxarm64-gpl.tar.xz" ;;
  x86_64|amd64) asset_name="ffmpeg-master-latest-linux64-gpl.tar.xz" ;;
  *)
    echo "[seed-video] ERROR: unsupported arch for ffmpeg: ${arch}" >&2
    exit 2
    ;;
esac

mkdir -p "${RUNTIME_DIR}/downloads"
tarball="${RUNTIME_DIR}/downloads/${asset_name}"

if [[ -x "${FFMPEG_DIR}/bin/ffmpeg" && -x "${FFMPEG_DIR}/bin/ffprobe" ]]; then
  echo "[seed-video] ffmpeg already present: ${FFMPEG_DIR}"
  exit 0
fi

download_url="$(python - "${asset_name}" <<'PY'
import json
import sys
import urllib.request

asset_name = sys.argv[1]
url = "https://api.github.com/repos/BtbN/FFmpeg-Builds/releases/latest"
with urllib.request.urlopen(url, timeout=20) as r:
    obj = json.load(r)
for a in obj.get("assets", []):
    if a.get("name") == asset_name:
        print(a.get("browser_download_url") or "")
        break
PY
)"
if [[ -z "${download_url}" ]]; then
  echo "[seed-video] ERROR: failed to resolve ffmpeg download url for ${asset_name}" >&2
  exit 2
fi

if [[ ! -f "${tarball}" ]]; then
  echo "[seed-video] Downloading ffmpeg: ${asset_name}"
  curl -fsSL "${download_url}" -o "${tarball}"
fi

tmp="${RUNTIME_DIR}/tmp_ffmpeg_extract"
rm -rf "${tmp}"
mkdir -p "${tmp}"
tar -xJf "${tarball}" -C "${tmp}"

extracted_root="$(find "${tmp}" -maxdepth 1 -type d -name 'ffmpeg-*' | head -n 1 || true)"
if [[ -z "${extracted_root}" ]]; then
  echo "[seed-video] ERROR: unexpected ffmpeg tar structure: ${tarball}" >&2
  exit 2
fi

rm -rf "${FFMPEG_DIR}"
mkdir -p "${FFMPEG_DIR}"
cp -a "${extracted_root}/." "${FFMPEG_DIR}/"
rm -rf "${tmp}"

if [[ ! -x "${FFMPEG_DIR}/bin/ffmpeg" || ! -x "${FFMPEG_DIR}/bin/ffprobe" ]]; then
  echo "[seed-video] ERROR: ffmpeg binaries missing after extract: ${FFMPEG_DIR}" >&2
  exit 2
fi

echo "[seed-video] ffmpeg installed: ${FFMPEG_DIR}"
