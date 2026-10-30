#!/usr/bin/env sh

set -eu

usage() {
    cat <<'EOF'
Usage:
  tools/run-example-test.sh EXAMPLE_CODE [COMMAND] [-- CLI_ARGS...]

Examples:
  tools/run-example-test.sh A01
  tools/run-example-test.sh A01 compile
  tools/run-example-test.sh A02a probe -- --artifact-dir ci-artifacts/a02-probe
  tools/run-example-test.sh B02 all

COMMAND defaults to all.
Supported commands: clean, compile, build, up, readiness, probe, test, down, all.

EXAMPLE_CODE is matched against example folder prefixes, such as A01, A02a,
A02b, B02, or D00. If a prefix matches multiple folders, use a more specific
prefix.
EOF
}

is_command() {
    case "$1" in
        clean|compile|build|up|readiness|probe|test|down|all) return 0 ;;
        *) return 1 ;;
    esac
}

if [ "$#" -lt 1 ]; then
    usage
    exit 2
fi

case "$1" in
    -h|--help)
        usage
        exit 0
        ;;
esac

script_dir=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
repo_root=$(CDPATH= cd -- "$script_dir/.." && pwd)

code=$1
shift

command=all
if [ "$#" -gt 0 ] && is_command "$1"; then
    command=$1
    shift
fi

if [ "$#" -gt 0 ] && [ "$1" = "--" ]; then
    shift
fi

matches=$(
    find "$repo_root/examples" -mindepth 2 -maxdepth 2 -type d \
        \( -iname "${code}" -o -iname "${code}_*" \) | sort
)

if [ -z "$matches" ]; then
    echo "No example folder found for code: $code" >&2
    exit 1
fi

match_count=$(printf '%s\n' "$matches" | sed '/^$/d' | wc -l | tr -d ' ')
if [ "$match_count" -gt 1 ]; then
    echo "Example code $code is ambiguous. Matches:" >&2
    printf '%s\n' "$matches" | sed "s#^$repo_root/##" >&2
    exit 1
fi

example_dir=$matches
manifest="$example_dir/example.yaml"
if [ ! -f "$manifest" ]; then
    echo "Example folder found, but it does not have example.yaml:" >&2
    echo "  ${example_dir#$repo_root/}" >&2
    exit 1
fi

artifact_name=$(basename "$example_dir")
artifact_dir="$repo_root/ci-artifacts/$artifact_name"

echo "[run-example-test] example: ${example_dir#$repo_root/}"
echo "[run-example-test] command: $command"
echo "[run-example-test] artifacts: ${artifact_dir#$repo_root/}"

if [ -n "${PYTHON:-}" ]; then
    python_cmd=$PYTHON
elif command -v python3 >/dev/null 2>&1; then
    python_cmd=python3
elif command -v python >/dev/null 2>&1; then
    python_cmd=python
else
    echo "No Python interpreter found. Set PYTHON=/path/to/python and retry." >&2
    exit 1
fi

cd "$repo_root"
exec "$python_cmd" seedemu/testing/cli.py "$command" "$manifest" \
    --artifact-dir "$artifact_dir" "$@"
