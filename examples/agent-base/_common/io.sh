#!/usr/bin/env bash

seed_log() {
  local level="$1"
  shift
  local ts
  ts="$(date -u +"%Y-%m-%dT%H:%M:%SZ")"
  echo "[${ts}] [${level}] $*"
}

seed_log_info() {
  seed_log "INFO" "$@"
}

seed_log_warn() {
  seed_log "WARN" "$@" >&2
}

seed_log_error() {
  seed_log "ERROR" "$@" >&2
}

seed_ensure_dir() {
  local dir_path="$1"
  mkdir -p "${dir_path}"
}

seed_write_pretty_json() {
  local in_file="$1"
  local out_file="$2"
  local pybin
  pybin="$(seed_python_bin)"
  "$pybin" - "$in_file" "$out_file" <<'PY'
import json
import sys
from pathlib import Path

src = Path(sys.argv[1])
dst = Path(sys.argv[2])

with src.open("r", encoding="utf-8") as f:
    data = json.load(f)

with dst.open("w", encoding="utf-8") as f:
    json.dump(data, f, indent=2, ensure_ascii=False)
    f.write("\n")
PY
}

seed_make_run_dir() {
  local artifacts_root="$1"
  local scenario_id="$2"
  local run_id
  run_id="$(seed_now_utc_compact)"
  local run_dir="${artifacts_root}/${scenario_id}/${run_id}"
  seed_ensure_dir "${run_dir}"
  local latest_link="${artifacts_root}/${scenario_id}/latest"
  ln -sfn "${run_id}" "${latest_link}"
  echo "${run_dir}"
}
