#!/bin/bash
# Finds and opens a shell into the C2_Server container
CONTAINER_NAME="C2_server"
CONTAINER_ID=$(docker ps -f "name=$CONTAINER_NAME" -q | head -n 1)
CMD="cd /tmp/byob/byob/ && python3 server.py --port 445"

if [ -z "$CONTAINER_ID" ]; then
    echo "Error: C2_Server container not found. Is the simulation running?"
    exit 1
fi

echo "Found C2_Server container: $CONTAINER_ID"
echo "Opening shell..."

/usr/bin/curl -X POST -H "Content-Type: application/json" -d "{\"nodeId\": \"$CONTAINER_ID\", \"title\": \"$CONTAINER_NAME\", \"cmd\": \"$CMD\"}" "http://localhost:8080/api/v1/host"
