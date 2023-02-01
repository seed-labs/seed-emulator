#!/bin/bash

# docker compose build
cd ./emulator-code/output
docker-compose down 2>/dev/null
echo "y" | docker system prune >/dev/null
docker-compose up > ../../test_log/log
cd ../../