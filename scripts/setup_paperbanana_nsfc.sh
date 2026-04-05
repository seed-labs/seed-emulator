#!/usr/bin/env bash
set -euo pipefail

target_dir="${1:-$HOME/.cache/paperbanana/PaperBanana}"
repo_root="$(cd "$(dirname "$0")/.." && pwd)"

mkdir -p "$(dirname "$target_dir")"
if [[ ! -d "$target_dir/.git" ]]; then
  git clone https://github.com/dwzhu-pku/PaperBanana.git "$target_dir"
fi

python3 -m venv "$target_dir/.venv"
source "$target_dir/.venv/bin/activate"
python -m pip install --upgrade pip
python -m pip install -r "$target_dir/requirements.txt"

python "$repo_root/scripts/patch_paperbanana_proxy.py" "$target_dir"

cat > "$target_dir/configs/model_config.yaml" <<'EOF'
defaults:
  main_model_name: "gemini-3-pro-preview"
  image_gen_model_name: "gemini-3.1-flash-image-preview"

api_keys:
  google_api_key: ""
  openai_api_key: ""
  anthropic_api_key: ""

google_api:
  base_url: ""
  api_version: "v1beta"
EOF

cat <<EOF
PaperBanana is ready at: $target_dir

Recommended environment before running:
  # text/planning path
  export PAPER_ONLY_API_KEY='...'
  export PAPER_TEXT_API_BASE='https://right.codes/gemini'
  # image/refine path
  export GEMINI_API_KEY='...'
  export PAPER_IMAGE_API_KEY="\${GEMINI_API_KEY}"
  export PAPER_IMAGE_API_BASE=''
  export PAPERBANANA_STYLE_GUIDE_PATH='$repo_root/docs/proposal/prompts/nsfc_concept_figure_style_guide.md'
  export PAPERBANANA_DRAFT_IMAGE_SIZE='1K'

To launch the original UI:
  cd '$target_dir'
  source .venv/bin/activate
  streamlit run demo.py
EOF
