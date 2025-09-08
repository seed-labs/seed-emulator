#!/bin/bash

URL="http://ADDRESS/api/v1/container/vis/set?id=$(hostname)"

ACTION=""
STYLE_FILE=""

show_usage() {
    echo "Usage: $0 -a|--action [flash|flashOnce|highlight] [-s|--style option_file]"
    echo "Options:"
    echo "  -a, --action ACTION   flash|flashOnce|highlight (default: highlight)"
    echo "  -s, --style STYLE_FILE       style option json file path"
    echo "  -h, --help            show this help message"
}

while [[ $# -gt 0 ]]; do
    case $1 in
        -a|--action)
            if [ -z "$2" ] || [[ "$2" == -* ]]; then
                ACTION="highlight"
                shift
            else
                ACTION="$2"
                shift 2
            fi
            ;;
        -s|--style)
            STYLE_FILE=${2:-${STYLE_FILE}}
            shift 2
            ;;
        -h|--help)
            show_usage
            exit 0
            ;;
        *)
            echo "error: unknown option $1"
            show_usage
            exit 1
            ;;
    esac
done

if [ -z "${ACTION}" ]; then
    echo "error: the -a or --action parameter must be provided"
    show_usage
    exit 1
fi

case "${ACTION}" in
    "flash"|"highlight"|"flashOnce")
        URL="${URL}&action=${ACTION}"
        ;;
    "")
        ;;
    *)
        echo "error: unknown action '${ACTION}' [flash|flashOnce|highlight]"
        show_usage
        exit 1
        ;;
esac

if [ -n "${STYLE_FILE}" ] && [ -f "${STYLE_FILE}" ]; then
    curl -X POST \
     -H "Content-Type: application/json" \
     -d @${STYLE_FILE} \
     "${URL}"
else
    curl -X POST "${URL}"
fi