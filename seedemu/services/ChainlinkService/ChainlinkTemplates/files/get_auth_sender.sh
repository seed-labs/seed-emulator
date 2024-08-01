#!/bin/bash

# Change the work folder to where the program is
cd "$(dirname "$0")"

# Wait for the Chainlink node to be up
while true; do
    # Get Ethereum address
    chainlink admin login -f ./password.txt
    ETH_ADDRESS=$(chainlink keys eth list | grep 'Address:' | awk '{{print $2}}')

    # Check if the address is empty
    if [ -z "$ETH_ADDRESS" ]; then
        echo "Error: Ethereum address cannot be empty, retrying ..."
        sleep 20
    else
        # Address is not empty, break the loop
        echo "Ethereum address: $ETH_ADDRESS"
        break
    fi
done

# Save the address to a file
mkdir -p ./info
echo $ETH_ADDRESS > ./info/auth_sender.txt

