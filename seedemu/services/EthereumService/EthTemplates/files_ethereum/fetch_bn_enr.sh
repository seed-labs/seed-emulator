#!/bin/bash

BOOTNODES_FILE="/tmp/bootnodes"
OUTPUT_ENR_FILE="/tmp/bc_enrs.txt"

MAX_RETRIES=60
SLEEP_SECONDS=3

ENRS=()

while read -r ip; do
    echo "⏳ Fetching ENR from $ip..."

    count=0
    while true; do
        enr=$(curl -s "http://$ip:8000/eth/v1/node/identity" | jq -r '.data.enr')

        if [ -n "$enr" ] && [ "$enr" != "null" ]; then
            echo "✅ Fetched ENR from $ip"
            ENRS+=("$enr")
            break
        else
            echo "❌ Failed to get ENR from $ip, retrying in $SLEEP_SECONDS seconds..."
            sleep "$SLEEP_SECONDS"
            ((count++))
            if [ "$count" -ge "$MAX_RETRIES" ]; then
                echo "❌ Gave up on $ip after $MAX_RETRIES retries."
                break
            fi
        fi
    done
done < "$BOOTNODES_FILE"

# Join ENRs with commas
IFS=','; echo "${ENRS[*]}" > "$OUTPUT_ENR_FILE"; unset IFS

echo "✅ All ENRs saved to $OUTPUT_ENR_FILE"
