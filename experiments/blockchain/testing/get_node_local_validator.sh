#!/bin/bash

# Configuration
CONTAINER_FILTER="POS"
DATA_DIR="/tmp/vc/local-testnet/testnet/validators"

echo "Scanning containers with name containing: $CONTAINER_FILTER"
echo "---------------------------------------------------------------"
printf "%-30s %-15s %-15s\n" "CONTAINER NAME" "IP ADDRESS" "VAL COUNT"
echo "---------------------------------------------------------------"

# Get all running containers matching the filter
CONTAINERS=$(docker ps --format '{{.Names}}' | grep "$CONTAINER_FILTER")

TOTAL_VALS=0
TOTAL_NODES=0

for CONTAINER in $CONTAINERS; do
    # Fetch container IP address
    IP=$(docker inspect -f '{{range .NetworkSettings.Networks}}{{.IPAddress}}{{end}}' "$CONTAINER")
    
    # Count directories starting with 0x in the validator path
    # Using 'ls' to count physical keystore folders
    VAL_COUNT=$(docker exec "$CONTAINER" bash -c "ls -d $DATA_DIR/0x* 2>/dev/null | wc -l")
    
    # Print row
    printf "%-30s %-15s %-15s\n" "$CONTAINER" "$IP" "$VAL_COUNT"
    
    # Aggregate statistics
    TOTAL_VALS=$((TOTAL_VALS + VAL_COUNT))
    TOTAL_NODES=$((TOTAL_NODES + 1))
done

echo "---------------------------------------------------------------"
echo "Summary Statistics:"
echo "Total POS Nodes Found: $TOTAL_NODES"
echo "Total Validators Found: $TOTAL_VALS"

