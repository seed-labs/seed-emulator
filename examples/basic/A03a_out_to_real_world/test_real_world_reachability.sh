#!/bin/sh

docker compose -f output/docker-compose.yml exec -T hnode_151_web \
    ping -4 -c 5 -W 5 23.192.228.80 
