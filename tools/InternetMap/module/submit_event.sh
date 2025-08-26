#!/bin/bash

OPTION_FILE="/option.json"
URL="http://ADDRESS/api/v1/container/ID/vis/set"

DEFAULT_ACTION="default"
ACTION=${1:-$DEFAULT_ACTION}

case "$ACTION" in
    "flash")
        URL="${URL}?action=flash"
        ;;
    "highlight")
        URL="${URL}?action=highlight"
        ;;
    "help")
        echo "params: $0 {flash|highlight|default}"
        echo "default: default"
        ;;
esac

if [ -f ${OPTION_FILE} ]; then
    curl -X POST \
     -H "Content-Type: application/json" \
     -d @${OPTION_FILE} \
     ${URL}
else
    curl -X POST ${URL}
fi
