#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VIDEO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

QUALITY="draft"
OUT=""

usage() {
  cat <<'EOF'
Usage: examples/agent-video/scripts/render_video.sh [options]

Options:
  --quality draft|final
  --out <path>          Output mp4 path (default: output/seed_platform_120s.mp4)
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --quality) QUALITY="${2:-draft}"; shift 2 ;;
    --out) OUT="${2:-}"; shift 2 ;;
    -h|--help) usage; exit 0 ;;
    *) echo "Unknown arg: $1" >&2; usage; exit 2 ;;
  esac
done

case "${QUALITY}" in
  draft|final) ;;
  *) echo "--quality must be draft|final" >&2; exit 2 ;;
esac

if [[ -z "${OUT}" ]]; then
  OUT="${VIDEO_ROOT}/output/seed_platform_120s.mp4"
fi
if [[ "${OUT}" != /* ]]; then
  OUT="${VIDEO_ROOT}/${OUT}"
fi
mkdir -p "$(dirname "${OUT}")"

# Bootstrap local Node runtime (no sudo required).
bash "${SCRIPT_DIR}/bootstrap_runtime.sh" >/dev/null

cd "${VIDEO_ROOT}"

NODE_HOME="${VIDEO_ROOT}/.runtime/node"
export PATH="${NODE_HOME}/bin:${PATH}"

## Bootstrap local ffmpeg (no sudo required).
bash "${SCRIPT_DIR}/bootstrap_ffmpeg.sh" >/dev/null
FFMPEG_HOME="${VIDEO_ROOT}/.runtime/ffmpeg"
export FFMPEG_PATH="${FFMPEG_HOME}/bin/ffmpeg"
export FFPROBE_PATH="${FFMPEG_HOME}/bin/ffprobe"
export PATH="${FFMPEG_HOME}/bin:${PATH}"

if [[ ! -d node_modules ]]; then
  echo "[seed-video] Installing npm deps..."
  npm install
fi

if [[ ! -f public/voiceover.wav ]]; then
  echo "[seed-video] ERROR: missing public/voiceover.wav" >&2
  echo "[seed-video] Run: python scripts/generate_voiceover.py --script assets/narration/zh_cn_script.json --out assets/audio/voiceover.wav" >&2
  exit 2
fi

if [[ ! -f assets/subtitles/timeline.json ]]; then
  echo "[seed-video] Generating subtitles timeline..." >&2
  python scripts/build_subtitles.py
fi

options=()
if [[ "${QUALITY}" == "draft" ]]; then
  options+=(--crf 28 --scale 0.5)
else
  options+=(--crf 18 --scale 1)
fi

echo "[seed-video] Rendering (${QUALITY}) -> ${OUT}"
npx remotion render src/index.ts SeedPlatform120s "${OUT}" "${options[@]}"

echo "[seed-video] Done: ${OUT}"
