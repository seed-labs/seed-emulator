#!/bin/bash

URL="http://{util_node_ip}:{util_node_port}/contracts_info?name={contract_name}"
EXPECTED_STATUS="200"

while true; do
    STATUS=$(curl -Is "$URL" | head -n 1 | awk '{{print $2}}')
    
    if [ "$STATUS" == "$EXPECTED_STATUS" ]; then
        echo "Link token contract has been deployed!"
        break
    else
        echo "Waiting for the link token contract to be deployed..."
        sleep 10
    fi
done
