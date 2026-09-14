#!/bin/bash
set -euo pipefail

cd -- "$(dirname -- "${BASH_SOURCE[0]}")"

# Read Compose service names, so unrelated files are never treated as services.
services=$(docker compose -f docker-compose.yml config --services)
base_services=()
node_services=()
while IFS= read -r service; do
    if [[ "$service" == "morris-worm-base" ]]; then
        continue
    elif [[ -f "dummies/$service" ]]; then
        base_services+=("$service")
    elif [[ -n "$service" ]]; then
        node_services+=("$service")
    fi
done <<< "$services"

# Compose does not infer build dependencies from another Dockerfile's FROM.
docker compose -f docker-compose.yml build morris-worm-base
if (( ${#base_services[@]} > 0 )); then
    docker compose -f docker-compose.yml build "${base_services[@]}"
fi

# Keep the original limit of 20 node images per batch.
for ((offset = 0; offset < ${#node_services[@]}; offset += 20)); do
    docker compose -f docker-compose.yml build "${node_services[@]:offset:20}"
done
