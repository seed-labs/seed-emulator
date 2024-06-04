#!/bin/env python3

import os, json, logging
from FaucetHelper import FaucetHelper

###########################################
faucet_url = "http://{faucet_server}:{faucet_server_port}"
###########################################

# Change the work folder to where the program is
abspath = os.path.abspath(__file__)
dname = os.path.dirname(abspath)
os.chdir(dname)

# Read the address
with open('./info/auth_sender.txt', 'r') as file:
    sender = file.read().strip()

# Fund the user account
faucet = FaucetHelper(faucet_url)
faucet.wait_for_server_ready()
faucet.send_fundme_request(sender, 10)


