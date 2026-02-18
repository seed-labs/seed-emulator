#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
RENDER_SCRIPT="${SCRIPT_DIR}/_common/render_showcase_report.py"
RUN_SCRIPT="${SCRIPT_DIR}/run_real_showcase.sh"

WORK_DIR="/tmp/seed-agent-real-showcase"
REPORT_FILE=""
TAIL_LINES=25
PASS_ARGS=()

usage() {
  cat <<'EOF'
Usage: examples/agent-base/run_showcase_with_report.sh [options] [-- <run_real_showcase args>]

Options:
  --work-dir <path>      Work directory (default: /tmp/seed-agent-real-showcase)
  --report-file <path>   Output markdown path (default: <work-dir>/showcase_report.md)
  --tail-lines <n>       Log tail lines per section (default: 25)
  -h, --help

Examples:
  ./examples/agent-base/run_showcase_with_report.sh --s01-mode canonical --s04-mode canonical
  ./examples/agent-base/run_showcase_with_report.sh --work-dir /tmp/seed-demo -- --keep-work-dir
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --work-dir)
      WORK_DIR="${2:-}"
      shift 2
      ;;
    --report-file)
      REPORT_FILE="${2:-}"
      shift 2
      ;;
    --tail-lines)
      TAIL_LINES="${2:-}"
      shift 2
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    --)
      shift
      PASS_ARGS+=("$@")
      break
      ;;
    *)
      PASS_ARGS+=("$1")
      shift
      ;;
  esac
done

if [[ -z "${REPORT_FILE}" ]]; then
  REPORT_FILE="${WORK_DIR}/showcase_report.md"
fi

set +e
"${RUN_SCRIPT}" --work-dir "${WORK_DIR}" "${PASS_ARGS[@]}"
RUN_RC=$?
set -e

SUMMARY_JSON="${WORK_DIR}/real_showcase_summary.json"
LOG_DIR="${WORK_DIR}/logs"

python "${RENDER_SCRIPT}" \
  --summary "${SUMMARY_JSON}" \
  --logs-dir "${LOG_DIR}" \
  --output "${REPORT_FILE}" \
  --tail-lines "${TAIL_LINES}" >/dev/null
REPORT_RC=$?

echo "run_exit_code=${RUN_RC}"
echo "summary_json=${SUMMARY_JSON}"
echo "report_md=${REPORT_FILE}"

if [[ "${RUN_RC}" -ne 0 ]]; then
  exit "${RUN_RC}"
fi
exit "${REPORT_RC}"
