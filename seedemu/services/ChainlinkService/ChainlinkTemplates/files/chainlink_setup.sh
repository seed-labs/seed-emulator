#!/bin/bash

# Change the work folder to where the program is
cd "$(dirname "$0")"

bash ./request_fund.sh
bash ./check_link_contract.sh
python3 ./deploy_oracle_contract.py
bash ./register_contract.sh
bash ./create_chainlink_jobs.sh
