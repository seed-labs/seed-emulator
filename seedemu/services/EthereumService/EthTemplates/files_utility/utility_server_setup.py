#!/bin/bash

# Change the work folder to where the program is
cd "$(dirname "$0")"

python3 ./fund_account.py
python3 ./deploy_contract.py

