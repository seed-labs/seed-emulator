#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "$0")/.." && pwd)"
paperbanana_dir="${1:-$HOME/.cache/paperbanana/PaperBanana}"
output_root="${2:-$repo_root/docs/proposal/generated_figures/paperbanana_seed_agent_pack}"
pb_python="$paperbanana_dir/.venv/bin/python"

if [[ -f "$repo_root/.env" ]]; then
  set -a
  # shellcheck disable=SC1091
  source "$repo_root/.env"
  set +a
fi

export PAPER_TEXT_API_KEY="${PAPER_TEXT_API_KEY:-${PAPER_ONLY_API_KEY:-${GOOGLE_API_KEY:-${GEMINI_API_KEY:-}}}}"
export PAPER_TEXT_API_BASE="${PAPER_TEXT_API_BASE:-${PAPER_GEMINI_BASE:-https://right.codes/gemini}}"
export PAPER_IMAGE_API_KEY="${PAPER_IMAGE_API_KEY:-${GEMINI_API_KEY:-${GOOGLE_API_KEY:-${PAPER_ONLY_API_KEY:-}}}}"
export PAPER_IMAGE_API_BASE="${PAPER_IMAGE_API_BASE:-}"
export PAPER_ONLY_API_KEY="${PAPER_ONLY_API_KEY:-${PAPER_TEXT_API_KEY:-}}"
export GOOGLE_API_KEY="${GOOGLE_API_KEY:-${PAPER_TEXT_API_KEY:-}}"
export PAPER_GEMINI_BASE="${PAPER_GEMINI_BASE:-${PAPER_TEXT_API_BASE:-https://right.codes/gemini}}"
export PAPERBANANA_STYLE_GUIDE_PATH="${PAPERBANANA_STYLE_GUIDE_PATH:-$repo_root/docs/proposal/prompts/nsfc_concept_figure_style_guide.md}"
export PAPERBANANA_DRAFT_IMAGE_SIZE="${PAPERBANANA_DRAFT_IMAGE_SIZE:-1K}"
export PAPER_GEMINI_TIMEOUT_SECONDS="${PAPER_GEMINI_TIMEOUT_SECONDS:-30}"
export PAPER_GEMINI_MAX_ATTEMPTS="${PAPER_GEMINI_MAX_ATTEMPTS:-1}"
export PAPER_GEMINI_RETRY_DELAY_SECONDS="${PAPER_GEMINI_RETRY_DELAY_SECONDS:-3}"

if [[ -z "${PAPER_TEXT_API_KEY}" ]]; then
  echo "Missing PAPER_TEXT_API_KEY/PAPER_ONLY_API_KEY/GOOGLE_API_KEY/GEMINI_API_KEY" >&2
  exit 2
fi

if [[ -z "${PAPER_IMAGE_API_KEY}" ]]; then
  echo "Missing PAPER_IMAGE_API_KEY/GEMINI_API_KEY/GOOGLE_API_KEY/PAPER_ONLY_API_KEY" >&2
  exit 2
fi

if [[ ! -x "$pb_python" ]]; then
  echo "Missing PaperBanana venv python: $pb_python" >&2
  exit 2
fi

mkdir -p "$output_root"

run_case() {
  local name="$1"
  local method_file="$2"
  local caption_file="$3"
  local out_dir="$output_root/$name"

  mkdir -p "$out_dir"
  "$pb_python" "$repo_root/scripts/run_paperbanana_nsfc.py" \
    --paperbanana-dir "$paperbanana_dir" \
    --method-file "$method_file" \
    --caption-file "$caption_file" \
    --output-dir "$out_dir" \
    --exp-mode demo_full \
    --retrieval none \
    --candidates 2 \
    --concurrent 1 \
    --max-critic-rounds 1 \
    --aspect-ratio 16:9 \
    --pick 0 \
    --refine-4k \
    --refine-resolution 4K
}

run_case \
  architecture \
  "$repo_root/docs/proposal/prompts/seed_agent_architecture_method.md" \
  "$repo_root/docs/proposal/prompts/seed_agent_architecture_caption.txt"

run_case \
  principle \
  "$repo_root/docs/proposal/prompts/seed_agent_principle_method.md" \
  "$repo_root/docs/proposal/prompts/seed_agent_principle_caption.txt"

printf 'figure_pack=%s\n' "$output_root"
