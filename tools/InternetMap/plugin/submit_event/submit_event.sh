#!/bin/bash

URL="http://ADDRESS/api/v1/container/vis/set?id=$(hostname)"

ACTION=""
OPTION_FILE="/option.json"

show_usage() {
    echo "Options:"
    echo "  -a, --action flash   flash|flashOnce|highlight default: null"
    echo "  -f, --file           option json file path default: /option.json"
}

while [[ $# -gt 0 ]]; do
    case $1 in
        -a|--action)
            ACTION="$2"
            shift 2
            ;;
        -f|--file)
            OPTION_FILE=${2:-${OPTION_FILE}}
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

case "${ACTION}" in
    "flash"|"highlight"|"flashOnce")
        URL="${URL}&action=${ACTION}"
        ;;
    "")
        ;;
    *)
        show_usage
        ;;
esac

if [ -n ${OPTION_FILE} ] && [ -f ${OPTION_FILE} ]; then
    curl -X POST \
     -H "Content-Type: application/json" \
     -d @${OPTION_FILE} \
     "${URL}"
else
    curl -X POST "${URL}"
fi