#!/usr/bin/env bash
set -euo pipefail

if [[ $# -lt 2 ]]; then
  echo "Usage: $0 <prompt_file> <output_prefix>"
  exit 1
fi

prompt_file="$1"
out_prefix="$2"
repo_root="$(cd "$(dirname "$0")/.." && pwd)"

if [[ ! -f "$prompt_file" ]]; then
  echo "Prompt file not found: $prompt_file"
  exit 1
fi

if [[ -f "$repo_root/.env" ]]; then
  set -a
  source "$repo_root/.env"
  set +a
fi

: "${PAPER_ONLY_API_KEY:?PAPER_ONLY_API_KEY is required}"

model="${PAPER_IMAGE_MODEL:-gemini-3.1-flash-image-preview}"
image_size="${PAPER_IMAGE_SIZE:-2K}"
aspect_ratio="${PAPER_ASPECT_RATIO:-16:9}"
gemini_base="${PAPER_GEMINI_BASE:-https://right.codes/gemini}"

mkdir -p "$(dirname "$out_prefix")"
req_json="${out_prefix}.request.json"
resp_json="${out_prefix}.response.json"

python3 - <<'PY' "$prompt_file" "$req_json" "$aspect_ratio" "$image_size"
import json, pathlib, sys
prompt_path, req_path, aspect_ratio, image_size = sys.argv[1:5]
prompt = pathlib.Path(prompt_path).read_text(encoding='utf-8')
body = {
    "contents": [{"parts": [{"text": prompt}]}],
    "generationConfig": {
        "temperature": 0.85,
        "responseModalities": ["IMAGE"],
        "imageConfig": {
            "aspectRatio": aspect_ratio,
            "imageSize": image_size,
        },
    },
}
pathlib.Path(req_path).write_text(json.dumps(body, ensure_ascii=False, indent=2), encoding='utf-8')
PY

curl -sS --max-time 240 \
  -X POST "${gemini_base}/v1beta/models/${model}:generateContent" \
  -H "x-goog-api-key: ${PAPER_ONLY_API_KEY}" \
  -H 'Content-Type: application/json' \
  --data @"${req_json}" \
  > "${resp_json}"

python3 - <<'PY' "$resp_json" "$out_prefix"
import base64, json, pathlib, sys
resp_path, out_prefix = sys.argv[1:3]
raw = pathlib.Path(resp_path).read_text(encoding='utf-8', errors='ignore')
obj = json.loads(raw)
out_count = 0
for ci, cand in enumerate(obj.get('candidates', [])):
    for pi, part in enumerate(cand.get('content', {}).get('parts', [])):
        inline = part.get('inlineData') or part.get('inline_data')
        if inline and inline.get('data'):
            mime = inline.get('mimeType') or inline.get('mime_type') or 'image/png'
            ext = '.png' if 'png' in mime else '.bin'
            out_path = pathlib.Path(f"{out_prefix}_{ci}_{pi}{ext}")
            out_path.write_bytes(base64.b64decode(inline['data']))
            print(out_path)
            out_count += 1
        elif 'text' in part:
            note_path = pathlib.Path(f"{out_prefix}.notes.txt")
            note_path.write_text(part['text'], encoding='utf-8')
            print(note_path)
if out_count == 0:
    raise SystemExit('No image parts returned. Inspect response JSON for details.')
PY
