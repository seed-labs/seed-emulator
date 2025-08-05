#!/bin/bash

OPTION_FILE="/option.json"

curl -X POST \
     -H "Content-Type: application/json" \
     -d @$OPTION_FILE \
     http://ADDRESS/api/v1/container/ID/vis/set
