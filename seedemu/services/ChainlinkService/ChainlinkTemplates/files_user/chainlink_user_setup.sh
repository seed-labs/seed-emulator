#!/bin/bash

# Change the work folder to where the program is
cd "$(dirname "$0")"

python3 get_oracle_addresses.py
python3 deploy_user_contract.py
python3 set_contract_addresses.py
python3 fund_user_contract.py
python3 request_eth_price.py

