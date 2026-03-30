#!/bin/bash
docker container prune -f
docker network prune -f
#docker system prune -a -f --volumes
