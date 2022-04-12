#!/bin/bash

export SAVE_STATE=True
# remove the output folder
sudo rm -rf output/

# initial the network
./nano-internet.py

# build blockchain component
./component-blockchain.py

# render
./blockchain.py

# docker compose build
cd ./output 
docker-compose build

unset SAVE_STATE

