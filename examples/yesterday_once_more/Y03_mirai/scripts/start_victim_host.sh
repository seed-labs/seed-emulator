#!/bin/bash
# Finds and opens a shell into the victim_host container

CONTAINER_ID=$(docker ps -f "name=host_victim" -q | head -n 1)

if [ -z "$CONTAINER_ID" ]; then
    echo "Error: victim_host container not found. Is the simulation running?"
    exit 1
fi

echo "Found victim_host container: ${CONTAINER_ID}"
echo "Opening shell..."
docker exec -it ${CONTAINER_ID} /bin/bash