#!/bin/bash

LOGFILE="pos_block_$(date '+%Y%m%d_%H%M%S').log"

docker ps --format '{{.Names}}' | grep Geth | while IFS= read -r eth_container; do
    block=$(docker exec "$eth_container" geth attach --exec 'eth.blockNumber' 2>&1)
    exit_code=$?

    timestamp=$(date '+%F %T')

    if [ $exit_code -ne 0 ]; then
        line="$timestamp  ERROR on $eth_container: $block"
    else
        line="$timestamp  $eth_container Block: $block"
    fi

    echo "$line"
    echo "$line" >> "$LOGFILE"
done

