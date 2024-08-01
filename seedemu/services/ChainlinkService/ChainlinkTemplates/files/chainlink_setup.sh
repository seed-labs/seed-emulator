#!/bin/bash

# Change the work folder to where the program is
cd "$(dirname "$0")"

bash    ./get_auth_sender.sh
python3 ./fund_auth_sender.py
python3 ./deploy_oracle_contract.py
python3 ./register_contract.py
bash    ./create_jobs.sh
