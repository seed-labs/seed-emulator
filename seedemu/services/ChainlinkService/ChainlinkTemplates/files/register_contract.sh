#!/bin/bash

URL="http://{util_node_ip}:{util_node_port}"
EXPECTED_STATUS="200"

while true; do
    STATUS=$(curl -Is "$URL" | head -n 1 | awk '{{print $2}}')
    
    if [ "$STATUS" == "$EXPECTED_STATUS" ]; then
        echo "Server is up!"
        break 
    else
        echo "Retrying in 10 seconds.."
        sleep 10 
    fi
done


#RESPONSE=$(curl -X POST http://{util_node_ip}:{util_node_port}/register_contract \\
RESPONSE=$(curl -X POST "$URL"/register_contract \\
     -H "Content-Type: application/json" \\
     -d "{{\\"contract_name\\":\\"oracle-{node_name}\\", \\"contract_address\\":\\"$(tail -n 1 /deployed_contracts/oracle_contract_address.txt)\\"}}")

echo "$RESPONSE"

