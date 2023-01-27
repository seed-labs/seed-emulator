#!/bin/bash

cd ./output

docker-compose down
echo "y" | docker system prune > /dev/null

cd ..

