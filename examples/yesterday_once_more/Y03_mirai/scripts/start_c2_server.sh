#!/bin/bash
# Finds and opens a shell into the C2_Server container

CONTAINER_ID=$(docker ps -f "name=C2_server" -q | head -n 1)

if [ -z "$CONTAINER_ID" ]; then
    echo "Error: C2_Server container not found. Is the simulation running?"
    exit 1
fi

echo "Found C2_Server container: ${CONTAINER_ID}"
echo "Opening shell..."
docker exec -it ${CONTAINER_ID} /bin/bash