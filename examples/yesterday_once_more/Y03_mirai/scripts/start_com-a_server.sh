#!/bin/bash
# Finds and opens a shell into the COM-A DNS server container

# The container is bound to dns-host.as152
CONTAINER_ID=$(docker ps -f "name=COM-A" -q | head -n 1)

if [ -z "$CONTAINER_ID" ]; then
    echo "Error: COM-A Server container not found. Is the simulation running?"
    exit 1
fi

echo "Found COM-A Server container: ${CONTAINER_ID}"
echo "Opening shell..."
docker exec -it ${CONTAINER_ID} /bin/bash