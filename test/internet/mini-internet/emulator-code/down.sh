#!/bin/bash

cd ./emulator-code/output

docker-compose down
echo "y" | docker system prune > /dev/null

cd ../../

