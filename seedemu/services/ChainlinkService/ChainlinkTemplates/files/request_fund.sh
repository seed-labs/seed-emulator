#!/bin/bash

FAUCET_RPC_URL="http://{faucet_server_ip}:{faucet_server_port}"
ETH_RPC_URL="http://{eth_server_ip}:{eth_server_port}"

# Change the work folder to where the program is
cd "$(dirname "$0")"

# Wait for the Chainlink node to be up
while true; do
    sleep 20
    # Get Ethereum address
    chainlink admin login -f ./password.txt
    ETH_ADDRESS=$(chainlink keys eth list | grep 'Address:' | awk '{{print $2}}')

    # Check if the address is empty
    if [ -z "$ETH_ADDRESS" ]; then
        echo "Error: Ethereum address cannot be empty."
    else
        # Address is not empty, break the loop
        echo "Ethereum address: $ETH_ADDRESS"
        break
    fi
done


AMOUNT=5
TIME_LIMIT=100

check_balance() {{
    response=$(curl -s -X POST $ETH_RPC_URL -H "Content-Type: application/json" --data '{{"jsonrpc":"2.0","method":"eth_getBalance","params":["'$1'", "latest"],"id":1}}')
    balance_hex=$(echo $response | jq -r '.result')
    if [ $balance_hex == "null" ]; then
        echo 0
    else
        echo $((16#${{balance_hex#0x}}))
    fi
}}

SERVER_STATUS=0

echo "Waiting for the faucet server to be up..."

while [ "$SERVER_STATUS" -ne 200 ]; do
    SERVER_STATUS=$(curl -s -o /dev/null -w "%{{http_code}}" $FAUCET_RPC_URL)
    if [ "$SERVER_STATUS" -ne 200 ]; then
        echo "Faucet server not up yet. Retrying..."
        sleep 5
    fi
done

echo "Faucet server is up. Proceeding to send fund request."
echo "curl -X POST -d address=$ETH_ADDRESS&amount=$AMOUNT $FAUCET_RPC_URL/fundme > /dev/null 2>&1 &"
curl -X POST -d "address=$ETH_ADDRESS&amount=$AMOUNT" "$FAUCET_RPC_URL/fundme" > /dev/null 2>&1 &
echo "Fund request sent to the faucet server."

start_time=$(date +%s)

while true; do
    current_time=$(date +%s)
    elapsed_time=$((current_time - start_time))
    
    balance=$(check_balance $ETH_ADDRESS)
    balance_eth=$(echo $balance | awk '{{printf "%.18f\\n", $1 / 1000000000000000000}}')
    
    echo "Current balance: $balance_eth ETH"
    
    funded=$(echo $balance_eth | awk '{{print ($1 > 0) ? "1" : "0"}}')
    
    if [ $funded -eq 1 ]; then
        echo "Funds already received. Exiting..."
        break
    elif [ $elapsed_time -gt $TIME_LIMIT ]; then
        echo "Account not funded after $TIME_LIMIT seconds. Sending another request..."
        echo "curl -X POST -d address=$ETH_ADDRESS&amount=$AMOUNT $FAUCET_RPC_URL/fundme > /dev/null 2>&1 &"
        curl -X POST -d "address=$ETH_ADDRESS&amount=$AMOUNT" "$FAUCET_RPC_URL/fundme" > /dev/null 2>&1 &
        start_time=$(date +%s)
    else
        echo "Account not yet funded. Waiting..."
    fi
    sleep 30
done

mkdir -p ./deployed_contracts
echo $ETH_ADDRESS > ./deployed_contracts/auth_sender.txt
