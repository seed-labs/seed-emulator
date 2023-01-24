#!/bin/bash

rm -rf output/

./blockchain-pos.py

# docker compose build
cd ./output
docker-compose build