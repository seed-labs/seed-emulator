#!/bin/bash

# docker compose build
cd ./output
docker-compose down 2>/dev/null
echo "y" | docker system prune >/dev/null
docker-compose up > ../log