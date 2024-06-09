#!/bin/bash

# Change the work folder to where the program is
cd "$(dirname "$0")"


python3 deploy_oracle_contract.py
python3 oracle_node_set_price.py
