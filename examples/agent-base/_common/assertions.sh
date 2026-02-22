#!/usr/bin/env bash

seed_status_to_exit_code() {
  local status="${1:-error}"
  case "${status}" in
    ok) echo 0 ;;
    needs_input) echo 2 ;;
    blocked) echo 3 ;;
    upstream_error|timeout) echo 4 ;;
    error) echo 5 ;;
    *) echo 5 ;;
  esac
}

seed_json_path() {
  local json_file="$1"
  local path="$2"
  local pybin
  pybin="$(seed_python_bin)"
  "$pybin" - "$json_file" "$path" <<'PY'
import json
import re
import sys
from pathlib import Path

json_file = Path(sys.argv[1])
path = sys.argv[2].strip()

if not json_file.exists():
    print("")
    raise SystemExit(0)

with json_file.open("r", encoding="utf-8") as f:
    data = json.load(f)

if not path:
    print("")
    raise SystemExit(0)

cur = data
for token in path.split("."):
    if token == "":
        continue
    m = re.fullmatch(r"([^\[\]]+)(?:\[(\d+)\])?", token)
    if not m:
        print("")
        raise SystemExit(0)
    key = m.group(1)
    idx = m.group(2)
    if isinstance(cur, dict) and key in cur:
        cur = cur[key]
    else:
        print("")
        raise SystemExit(0)
    if idx is not None:
        if isinstance(cur, list):
            i = int(idx)
            if 0 <= i < len(cur):
                cur = cur[i]
            else:
                print("")
                raise SystemExit(0)
        else:
            print("")
            raise SystemExit(0)

if isinstance(cur, (dict, list)):
    print(json.dumps(cur, ensure_ascii=False))
elif cur is None:
    print("")
else:
    print(str(cur))
PY
}

seed_json_status() {
  seed_json_path "$1" "status"
}

seed_assert_status_ok() {
  local json_file="$1"
  local status
  status="$(seed_json_status "${json_file}")"
  if [[ "${status}" != "ok" ]]; then
    seed_log_error "Assertion failed: expected status=ok, got status=${status}, file=${json_file}"
    return 1
  fi
}

seed_assert_policy_allowed() {
  local json_file="$1"
  local allowed
  allowed="$(seed_json_path "${json_file}" "compiled_plan.policy.allowed")"
  if [[ "${allowed}" != "True" && "${allowed}" != "true" ]]; then
    seed_log_error "Assertion failed: compiled_plan.policy.allowed != true (${allowed}), file=${json_file}"
    return 1
  fi
}

seed_assert_summary_job_terminal() {
  local json_file="$1"
  local job_status
  job_status="$(seed_json_path "${json_file}" "summary.job_status")"
  if [[ -z "${job_status}" ]]; then
    job_status="$(seed_json_path "${json_file}" "job.final.job.status")"
  fi
  case "${job_status}" in
    succeeded|succeeded_with_errors|failed|canceled|interrupted) return 0 ;;
    *)
      seed_log_error "Assertion failed: job status is not terminal (${job_status}), file=${json_file}"
      return 1
      ;;
  esac
}

seed_assert_artifact_count_ge() {
  local json_file="$1"
  local min_count="$2"
  local pybin
  pybin="$(seed_python_bin)"
  "$pybin" - "$json_file" "$min_count" <<'PY'
import json
import sys
from pathlib import Path

path = Path(sys.argv[1])
min_count = int(sys.argv[2])
with path.open("r", encoding="utf-8") as f:
    data = json.load(f)

count = data.get("summary", {}).get("artifact_count")
if count is None:
    rows = data.get("artifacts", {}).get("list", {}).get("artifacts", [])
    count = len(rows) if isinstance(rows, list) else 0

if int(count or 0) < min_count:
    raise SystemExit(1)
PY
  local rc=$?
  if [[ ${rc} -ne 0 ]]; then
    seed_log_error "Assertion failed: artifact_count < ${min_count}, file=${json_file}"
    return 1
  fi
}

seed_assert_field_nonempty() {
  local json_file="$1"
  local path="$2"
  local value
  value="$(seed_json_path "${json_file}" "${path}")"
  if [[ -z "${value}" ]]; then
    seed_log_error "Assertion failed: field is empty (${path}), file=${json_file}"
    return 1
  fi
}

seed_assert_status_consistent() {
  local file_a="$1"
  local file_b="$2"
  local status_a
  local status_b
  status_a="$(seed_json_status "${file_a}")"
  status_b="$(seed_json_status "${file_b}")"
  if [[ "${status_a}" != "${status_b}" ]]; then
    seed_log_error "Assertion failed: status mismatch canonical=${status_a}, fallback=${status_b}"
    return 1
  fi
}

seed_resolve_mode_exit_code() {
  local mode="$1"
  local canonical_status="${2:-ok}"
  local fallback_status="${3:-ok}"

  if [[ "${mode}" == "canonical" ]]; then
    seed_status_to_exit_code "${canonical_status}"
    return 0
  fi
  if [[ "${mode}" == "fallback" ]]; then
    seed_status_to_exit_code "${fallback_status}"
    return 0
  fi

  local c_code
  local f_code
  c_code="$(seed_status_to_exit_code "${canonical_status}")"
  f_code="$(seed_status_to_exit_code "${fallback_status}")"
  if [[ "${c_code}" -ge "${f_code}" ]]; then
    echo "${c_code}"
  else
    echo "${f_code}"
  fi
}
