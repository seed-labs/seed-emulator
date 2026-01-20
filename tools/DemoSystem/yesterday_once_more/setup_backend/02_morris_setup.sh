#!/bin/bash

# This conda_env variable might be different for the user
conda_env='emu'  

conda_path=$(which conda)
demo_system_path=$(pwd | sed 's/DemoSystem.*/DemoSystem/' )

CONFIG=$(cat <<EOF
condaPath: $conda_path
demoSystem:
  envName: $conda_env
  hostProjectPath: $demo_system_path
EOF
)

#echo "$CONFIG" > ./seedemu.conf

sudo mkdir -p /etc/seedemu
sudo rm -f /etc/seedemu/seedemu.conf
echo "$CONFIG" | sudo tee /etc/seedemu/seedemu.conf > /dev/null
